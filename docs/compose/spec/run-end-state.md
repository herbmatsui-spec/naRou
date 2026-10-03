---
feature: run-end-state
status: designed
updated: 2026-10-04
branch: feature/run-end
commits:
---

# 案A ゲームを「終わらせる」

## Report

## [S1] Problem

### S1.1 ゲームは終了しない

`GameState.GAME_OVER` は `constants.py:249` に定義されているが、代入はリポジトリ全体で 0 件である。プレイヤーの HP が 0 になっても `engine/engine.py:1628` がログを 1 行出して終わるだけで、`GameStateData.current_state` は `EXPLORING` のままである。0 HP のプレイヤーは `turn_manager.py:131` の `e.hp > 0` フィルタでターン順から静かに除外されるため、世界は進行し続ける。

死亡前と同じ操作がそのまま通り、死は事実上の無意味である。run の概念が存在しないので、スコアも、次回への有意義な差も存在しない。

### S1.2 「ターン」はフレーム数である

`self.turns += 1` が 2 箇所にある。

- `engine/engine.py:1474` — `advance_world()` の中。処理済みで正しい。
- `engine/engine.py:2114` — `Engine.update()` の中。vsync ループが入力を読む前に毎フレーム無条件に呼ぶため、これによって `turns` は 1 プレイヤーアクションあたり数フレームだけ増える。

このため、自然回復の条件 `self.turns % NATURAL_REGEN_INTERVAL == 0` (`engine/engine.py:1483`) は、入力待ち時間を含めても概ね 10 フレームごとに成立する。待ち時間だけで全回復する。`).natural_regen` は毎戦前後に実質全快になり、消耗を設計できない。

同じ誤りは 50 ターンごとのオートセーブ (`engine/engine.py:1497` 付近) にも波及しており、実際には 50 フレームごとである。

### S1.3 バランス計測が測定結果を PASS に固定している

`tests/balance_simulator.py` がコミットされている `balance_report.json` は 3 シナリオすべて `win_rate: 1.0` を記録し、`lvl5_vs_orc` で `avg_dmg_dealt: 48.22` に対し `avg_dmg_taken: 7.55`（6.4 倍）の出力に対して `"is_balanced": true` と `"summary": "PASS"` を記録している。

`BalanceChecker.check_standards` (`tests/balance_simulator.py:51-65`) は `issues = []` とコメントだけの stub で、`data/balance_standards.yaml`（レベル別 HP/攻撃レンジ、経済、スキル効率、转生成長率）をロードしてから**一度も参照しない**。

さらに `simulate_battle` は実際に戦闘をシミュレートしていない。マップを生成せず、`advance_world` も `player_act` も `process_ai` も呼ばない。両者が `CombatSystem.calculate_melee_attack` を交互に呼ぶだけのアリーナであり、実際の戦闘ループ（自然回復・敵 AI・進行中の世界状態）を反映しない。

この 2 つの問題は別々に致命的である。計測器が「絶対に勝つのをバランス良好」と判定するため、案B/案C の効果が測定できない。

## [S2] Design

### S2.1 死亡で run を終了させる

死の判定を 1 箇所に集約し、`GameState.GAME_OVER` への遷移と run summary の提示を行う。

- 死の判定は turn 進行の入口（`Engine.advance_world`）に置き、攻撃元の種類（NPC・モンスター・環境効果）に依存させない。現状は NPC 攻撃分岐 `engine/engine.py:1626` にしかなく、他の死因では発火しない。
- 死亡時に `GameStateData.current_state = GameState.GAME_OVER` を立て、`game_state` 旧互換文字列も `"game_over"` に揃える。
- `GAME_OVER` 後は turn を進めない。`advance_world` は入口で状態を読み、GAME_OVER なら世界の更新を行わない（冪等）。
- run summary は到達深度・撃破数・喰い得到スキル数・経過ターン・死因・経過時間を保持し、画面に描画できるようにする。集計の実装は既存の state から引ける値のみを使い、新たな追跡機構を増やさない。
- 既存ログ行 `★あなたは力尽きた… 【GAME OVER】` は保持する（記述の連続性）。ただし它是唯一の状態表示でなくなる。

契約: プレイヤーの HP を 0 にすると `current_state` が `GameState.GAME_OVER` になる / その後 `advance_world` を呼んでもターンが増えない / summary に到達深度・撃破数・経過ターンが含まれる。

### S2.2 ターンカウントをターンに紐づける

- `Engine.update()` 内の `self.turns += 1` (`engine/engine.py:2114`) を削除する。描画・アニメーション・通知の更新はフレームベースのまま残す。
- `self.turns` は `advance_world()` の 1 回の起動ごとに 1 増える。アクションを 1 回も行わないフレームでは増えない。
- これにより自然回復は `NATURAL_REGEN_INTERVAL` ターンごとになり、`autosave_if_due` の 50 ターン周期も実距離に一致する。

契約: `update()` を N 回呼んでも `turns` が増えない / `advance_world()` を 1 回呼ぶと 1 増える / `NATURAL_REGEN_INTERVAL` の倍数の turn でのみ自然回復が成立する。

### S2.3 バランス計測を正直にする

測定器が PASS を返す仕組みをやめる。

- `BalanceChecker.check_standards` を実装し、`data/balance_standards.yaml` の基準値と実測値を照合する。最低限 `standards.levels` の min/max HP・攻撃と、`economy.max_gold_per_dungeon_floor` を実際に比較し、違反を `issues` に列挙する。
- `simulate_battle` は実際の戦闘ループの要素を含める。敵の AI 行動選択と、自然回復（S2.2 の turn ベース規則）を入れ、毎フレーム全快する状況を再現できるようにする。専用のアリーナ近似（両者が `calculate_melee_attack` を交互に呼ぶだけ）はやめる。
- 与被ダメージ比が想定を大きく下回る、もしくは勝率が 1.0 に張り付く場合は FAIL とする。「絶対勝利」を PASS と扱わない。
- 判定基準（勝率の許容範囲、ダメージ比の下限、one-shot 率の上限）を YAML に置き、コードに埋めない。既存の `expected_win_rate` は既にシナリオ定義にあるため、その形式をそのまま拡張する。

契約: 現状の数値で走らせると PASS にならない / 明示的に偏った 상황을渡すと FAIL になる / `check_standards` が YAML の基準値への違反を `issues` に列挙する。

### S2.4 リグレッション防止テスト

- `tests/test_run_end.py` — S2.1 と S2.2 の契約。GAME_OVER 遷移・GAME_OVER 後の turn 停止・summary 項目・`update()` が turn を増やさない・`advance_world()` が 1 増やす・自然回復が turn 間隔で成立すること。
- `tests/test_balance_report_honesty.py` — S2.3 の契約。偏りケースで FAIL になること、`check_standards` が YAML 違反を検出すること、コミット済み `balance_report.json` の `summary` が再実行結果と一致すること（古い PASS を残さない）。
- 既存 15 件の既知失敗は本 feature の残件ではない。

## [S3] Out of Scope

- 案B（devour の実効化）、案C（プレースホルダデータへの実データ投入）。別 feature。
- 難易度曲線そのものの設計（スケールの追加）。S2.3 は「正しく測る」までであり、読んだ数値を良い値にすることではない。
- 敵 AI の改善（`ai_system.py` のキャスターの防御ロール無し乱数、到達不能な kiter/flanker 分岐）。S2.3 では現状をそのまま測定する。
- リザルトのセーブ／ロードへの書き戻し、`save_system.py` の pickle 方式の変更。
- 死因の細分類（毒・窒息・落下など）。S2.1 で記録する死因は「戦闘」等の軽量な区分にとどめる。

## Tasks

- [ ] T1: 死の判定を `advance_world` に集約し、`GameState.GAME_OVER` 遷移と run summary を実装する — acceptance: プレイヤー HP を 0 にすると current_state が GAME_OVER になり、その後の advance_world で turn が増えず、summary に到達深度/撃破数/経過ターンが含まれる (covers: S2.1)
- [ ] T2: `Engine.update()` の `turns += 1` を削除し、ターンカウントを `advance_world` のみに紐づける — acceptance: update() を何度呼んでも turn が増えず、advance_world() を 1 回呼ぶと 1 増え、自然回復が NATURAL_REGEN_INTERVAL ターンごとにのみ成立する (covers: S2.2)
- [ ] T3: `BalanceChecker.check_standards` を `data/balance_standards.yaml` に対して実装し、`simulate_battle` に敵 AI と turn ベース自然回復を含めて判定基準を YAML 化する — acceptance: 現状の数値で PASS が返らず、意図的に偏った入力では FAIL が返り、YAML 違反が issues に列挙される (covers: S2.3)
- [ ] T4: リグレッション防止テスト `tests/test_run_end.py` と `tests/test_balance_report_honesty.py` を追加する — acceptance: 各テストが S2.1〜S2.3 の不具合を再現する形で失敗し、T1〜T3 適用後は全て成功する (covers: S2.1, S2.2, S2.3)
- [ ] T5: `balance_report.json` / `balance_report.html` を再生成し、値を実測に合わせる — acceptance: 再実行の結果が「PASS を返さない」結果を表しており、コミット済みレポートの summary が `run_full_validation` の戻り値と一致する (covers: S2.3)