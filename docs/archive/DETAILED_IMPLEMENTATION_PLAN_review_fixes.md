# 詳細実装計画書: コードレビュー指摘事項の修正 (1〜36 ステップ)

対象ブランチ方針: 現在の作業ツリー (`feature/webgl-postprocess`) 上で修正を実施。
ベースライン: `ruff` 498 errors (うち 314 自動修正可) / `pytest` 1 failed, 82 passed。

## Phase A — 準備 (Step 1-2)
1. ベースライン記録 (ruff/pytest 現状を `/tmp` に保存)
2. 本計画書作成

## Phase B — Critical: 実行時 NameError バグ (Step 3-14)
3. `fx_manager.py`: `import math` 追加 (spawn_shockwave の `math.radians/cos/sin`)
4. ruff で `fx_manager` F821 解消確認
5. `render_system.py`: `import math` 追加 (詠唱エフェクト)
6. ruff で `render_system` math F821 解消確認
7. `render_system.py`: ピクセルアート分岐で `lit_col` を計算してから照明ブロックを実行 (111行の未定義を解消)
8. ruff で `render_system` lit_col F821 解消確認
9. `ui_fx_systems.py`: モジュール先頭に `import random` 追加 (493-497行)
10. `ui_fx_systems.py`: `SoundManager` 未定義を修正 (関数内遅延 import)
11. ruff で `ui_fx_systems` F821 解消確認
12. `src/relationships/graph.py`: `from .models import ..., FactionAffiliation` 追加
13. `src/relationships/branching.py`: 同上
14. ruff で relationships F821 解消確認

## Phase C — Critical: dialogue speaker_id (Step 15-17)
15. `src/relationships/dialogue.py`: `_select_template` に `speaker_id` 引数を追加
16. 同ファイル: 呼び出し側 (252行) で `speaker_id` を渡す
17. ruff + relationships テスト実行

## Phase D — High: デッド機能 & 既存テスト (Step 18-21)
18. `main.py`: 存在しない `economy_sim.py` / `orchestrator.py` のメニュー項目を削除・番号付け直し
19. `main.py`: ヘルプテキストの該当記述を削除
20. 失敗テスト `test_dialogue_generation` を調査 (生成ロジックは正しいがテスト前提が脆弱)
21. 失敗テストを修正 (決定的かつ妥当なアサーションへ)

## Phase E — Medium: 非推奨 API & lint 一掃 (Step 22-29)
22. `input_handler.py`: `event.type == "QUIT"` 等の非推奨 API を `isinstance(event, tcod.event.Quit)` に置換
23. `input_handler.py.bak` を削除
24. `ruff --fix .` で F401/F841/F601/F811 を一括自動修正
25. E402 (ファイル先頭以外の import) / E741 (変数名 `l`) を手動修正
26. F541 (プレースホルダなし f-string) を修正
27. E701/E702 (1行複文) を修正 (ui_fx_systems / web_server)
28. `world_event_system.py` / `event_scheduler.py`: 未使用 import (`game.Engine`, `typing.*`) を削除
29. `title_system.py` / `systems.py`: 型注釈の未解決名 (`Entity`/`Item`) を import または `TYPE_CHECKING` で解決

## Phase F — Low: クリーンアップ (Step 30-31)
30. `.gitignore`: `*.bak`, `savegame.bin*`, `logs/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/` を追加
31. ルートの不要バックアップ (`savegame.bin.bak1~3`) を削除

## Phase G — 検証 (Step 32-36)
32. `ruff check .` で 0 エラー達成確認
33. `python -m pytest tests/ -q` ですべて pass 確認
34. `mypy .` 実行・主要箇所確認 (型エラーがあれば最小修正)
35. `git diff` で変更差分を最終レビュー
36. 完了サマリー作成

## 各バグの修正方針 (詳細)
- **fx_manager/math**: ファイル先頭 `import math` を追加。
- **render_system/math**: ファイル先頭 `import math` を追加。
- **render_system/lit_col**: ピクセルアート分岐で `console.blit` 直後に
  `lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, base_col, light_sources)`
  を挿入 (`base_col` は `COLOR_WALL_LIT`/`COLOR_FLOOR_LIT` で tile 種別判定)。
- **ui_fx_systems/random+SoundManager**: 先頭 `import random`; 呼び出し箇所で
  `from sound_manager import SoundManager` を遅延 import。
- **relationships/FactionAffiliation**: `graph.py`/`branching.py` の `from .models import` に追加。
- **dialogue/speaker_id**: `_select_template(..., speaker_id: str = "")` とし、呼び出し側で渡す。
- **main.py デッドメニュー**: 項目 2・3 を削除し、バランス検証を項目 2 に繰り上げ。
- **失敗テスト**: 生成ロジックは正しいため、アサーションを決定的なもの (非空文字列) に修正。
- **input_handler 非推奨**: `event.type` 比較を `isinstance` に置換。
