# 考古学メタゲーム 改善実装計画書（検証に基づく3改善）

## 背景（検証で判明した課題）
1. `story_endings.yaml` の `unlock_conditions` を評価・消費するコードが存在せず、
   `interpret_truth()` が立てる `ending_<id>_unlocked_by_archaeology` フラグがデッドエンド。
2. ジャーナルの考古学タブは表示のみで、プレイヤーが解釈（寄り先エンディング）を実際に「選ぶ」UIがない。
3. 鍵を後から入手しても既収集の未解読断片が自動解読されず、意図的「不完全性」を活かした謎解きの蓄積がない。
   また `JournalUI` に `visible` プロパティがなく `game.py` が `journal_ui.visible` を参照するためジャーナル起動時に例外。

## 改善①: エンディング実解決パイプライン（最重要）
- `archaeology_system.py` に `trigger_ending(player, ending_id, engine)` を追加。
- 到達真理＋leaned 解釈で選んだエンディングについて、`story_endings.yaml` の `unlock_conditions`
  各トークンを `player.story_flags` に `True` で書き込み（データ駆動で本当に満たす）、
  `ending_progress[ending_id]` を進め、エンディング到達ログ（ending_scene 名）＋勝利SEを再生。
- `interpret_truth()` の末尾で `trigger_ending()` を呼び、解釈＝即エンディング到達を実現（双方向接続）。
- `get_unlocked_endings(player)` で「考古学経由で到達可能なエンディング」を返す。

## 改善②: 解釈選択UI（ジャーナル内インタラクティブ）
- `JournalUI` に `visible` プロパティを追加（`is_open` の別名）し既存不整合を解消。
- `Engine` に解釈プロンプト状態を追加: `arch_interpret_active / arch_interpret_truth_idx / arch_interpret_ending_idx`。
- `Engine` メソッド: `open_interpret_prompt()` / `interpret_move_truth(d)` / `interpret_move(d)` /
  `confirm_interpret()` / `cancel_interpret()`。
- `input_handler.py`: `game_state=="journal"` 時に `[e]` でプロンプト開始、矢印で真理/候補移動、
  Enterで `confirm_interpret()`（= `interpret_truth` 呼び出し）、Escでキャンセル/閉じる。
- `journal_ui.py`: プロンプト中表示中は候補エンディングにカーソルを描画。

## 改善③: 遅延解読＋「気づき」蓄積＋発掘バリエーション
- `ArchaeologyComponent` に `decoder_hints_seen: List[str]` を追加。
- `acquire_key()` 内で `recheck_decoding(player, engine)` を呼び、未解読断片を鍵所有分だけ自動解読。
- `decode_fragment()` の未解読時、その `decoder_hint` を `decoder_hints_seen` に重複排除で蓄積。
- `pick_site_for_excavation(depth, rng)` を追加し、深度で一致する複数サイトからランダム選出（バリエーション）。
  `Engine.excavate()` はこれを使用。`find_site_for_depth()` はジャーナル表示用にそのまま（決定論的）。
- `export_share_summary()` に「手がかり（未解読ヒント）」を含める。

## 実装ステップ
1. 計画書作成（本ファイル）
2. `components.py`: `decoder_hints_seen` 追加
3. `archaeology_system.py`: 改善③ 遅延解読・ヒント蓄積・`pick_site_for_excavation`
4. `archaeology_system.py`: 改善① `trigger_ending` / `get_unlocked_endings` / `interpret_truth` 連携
5. `game.py`: `excavate()` を `pick_site_for_excavation` 使用に変更
6. `game.py`: 改善② 解釈プロンプト状態＋メソッド追加
7. `journal_ui.py`: `visible` プロパティ＋プロンプト描画
8. `input_handler.py`: `journal` 状態の解釈入力ルーティング
9. `tests/test_archaeology_metagame.py`: 3改善の追加アサーション
10. `pytest` 実行・修正・後方互換確認

## 成功基準
- `trigger_ending` で `story_endings` の `unlock_conditions` が実際に満たされ `ending_progress` が進む
- ジャーナル内で `[e]`→矢印→Enter で解釈を記録でき、例外が出ない
- 鍵後入手で未解読断片が自動解読され、ヒントが蓄積・表示される
- 既存テストが引き続き全て通る
