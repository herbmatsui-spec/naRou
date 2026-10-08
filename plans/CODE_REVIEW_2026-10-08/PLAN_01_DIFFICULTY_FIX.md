# 実装計画書: PLAN_01 難易度プリセット整合性の修正とロック

**対象発見**: F001 (critical), F004 (medium)  
**優先度**: 1 (商用ビルドのバランスが黙って壊れているため即時)  
**作業見積**: 30分 (Phase 0: 10分 + 実装: 15分 + 検証: 5分)

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_difficulty_preset.py` (新規) | `test_difficulty_preset_matches_config` | `core/difficulty.py` のプリセット値と `config.yaml` の値が一致することを検証 | `xfail(strict=True)` で追加 (失敗することを確認してから実装) |
| 0.2 | `tests/test_difficulty_preset.py` | `test_win_depth_reads_from_config` | `world_system.py` が `config.win_depth` を読むことを検証 | `xfail(strict=True)` |
| 0.3 | `tests/test_non_vacuity.py` | `assert_can_fail(test_difficulty_preset_matches_config, good_config, bad_config)` | テストが「偽の合格」を検出できることを非空虚性証明 | 実装後 green になることを確認 |

**非空虚性証明**: `bad_config` で `easy.player_damage_taken: 0.75` (現状の config 値) を与え、テストが赤になることを確認。

---

## 1. 実装ステップ (ファイル単位、アトミック、green→green)

### Step 1: `core/difficulty.py` — プリセット値を config と整合
- **ファイル**: `core/difficulty.py:15`
- **変更**: `DIFFICULTY_PRESETS["easy"]["player_damage_taken"] = 0.75` (config.yaml:19 と合わせる)
- **理由**: コード内プリセット(0.5) と設定値(0.75) の不整合を解消。どちらか一方を真実とする。config.yaml がユーザー可視設定なので、コードを config に合わせる。
- **回帰テスト**: 0.1 が green になる。

### Step 2: `engine/systems/world_system.py:108` — win_depth を config から読む
- **ファイル**: `engine/systems/world_system.py`
- **変更**: `if engine.dungeon_level >= 20:` → `win_depth = engine.config.get("win_depth", 20); if engine.dungeon_level >= win_depth:`
- **依存**: `engine.config` が `ConfigManager` または dict-like でアクセス可能であること (確認済み: `core/difficulty.py` は `config.get_config()` 使用)
- **回帰テスト**: 0.2 が green になる。

### Step 3: `config.yaml:19` — ドキュメント化 (任意)
- **ファイル**: `config.yaml`
- **変更**: コメント追加 `# player_damage_taken: 0.75 = 25% damage reduction (matches code preset)`
- **理由**: 将来の drift 防止。

---

## 2. 検証手順

```bash
# Phase 0: テストが赤であることを確認
/usr/bin/python3 -m pytest tests/test_difficulty_preset.py -v --runxfail

# 実装後
/usr/bin/python3 -m pytest tests/test_difficulty_preset.py -v
/usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_can_fail -v
```

---

## 3. 完了の定義

- [ ] `test_difficulty_preset_matches_config` PASS
- [ ] `test_win_depth_reads_from_config` PASS
- [ ] 非空虚性証明: `assert_can_fail` で偽 config が検出される
- [ ] 既存テスト (`test_enemy_abilities.py` 等) に回帰なし
- [ ] ruff/mypy clean