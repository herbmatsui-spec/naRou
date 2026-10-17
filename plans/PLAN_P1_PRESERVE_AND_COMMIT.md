# PLAN P1 — 未コミット1,841行+未追跡成果物の保全・分割コミット (案1)

基準: `main` @ `080b7ea`、未コミット 43ファイル (+1,841/−1,727) + 未追跡成果物
根拠: `plans/AUDIT_2026-10-06_EVALUATION_AND_9_PROPOSALS.md` §1.1/§2
原則: **preserve → green → tidy**。保全が最優先で、破壊的操作はしない。push はユーザー指示がない限りしない。

---

## 0. 目的と非目標

**目的**: 実装済みの未コミット作業 (DESIGN_V2 Step 12-32 相当: 死・勝利・進行・経済) と新規テスト9本を、誤操作で消失しない状態にし、レビュー可能な単位でコミットする。

**非目標**: push (未指示)、リベース/履歴書き換え、`.worktrees/` 配下の変更、Plan P2/P3 以外のコード修正。

---

## 1. リグレッション防止テスト (計画時に名指し)

| テスト | 役割 | 期待値 (測定済みベースライン) |
|---|---|---|
| `tests/test_non_vacuity.py` | 安全網の自己検証 | 7 passed |
| `tests/test_data_integrity.py` | データ整合 (2 xfail strict) | 2 xfailed (減らさない) |
| `tests/test_game_state.py` | 状態遷移 | 9 passed |
| `tests/test_economy.py` | 売却/経済 | 3 passed |
| `tests/test_difficulty.py` | 難易度プリセット | 4 passed |
| `tests/test_survival_balance.py` | サバイバル調整 | 4 passed |
| `tests/test_win_condition.py` | 勝利条件 | 5 passed |
| `tests/test_player_death.py` | 死亡ハンドラ | passed |
| `tests/test_run_boundary.py` | ラン境界 | passed |
| `tests/test_progression_curve.py` | 進行カーブ | passed |
| `tests/test_enemy_pool.py` | 敵プール | 2 passed |
| `tests/test_reachability.py` | 到達可能性 | 3 passed |
| `tests/test_balance_snapshot.py` | バランススナップショット | 5 passed / **1 failed (`test_exp_next_is_flat_100` — 既知の陳腐化マーカー、案4で置換)** |
| `tests/test_meta_progression.py` | メタ進行 | 6 passed |

**ルール**: 各コミット前後で上記チャンクの pass/fail/xfail カウントが**不変**であること (green→green)。カウントが変わったらそのコミットを取り消して分割をやり直す。

---

## 2. 原子サブステップ (1ステップ = 2-5項目、1ファイル単位で revert 可能)

### ステップ 1-1: ベースライン記録 (コード変更なし)
1. コアチャンク14ファイルを `pytest --tb=no -q` で実行し、pass/fail/xfail カウントを記録する。
2. `git stash list` が空であること (stash を作らない方針の確認)。

### ステップ 1-2: コミット (a) — DESIGN_V2 Step 12-32 相当の実装本体
1. `git add` 対象: `engine/` (engine.py, game_state.py, `systems/` 新規ディレクトリ), `ecs/`, `game.py`, `input_actions.py`, `input_handler.py`, `map_engine.py`, `save_system.py`, `data_manager.py`, `managers/combat_manager.py`, `packages/gameplay/package.py`, `config_loader.py` (新規), `run_history.json` (新規), `item_system.py`, `main_quest_system.py`, `meta_progression_system.py`, `skill_eater/ai/ai_system.py`, `reincarnation_system.py`。
2. `git add` データ: `config.yaml`, `data/balance_standards.yaml`, `data/world_state.yaml`, `data/monsters.yaml`, `data/items.yaml`, `data/meta_progression.yaml`, `data/jobs.yaml`, `data/skill_trees.yaml`, `data/skill_fusion.yaml`, `data/procedural_scenarios.yaml`, `data/story_choices.yaml`, `data/generated/`。
3. `git add` 新規テスト9本: `tests/test_player_death.py` `test_win_condition.py` `test_survival_balance.py` `test_difficulty.py` `test_economy.py` `test_enemy_pool.py` `test_progression_curve.py` `test_run_boundary.py` `test_dungeon_ceiling.py`、および `tests/relationships/`、`tests/balance_simulator.py`、72ステップ5ファイルのパス修正。
4. コアチャンクを再実行し、カウント不変を確認してから `git commit -m "feat: DESIGN_V2 Step 12-32 相当 (死・勝利・進行・経済の実装) — 未コミット作業の保全"`。

### ステップ 1-3: コミット (b) — 仕様書・報告書
1. `docs/compose/spec/survival-balance.md` と `win-condition.md` を確認 (内容は Step 29/勝利条件の仕様と一致済み)。
2. `plans/DESIGN_V2_PHASE1_REPORT.md` をコミット (`git add plans/`)。
3. `DEBUG_SUMMARY.md` は根ディレクトリ肥大化防止のため `plans/DEBUG_SUMMARY_2026-10-05.md` に移動してコミットする。
4. コアチャンク再実行 (カウント不変) → `git commit -m "docs: DESIGN_V2 Phase 1 報告書と仕様書を保全する"`。

### ステップ 1-4: savegame.bin* の追跡解除 (案8の土台、非破壊)
1. `git rm --cached savegame.bin savegame.bin.bak1 savegame.bin.bak2 savegame.bin.bak3` (ディスク上のデータは残る)。
2. `.gitignore` に `savegame.bin` と `savegame.bin*` を追加。
3. `git status` でセーブ系が未追跡になったことを確認 → コミット (b) の後に続けて `git commit -m "chore: セーブデータを実行時成果物として追跡対象外にする"`。

### ステップ 1-5: 残務の最終確認
1. `git status --short` が `.worktrees/`・`venv/`・`.tmp_bb4*` 以外クリーンであること。`.tmp_bb4/` `.tmp_bb4_sim.py` は中身を確認してから削除 (テスト実行時の一時物と確認できた場合のみ)。
2. `data/text/en.yaml.backup` は i18n 修復時のバックアップ — `en.yaml` が正しく構造統一済みであることを再確認してから削除する (削除前に内容差分を確認)。
3. コアチャンクを最終実行し、ステップ 1-1 のカウントと一致すること。

---

## 3. Definition of Done

1. 全コミット後、`git status --short` が意図した残務のみ (作業コード・テスト・データは全て追跡済み)。
2. コアチャンク pass/fail/xfail カウントが開始時と**完全一致**。
3. `git log --oneline -5` に保全コミットが並ぶ。
4. push はしない (未指示) — 「main が origin より N コミット先行」の状態を報告書に残す。

---

## 4. 検証と失敗時

- 各コミット後にカウントが変わった場合: `git reset HEAD~1` で当該コミットを取り消し、分割単位を見直す (revert 可能性を保証するため、 squash はしない)。
- `.bin` 追跡解除でテストが赤になった場合: `.gitignore` 追加のみを取り消し、追跡は維持して案8を再検討する。
