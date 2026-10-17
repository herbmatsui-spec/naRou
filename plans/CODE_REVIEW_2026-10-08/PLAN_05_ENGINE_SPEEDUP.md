# 実装計画書: PLAN_05 Engine() 構築高速化 — YAMLキャッシュ + ヘッドレス時Web bind抑制

**対象発見**: F036 (high) — Engine() 2.213秒 × テスト数 = テストスイート完走不能  
**優先度**: 5 (CI/開発ループの根本ボトルネック；全テスト実行可能化の前提)  
**作業見積**: 1.5–2時間 (Phase 0: 15分 + 実装: 45–60分 + 検証: 30分)  
**効果見込み**: Engine() 構築 2.2s → **<0.5s** (ヘッドレス時) = 4–5倍高速化

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_engine_performance.py` (新規) | `test_engine_construct_under_500ms_headless` | `NAROU_HEADLESS=1` 環境で `Engine()` 構築が 500ms 未満 | `xfail(strict=True)` |
| 0.2 | `tests/test_engine_performance.py` | `test_engine_construct_cache_hit` | 2回目以降の `Engine()` 構築で YAML 再読込が発生しない (キャッシュヒット) | `xfail(strict=True)` |
| 0.3 | `tests/test_engine_performance.py` | `test_web_server_not_bound_in_headless` | ヘッドレス時、ポート 8080 bind が試みられない | `xfail(strict=True)` |
| 0.4 | `tests/test_non_vacuity.py` | `assert_can_fail(test_engine_construct_under_500ms_headless, fast_engine, slow_engine)` | 遅いエンジンを検出できる非空虚性証明 | 実装後 green |

**非空虚性証明**: `slow_engine` = キャッシュ無効化 + bind 強制版 → 500ms 超えを検出。

---

## 1. ボトルネック分析 (実測済み)

| コンポーネント | 時間 | 対策 |
|---|---|---|
| 全 YAML データ再読込 (skill_trees, jobs, skill_fusion, procedural_scenarios, quest_generation_fallback, pet_quests) | ~1.2s | **モジュールレベルキャッシュ** (`functools.lru_cache` または専用 `DataCache` シングルトン) |
| `skill_eater_audio_system.py:90` `import pygame` 試行 ×2 (ModuleNotFoundError ハンドル) | ~0.3s | **Lazy import** + ヘッドレス検知でスキップ |
| `core/system_initializer.py:29` `start_web_server(engine, port=8080)` bind 試行 | ~0.4s | **環境変数/フラグで bind 抑制** (`NAROU_HEADLESS=1` または `engine.headless=True`) |
| その他 (ECS初期化、システム登録等) | ~0.3s | 現状維持 (最適化余地小) |

---

## 2. 実装ステップ (ファイル単位、アトミック)

### Step 1: `data_manager.py` / `data_validation.py` — YAML ロード関数に `lru_cache` 追加
- **対象**: `load_yaml()`, `load_all_data()`, `validate_data_files()` 等の公開関数
- **変更**: `@functools.lru_cache(maxsize=32)` デコレータ追加 (引数がパスのみなら自動キャッシュ)
- **注意**: テスト用に `cache_clear()` 公開関数も提供 (`data_manager.clear_cache()`)
- **回帰テスト**: 0.2 (cache hit) が green になる。

### Step 2: `skill_eater_audio_system.py:90` — pygame import を lazy 化
- **現状**: モジュールトップレベルで `try: import pygame except: pygame = None` ×2
- **変更**: 関数内遅延 import (`def _get_pygame(): ...`) に移動；ヘッドレス時は即座に `None` 返す
- **判定**: `os.environ.get("NAROU_HEADLESS") == "1"` または `not hasattr(sys, 'stdin')` 等
- **回帰テスト**: 0.1 時間短縮に寄与。

### Step 3: `core/system_initializer.py:29` — Web サーバー bind を条件付きに
- **現状**: `initialize_ui_and_services()` 内で無条件 `start_web_server(engine, port=8080)`
- **変更**: 
  ```python
  if not getattr(engine, 'headless', False) and os.environ.get("NAROU_HEADLESS") != "1":
      start_web_server(engine, port=8080)
  ```
- **Engine 側**: `__init__` で `self.headless = kwargs.get('headless', False)` 受け入れ
- **回帰テスト**: 0.1, 0.3 が green になる。

### Step 4: `main_text.py:14` / `run.py` — ヘッドレスフラグ伝播
- **main_text.py**: `Engine(headless=True)` で構築
- **run.py**: 同様
- **テスト側**: `conftest.py` で `os.environ["NAROU_HEADLESS"] = "1"` 設定 (既存テスト自動適用)

### Step 5: `engine/engine.py` — 不要な初期化遅延 (任意・低優先)
- **対象**: `kernel.get_system()` 遅延プロパティ化、`@property` デリゲーションを `__getattr__` に集約等
- **理由**: 更なる高速化余地；Phase 2 で対応

---

## 3. 検証手順

```bash
# Phase 0: 赤確認 (現状 2.2s で失敗するはず)
NAROU_HEADLESS=1 /usr/bin/python3 -m pytest tests/test_engine_performance.py -v --runxfail

# Step 1-3 後
NAROU_HEADLESS=1 /usr/bin/python3 -m pytest tests/test_engine_performance.py -v

# 非空虚性
NAROU_HEADLESS=1 /usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_can_fail -v

# 実用テスト: 8スイートが高速で通るか
NAROU_HEADLESS=1 /usr/bin/python3 -m pytest tests/test_skill_tree_job_system_72_steps.py tests/test_procedural_quest_generation_36_steps.py -v
```

---

## 4. 完了の定義

- [ ] `test_engine_construct_under_500ms_headless` PASS (ヘッドレス時 < 500ms)
- [ ] `test_engine_construct_cache_hit` PASS (2回目以降明らかに高速)
- [ ] `test_web_server_not_bound_in_headless` PASS (bind 試行なし)
- [ ] 非空虚性証明 PASS
- [ ] 既存 8スイート + 全テストが `NAROU_HEADLESS=1` で **完走可能** になる (時間短縮確認)
- [ ] ruff/mypy clean
- [ ] 非ヘッドレス (GUI) 起動で Web サーバー正常 bind 確認 (手動確認)