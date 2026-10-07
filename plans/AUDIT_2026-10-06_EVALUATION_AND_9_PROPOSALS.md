# naRou 精査・現実的評価と改善案9つ (2026-10-06)

対象リポジトリ: `/home/herbmatsui/narou` (main @ `080b7ea` + 大量の未コミット作業)
測定環境: Python 3.13.5 / pytest 9.1.1 / tcod 21.2.1 (システム Python、`venv/` は空)
検証方法: 本セッションで実測した値のみを根拠とする。推定には「(推定)」を付ける。

---

## 1. 測定された現状

### 1.1 ツリーの状態 (最大のリスク)

| 項目 | 実測値 |
|---|---|
| main が origin/main より進んでいるコミット | **29 コミット (未push)** |
| 未コミットの変更 | **43 ファイル / +1,841行 / −1,727行** |
| 未追跡の成果物 | 新規テスト9本 (`test_player_death.py` `test_win_condition.py` `test_survival_balance.py` `test_difficulty.py` `test_economy.py` `test_enemy_pool.py` `test_progression_curve.py` `test_run_boundary.py` `test_dungeon_ceiling.py`)、仕様書2本 (`docs/compose/spec/survival-balance.md` `win-condition.md`)、`engine/systems/`、`config_loader.py`、`run_history.json`、`tests/relationships/`、報告書2本 |
| セーブデータの追跡 | `savegame.bin` + `.bak1〜3` が **git に追跡されている** (`.gitignore` に該当エントリなし) |

未コミット作業の中身 (報告書と差分から): DESIGN_V2 Step 12〜32 相当 — 死亡ハンドラ、勝利条件 (`Engine.check_win_condition()` → `world_handler`、`engine/engine.py:1185`)、ラン境界、進行カーブ (`exp_next` プロパティ化)、難易度プリセット (`normal` 既定)、敵プール、経済 (売却 `SellAction`)、サバイバル調整。テスト付きで実装済みだが **1コミットもされていない**。

### 1.2 テストスイートの状態

| 項目 | 実測値 |
|---|---|
| 収集テスト数 | 933 |
| フルスイート完走 | **不能** — 570秒で約30% (テスト総量から (推定) 完走に30分超) |
| **Engine() 1回の構築コスト** | **平均 2.213秒** — 全YAMLデータ再読込 + `import pygame` 試行×2 (音声フォールバック) + **Webサーバー bind 試行×1** (`core/system_initializer.py:29` が Engine 構築のたびに `start_web_server(engine, port=8080)` を実行) |
| 「ハング」の正体 | **デッドロックではなく重さ**: ストーリーテラーテストは単独では **3.35秒でパス** (スイート内での停滞は累積時間)。`test_ranged_ability_accuracy_depends_on_defender` は Engine() を **120回** 構築 → **約265秒+** の単一テスト |
| pytest-timeout | **未インストール** (遅延が凍結に見え、検出されない) |
| pytest-xdist | 未インストール |
| コアチャンク (67テスト) の所要 | 57.28秒 (軽量な Entity 直接のシミュレーションは許容範囲) |

### 1.3 実測された失敗

| テスト | 状態 | 起因 |
|---|---|---|
| `test_balance_snapshot.py::test_exp_next_is_flat_100` | **失敗** (`assert 120`) | 欠陥を記録するマーカーテスト。Step 21 で `exp_next` がプロパティ化されたのに **Step 22 の置換が未実施** — 規約違反の「素の赤」 |
| `test_enemy_intent_formation.py` | **7失敗** / 47 | 未調査の失敗クラスタ |
| 72ステップデータ系6ファイル | **6/6 パス** (8.6秒) | `DEBUG_SUMMARY.md` の「プレースホルダー起因で未修復」記述は**陳腐化** |
| `tests/internationalization/test_internationalization.py::test_validate` | **失敗** | **`data/text/en.yaml` は依然13バイトのスタブ** (`hello: Hello` のみ; ja.yaml は 4,903バイト)。`DEBUG_SUMMARY.md` の「en.yaml を構造統一に更新した」主張は**未適用の虚偽** (本セッションで `en.yaml.backup` 13バイトと identical を実測) |
| 敵能力テスト | 5/22 測定後にハング | 継承21失敗は修復済みの可能性が高い |

### 1.4 静的検査 (ruff)

| ルール | 件数 | 性質 |
|---|---|---|
| W293 (空白入り空行) | 19 | 自動修正可 |
| W292 (末尾改行なし) | 10 | 自動修正可 |
| I001 (import未整列) | 8 | 自動修正可 |
| F811 (未使用の再定義) | 5 | 手動 (`engine/engine.py:189` CombatSystem、`engine/engine.py:1298` MAP_* 4件) |
| **F821 (未定義名)** | **5** | **実バグの可能性**: `engine/systems/world_system.py:123` の `engine` ×3 (未追跡の新規ファイル)、`save_system.py:352` の `game`、`sound_manager.py:142` の `Callable` (import欠落) |

### 1.5 良い news (評価の公平性のため)

- 勝利条件・死亡・進行・経済の DESIGN_V2 中核が**テスト付きで実装済み** (`test_win_condition.py` は `test_victory_cannot_go_to_game_over` など非空虚性パターンを踏襲)。
- 72ステップデータ系テストが全パス — `jobs.yaml` 等のプレースホルダ問題は解消済み。
- Phase 0 (Steps 1-11: GameStateMachine、遷移テスト) はマージ済み (`080b7ea`)。
- 継承された敵能力21失敗の多くが修復済みの可能性 (測定できた範囲では全パス)。

---

## 2. 現実的な評価

**強さ**: ゲームデザイン中核 (死・勝利・進行・経済) の実装は、72ステップ計画の規約 (テスト込み・非空虚性) に沿って進んでおり、Phase 0 の安全網も機能している。

**弱点 (この順で致命的)**:
1. **保全**: 1,841行の実装済み作業 + 新規テスト9本が未コミット。誤操作1回で消失する。push も29コミット分滞留。過去に「作業が存在するのに何も記録がなかった」事故が3回起きたリポジトリで、最大の未記録作業が今まさに存在する。
2. **検証可能性**: フルスイートが完走しない (30分超 + ハング2件 + timeout機構なし)。「実装→検証」ループの検証側が仕組みとして成立していない。
3. **実バグ**: 新規コード (`engine/systems/world_system.py`) に未定義名が3つ。到達すれば NameError。
4. **テストの正直さ**: 欠陥マーカーが素の赤として残り、xfail による進捗指標が汚れている。

総合: **方向は正しいが、検証基盤と保全が実装の速度に追いついていない。** 内容実装をさらに進める前に、(1) 保全、(2) 検証基盤、(3) 実バグの順に固めるのが現実的。

---

## 3. 改善案9つ (優先順位順)

| # | 改善案 | 根拠 (実測) | リグレッション防止 |
|---|---|---|---|
| **1** | **未コミット1,841行+未追跡成果物の保全・分割コミット** | §1.1 — 誤操作1回で消失する最大の未記録作業 | コミット前にコアチャンク緑確認、コミット単位で実装とテストを同じコミットに |
| **2** | **スイートを実行可能にする (Engine重量化の是正 + 反復数調整 + pytest-timeout 導入)** | §1.2 — Engine() 2.2秒×大量構築で完走不能、Webサーバー bind が構築のたびに走る | 修復対象テスト自体が緑、pyproject の timeout 設定を検証するテスト、Engine() の bind 抑制を検証する spy テスト |
| **3** | **F821 未定義名5件の修復 + F821 をゲート化** | §1.4 — 実バグの可能性、新規ファイルに3件 | 修正対象ファイルを直接実行する既存テスト群、`ruff --select F821` を pre-commit に追加 |
| 4 | 陳腐化した欠陥マーカー `test_exp_next_is_flat_100` の置換 (Step 22 の未完了) | §1.3 — 素の赤が xfail 進捗指標を汚す | 置換後のカーブテスト自体が緑、snapshot の他5テストが減らない |
| 5 | `test_enemy_intent_formation` の7失敗の根因修復 | §1.3 — 未調査の失敗クラスタ | 根因修復後に7テストが緑、敵能力系テストが減らない |
| 6 | スイート速度対策 (重いシミュレーションのサンプリング削減、slow マーク) | §1.2 — 67テスト57秒、完走30分超 | 数値を緩めたテストは `assert_can_fail` で非空虚性を証明 |
| 7 | F811 5件 + W293/W292/I001 41件の自動修正と pre-commit ゲート | §1.4 — 46件が修正可能 | 自動修正後にコアチャンク緑確認 |
| 8 | `savegame.bin*.bak` の追跡解除 (`.gitignore` 追加) | §1.1 — セーブ実データが git に混入 | `git status` でセーブ系が未追跡になること、テストは save_system 系が緑 |
| 9 | `requirements-lock.txt` のハッシュピン化 | MEMORY 記録の future work — `cd.yml:27` がこれをインストール | `test_entrypoint.py` の依存整合テストが緑 |

**本セッションで実装するのは上位3案 (#1〜#3)**。詳細な実装計画書:
- `plans/PLAN_P1_PRESERVE_AND_COMMIT.md` (案1)
- `plans/PLAN_P2_SUITE_RUNNABLE.md` (案2)
- `plans/PLAN_P3_F821_FIX_AND_GATE.md` (案3)

実装後は「実装→検証→修正」のループを5回繰り返す。サブエージェントは使わず単独で実施する。
