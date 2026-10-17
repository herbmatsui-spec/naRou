# 実装計画書: 誰でも面白くプレイできる3提案（全72ステップ）

- **目的**: GPU/環境/スキルに関わらず、誰でもこのゲームを楽しく遊べるようにする。
- **対象**: 低性能なLLMでも1ステップずつ確実に実装・検証できるよう、各ステップを「1つの小さな変更 ＋ 決まった検証」に分割。
- **前提知識**: Python 3.10+、既存コード（`game.py`, `core/tcod_renderer.py`, `web_server.py`, `webgl/renderer.ts`, `design_tokens.*.json`, `feature_flags.py`, `config.py`, `constants.py`）。
- **規約**: 各ステップは「独立してコンパイル/動作する」こと。前のステップが成功してから次へ。検証は必ず実行すること。

---

## フェーズ1（提案①）: GPU不要のテキスト(ASCII)プレイモード 〔ステップ1〜24〕

### Step 1 — `TextRenderer` の空クラスを作成
- **変更ファイル**: `core/text_renderer.py`（新規）
- **実装**: クラス `TextRenderer` を定義し、`__init__(self, width, height)` だけを持つ（ロジックなし）。docstring のみ。
- **検証**: `python -c "from core.text_renderer import TextRenderer; TextRenderer(80,50)"` がエラーなしで通る。

### Step 2 — 描画グリッド（文字＋色）を保持
- **変更ファイル**: `core/text_renderer.py`
- **実装**: `__init__` で `self.chars = [[" "]*width for _ in range(height)]` と `self.colors = [[(255,255,255)]*width for _ in range(height)]` を作る。
- **検証**: `python -c "..."` でインスタンス作成後 `len(tr.chars)==50 and len(tr.chars[0])==80`。

### Step 3 — `draw_tile(x,y,char,color)` を追加
- **変更ファイル**: `core/text_renderer.py`
- **実装**: 指定セルに char と color(rgb tuple) を格納。範囲外は無視。
- **検証**: 単体で `tr.draw_tile(1,2,'#',(200,0,0))` 後 `tr.chars[2][1]=='#'`。

### Step 4 — `draw_text(x,y,string,color)` を追加
- **変更ファイル**: `core/text_renderer.py`
- **実装**: 文字列を1文字ずつ横に描画。
- **検証**: `tr.draw_text(0,0,'HP',(0,255,0))` 後 `tr.chars[0][0]=='H' and tr.chars[0][1]=='P'`。

### Step 5 — `clear()` を追加
- **変更ファイル**: `core/text_renderer.py`
- **実装**: chars を全空白、colors を白に戻す。
- **検証**: 描画後に `clear()` し `tr.chars[2][1]==' '`。

### Step 6 — `present()` で ANSI 16色出力
- **変更ファイル**: `core/text_renderer.py`
- **実装**: 16色マップ `{"red":(200,0,0),...}` から最寄り色を選び `print(f"\x1b[38;5;{code}m{ch}\x1b[0m", end="")` を各行ごとに出力。
- **検証**: `tr.draw_tile(0,0,'@',(200,0,0)); tr.present()` が `@` を色付きで1行出力する。

### Step 7 — RGB→最寄り256色変換ヘルパ
- **変更ファイル**: `core/text_renderer.py`
- **実装**: `_nearest_256(r,g,b)` で 256色パレット(6x6x6+グレー)から最短距離を返す。
- **検証**: `_nearest_256(255,0,0)` が赤系コードを返す。

### Step 8 — `set_cursor(x,y)` ルックカーソル
- **変更ファイル**: `core/text_renderer.py`
- **実装**: `self.cursor=(x,y)` を保持、`present()` でそのセルを反転表示 `\x1b[7m`。
- **検証**: `set_cursor(3,3)` 後 `present()` で (3,3) が反転する（目視/文字列に `7m` 含む）。

### Step 9 — 機能フラグ `ENABLE_TEXT_MODE` を追加
- **変更ファイル**: `feature_flags.py`
- **実装**: `_feature_flags` に `"ENABLE_TEXT_MODE": False` を追加。
- **検証**: `python -c "from feature_flags import is_enabled; print(is_enabled('ENABLE_TEXT_MODE'))"` → `False`。

### Step 10 — 設定ファイルに `accessibility.text_mode` を追加
- **変更ファイル**: `config.yaml`
- **実装**: トップレベルに `accessibility:\n  text_mode: false` を追加。
- **検証**: `python -c "from config import get_config; print(get_config('accessibility.text_mode'))"` → `False`。

### Step 11 — `get_text_mode_enabled()` ヘルパ
- **変更ファイル**: `core/text_renderer.py`（または `feature_flags.py`）
- **実装**: フラグまたは config のいずれか True なら True を返す関数。
- **検証**: 両方 False で `False`、フラグ True で `True`。

### Step 12 — `engine.render()` のテキスト対応分岐
- **変更ファイル**: `game.py`
- **実装**: `Engine` に `render_to_text(self, tr)` を追加（まずは空で `pass`）。`render()` 側は変更しない。
- **検証**: `Engine` インスタンスで `render_to_text(tr)` がエラーなし。

### Step 13 — マップのテキスト描画（壁/床）
- **変更ファイル**: `game.py`（`render_to_text` 内）
- **実装**: `engine.map` のタイルを `TILE_WALL='#'`, `TILE_FLOOR='.'` 等（`constants.py`）で `tr.draw_tile` する。
- **検証**: テキストモードでマップが `#`/`.` として出力される。

### Step 14 — エンティティのテキスト描画
- **変更ファイル**: `game.py`
- **実装**: プレイヤー `@`、モンスターは種別最初の1文字を `tr.draw_tile`（敵は赤系色）。
- **検証**: `@` が1箇所、モンスター文字が描画される。

### Step 15 — HUD（HP/MP）のテキスト描画
- **変更ファイル**: `game.py`
- **実装**: 画面上段に `HP: 30/40 MP: 10/20` のような文字列を `draw_text`。
- **検証**: present 出力に `HP:` を含む。

### Step 16 — メッセージログのテキスト描画
- **変更ファイル**: `game.py`
- **実装**: 最後の数行を画面下部に `draw_text`（既存 `MessageLog` から取得）。
- **検証**: ログ文字列が下部に表示される。

### Step 17 — テキスト入力（ターンごと）
- **変更ファイル**: `core/text_renderer.py` または `main.py`
- **実装**: 簡易 `get_action()` で `input("> ")` から `w/a/s/d` 等を読み、`{"move":(dx,dy)}` 辞書を返す。
- **検証**: 入力 `w` で `{"move":(0,-1)}` が返る。

### Step 18 — 入力をエンジンアクションへ接続
- **変更ファイル**: `game.py`
- **実装**: 返されたアクションを既存 `InputHandler` または `TurnQueue` に渡す最小ループを `run_text_mode(engine)` に書く。
- **検証**: 1ターン進む（プレイヤーが移動する）。

### Step 19 — `main_text.py` エントリ作成
- **変更ファイル**: `main_text.py`（新規）
- **実装**: `tcod`/`pygame` を import せずに `TextRenderer` + `Engine` を初期化し `run_text_mode` を呼ぶ。
- **検証**: `python main_text.py` が import エラーなく開始する（SDLなしでも可）。

### Step 20 — メニューに「テキストモード起動」を追加
- **変更ファイル**: `main.py`
- **実装**: メニュー選択 `3` で `import main_text; main_text.main()` を呼ぶ。
- **検証**: メニュー表示に `3. テキストモードで起動` が出る。

### Step 21 — 単体テスト `tests/test_text_renderer.py`
- **変更ファイル**: `tests/test_text_renderer.py`（新規）
- **実装**: Step 2〜8 の挙動を `assert` する pytest ケース。
- **検証**: `python -m pytest tests/test_text_renderer.py -q` が全 GREEN。

### Step 22 — `game.py` のフォールバックチェーン修正
- **変更ファイル**: `game.py`（末尾 `except` ブロック、1908行付近）
- **実装**: SDL 失敗時 → `get_text_mode_enabled()` が True なら `TextRenderer` で続行、そうでなければ既存の Web サーバー待機。
- **検証**: 意図的に SDL を無効にしてもクラッシュしない。

### Step 23 — ドキュメント `docs/TEXT_MODE.md`
- **変更ファイル**: `docs/TEXT_MODE.md`（新規）
- **実装**: 起動方法・操作キー・制限を3行程度で記載。
- **検証**: ファイルが存在し Markdown として読める。

### Step 24 — テキストモード5ターン動作確認
- **変更ファイル**: なし（検証のみ）
- **実装**: `python main_text.py` で5ターン進め、例外なしで盤面が更新されることを目視/キャプチャ。
- **検証**: 5回の `present()` 出力があり、プレイヤー座標が変化。

---

## フェーズ2（提案②）: アクセシビリティ優先の「やさしい」デフォルト 〔ステップ25〜48〕

### Step 25 — 設定に `accessibility.color_vision` を追加
- **変更ファイル**: `config.yaml`
- **実装**: `accessibility:` 配下に `color_vision: "none"` を追加（値: none/deutan/protan/tritan）。
- **検証**: `get_config('accessibility.color_vision')` → `"none"`。

### Step 26 — `load_design_tokens(variant)` を追加
- **変更ファイル**: `core/accessibility.py`（新規）
- **実装**: `design_tokens.<variant>.json` を `json.load` して dict を返す（none は `design_tokens.json`）。
- **検証**: `load_design_tokens('protan')` が dict を返す。

### Step 27 — `get_active_tokens()` を追加
- **変更ファイル**: `core/accessibility.py`
- **実装**: config の `color_vision` を見て対応トークンを返す。
- **検証**: config=protan で protan トークンが返る。

### Step 28 — 環境変数 `COLOR_VISION` で自動検出
- **変更ファイル**: `core/accessibility.py`
- **実装**: `os.environ.get("COLOR_VISION")` があればそれを優先。
- **検証**: `COLOR_VISION=deutan python -c "..."` で deutan が返る。

### Step 29 — プラットフォーム非依存のスタブ検出
- **変更ファイル**: `core/accessibility.py`
- **実装**: OS 判別せず常に `"none"` を返す `detect_os_a11y()` を追加（後で拡張用）。
- **検証**: 関数が `"none"` を返す。

### Step 30 — トークンを Web クライアントへ渡す
- **変更ファイル**: `web_server.py`
- **実装**: `/api/tokens` エンドポイントで `get_active_tokens()` の JSON を返す。
- **検証**: `curl localhost:8080/api/tokens` が JSON を返す。

### Step 31 — 難易度プリセットを設定へ追加
- **変更ファイル**: `config.yaml`
- **実装**: `game.difficulty: "normal"` と `difficulty_presets:` を追加（easy/normal/hard の乗数）。
- **検証**: `get_config('game.difficulty')` → `"normal"`。

### Step 32 — `DifficultyManager` を作成
- **変更ファイル**: `core/difficulty.py`（新規）
- **実装**: config から乗数 `player_damage_taken`, `enemy_hp`, `player_regen` を読むクラス。
- **検証**: normal で全乗数 1.0 になる。

### Step 33 — 戦闘ダメージへ難易度を適用
- **変更ファイル**: `systems.py`（`CombatSystem`）
- **実装**: プレイヤー被ダメージに `player_damage_taken` を掛ける（最小1）。
- **検証**: easy で被ダメージが半減するテスト。

### Step 34 — 「やさしい」プリセット値を定義
- **変更ファイル**: `config.yaml`
- **実装**: easy = `{player_damage_taken: 0.5, enemy_hp: 0.8, player_regen: 1.5}` 等。
- **検証**: `get_config('difficulty_presets.easy.player_damage_taken')` → `0.5`。

### Step 35 — 起動時選択画面を追加
- **変更ファイル**: `main.py`
- **実装**: ゲーム起動前に「色覚: none/deutan/protan/tritan」「難易度: easy/normal/hard」を番号入力で選べる簡易画面。
- **検証**: 入力した値が config に反映される。

### Step 36 — 選択の永続化
- **変更ファイル**: `main.py` + `config.py`
- **実装**: 選択を `configure('accessibility.color_vision', v)` 等で保存。
- **検証**: 再起動しても選択が維持される。

### Step 37 — チュートリアル手順データ `tutorial_steps.json`
- **変更ファイル**: `data/tutorial_steps.json`（新規）
- **実装**: `[{"id":1,"text":"WASDで移動"},...]` を数ステップ記述。
- **検証**: `json.load` がリストを返す。

### Step 38 — `TutorialController` を作成
- **変更ファイル**: `core/tutorial_controller.py`（新規）
- **実装**: 現在ステップを保持し `advance()` / `current()` を提供。
- **検証**: `advance()` で次のテキストが返る。

### Step 39 — チュートリアルを Web に表示
- **変更ファイル**: `web_game_client.html`
- **実装**: `/api/tutorial` から手順を取得し、画面上部にオーバーレイ表示。
- **検証**: ページロードで1ステップ目が表示される。

### Step 40 — 常時コントロールガイドのトグル
- **変更ファイル**: `input_handler.py` または `game.py`
- **実装**: キー `?` で画面下部の操作ガイド表示を ON/OFF（既存ガイドを再利用）。
- **検証**: `?` を押すとガイドが消える/出る。

### Step 41 — 高コントラストテーマ `design_tokens.high_contrast.json`
- **変更ファイル**: `design_tokens.high_contrast.json`（新規）
- **実装**: 背景黒・文字白・境界線明るい等の単純なトークン。
- **検証**: `load_design_tokens('high_contrast')` が dict を返す。

### Step 42 — Web のフォントサイズ設定
- **変更ファイル**: `config.yaml` + `web_server.py`
- **実装**: `accessibility.font_scale: 1.0` を `/api/tokens` に含める。
- **検証**: JSON に `font_scale` を含む。

### Step 43 — `?a11y=` クエリ強制指定
- **変更ファイル**: `web_game_client.html` + `web_server.py`
- **実装**: URL の `?a11y=deutan` でトークンを上書き。
- **検証**: `?a11y=protan` で protan トークンが適用される。

### Step 44 — キーボード Only ナビ保証
- **変更ファイル**: `web_game_client.html`（CSS/JS）
- **実装**: `:focus` に明確なアウトラインを付与（既存 `ui-a11y.js` を活用）。
- **検証**: Tab キーで全 UI がフォーカス可能（目視チェックリスト）。

### Step 45 — アクセシビリティ設定の単体テスト
- **変更ファイル**: `tests/test_accessibility.py`（新規）
- **実装**: Step 26/27/32 のロードと乗数を assert。
- **検証**: `pytest tests/test_accessibility.py` が GREEN。

### Step 46 — `accessibility_report.md` 作成
- **変更ファイル**: `docs/accessibility_report.md`（新規）
- **実装**: 対応オプション一覧を箇条書き。
- **検証**: ファイルが存在。

### Step 47 — README のアクセシビリティ節を更新
- **変更ファイル**: `README.md`
- **実装**: 「色覚対応/難易度/チュートリアル」の3行説明を追加。
- **検証**: 該当セクションが存在。

### Step 48 — 手動統合確認（easy + deutan）
- **変更ファイル**: なし
- **実装**: easy + deutan で起動し、トークン適用とゲームクリア可能（数階層）を確認。
- **検証**: 被ダメージ半減と色トークンが反映。

---

## フェーズ3（提案③）: ワンタッチWeb起動＋描画ダウングレード＋タッチ 〔ステップ49〜72〕

### Step 49 — `launch_browser()` を追加
- **変更ファイル**: `web_server.py`
- **実装**: `import webbrowser; webbrowser.open("http://localhost:8080")` する関数。
- **検証**: 関数呼び出しでブラウザが開く（または例外を握りつぶす）。

### Step 50 — `--open` CLI フラグ
- **変更ファイル**: `main.py`
- **実装**: 起動時に `--open` があれば `launch_browser()` を呼ぶ。
- **検証**: `--open` でブラウザ起動処理が呼ばれる。

### Step 51 — Web サーバーをバックグラウンド起動
- **変更ファイル**: `main.py`
- **実装**: メニュー1で SDL 前に `threading.Thread(target=start_web_server).start()`。
- **検証**: メニュー選択でサーバースレッドが開始される。

### Step 52 — `detect_graphics()` ヘルパ
- **変更ファイル**: `web_server.py`
- **実装**: User-Agent / クエリから `"webgpu"|"webgl2"|"canvas2d"|"none"` を返す関数（サーバ側ヒューリスティクス）。
- **検証**: 関数が文字列を返す。

### Step 53 — WebGL2 失敗時の throw を fallback に変更
- **変更ファイル**: `webgl/renderer.ts`（365行付近）
- **実装**: `if (!gl)` で `throw` せず、後段の Canvas2D レンダラへフォールバックフラグを立てる。
- **検証**: WebGL2 非対応環境でも例外が出ない（目視/コンソールに fallback ログ）。

### Step 54 — `canvas2d_renderer.ts` 最小実装
- **変更ファイル**: `webgl/canvas2d_renderer.ts`（新規）
- **実装**: `getContext('2d')` で矩形＋テキストを描く `present()` のみ。
- **検証**: TypeScript が構文エラーなくパース（ビルド不可なら目視）。

### Step 55 — WebGPU 可用性検出
- **変更ファイル**: `web_game_client.html`（JS）
- **実装**: `if ('gpu' in navigator)` でレンダラを選択。
- **検証**: 論理が正しく分岐する（console.log で選択結果）。

### Step 56 — 選択レンダラをサーバーへ通知
- **変更ファイル**: `web_server.py`
- **実装**: `/api/capabilities` で最後に選択されたレンダラ名を保持・返す。
- **検証**: `curl /api/capabilities` がレンダラ名を返す。

### Step 57 — ローディング画面を追加
- **変更ファイル**: `web_game_client.html`
- **実装**: シェーダー/アトラス準備中のプログレスバー（HTML/CSS）。
- **検証**: 初期表示でローディングが出る。

### Step 58 — タッチイベントハンドラ
- **変更ファイル**: `web_game_client.html`（JS）
- **実装**: `touchstart/touchmove/touchend` を既存キーアクションへマップ。
- **検証**: リスナが登録される（目視）。

### Step 59 — オンスクリーン D-pad ボタン
- **変更ファイル**: `web_game_client.html`
- **実装**: モバイル用の方向ボタン（HTML）を追加し、タップで移動。
- **検証**: ボタン要素が存在しクリックで移動する。

### Step 60 — スワイプジェスチャ
- **変更ファイル**: `web_game_client.html`（JS）
- **実装**: touchmove の差分で上下左右を判定し移動。
- **検証**: スワイプでプレイヤーが移動。

### Step 61 — レスポンシブ CSS
- **変更ファイル**: `web_game_client.html`
- **実装**: `<meta viewport>` と `canvas { width:100% }` 等の柔軟レイアウト。
- **検証**: 狭い画面でも崩れない（目視/DevTools）。

### Step 62 — ランディング `index.html`
- **変更ファイル**: `index.html`（新規、または `web_server.py` の `/` で生成）
- **実装**: 最適レンダラを選び、操作説明を表示してゲームへ遷移。
- **検証**: `/` でランディングが表示される。

### Step 63 — 切断時の自動再接続
- **変更ファイル**: `web_game_client.html`（JS）
- **実装**: fetch/WebSocket エラー時に数秒待ってリトライ。
- **検証**: サーバー停止→再開で再接続する。

### Step 64 — FPS ベースの自動品質低下
- **変更ファイル**: `webgl/renderer.ts`
- **実装**: FPS<30 が続けばパーティクル数を半減するフラグ。
- **検証**: 低 FPS で `quality=low` になる。

### Step 65 — 「軽量モード」トグル
- **変更ファイル**: `web_game_client.html` + `webgl/renderer.ts`
- **実装**: DDGI/ブルーム等のシェーダーを無効化する `lite` フラグ。
- **検証**: lite 有効で重いパスが skip される。

### Step 66 — `/api/capabilities` エンドポイント完成
- **変更ファイル**: `web_server.py`
- **実装**: Step 52/56 を統合し、検出結果と選択レンダラを JSON で返す。
- **検証**: `curl /api/capabilities` が `{"detected":"webgl2","selected":"webgl2"}` 風。

### Step 67 — Web スモークテスト
- **変更ファイル**: `tests/test_web_smoke.py`（新規）
- **実装**: サーバー起動→`GET /`→ステータス200を assert。
- **検証**: `pytest tests/test_web_smoke.py` が GREEN。

### Step 68 — README「どこでも遊ぶ」節
- **変更ファイル**: `README.md`
- **実装**: ワンタップ Web 起動とモバイル操作の説明を追加。
- **検証**: セクションが存在。

### Step 69 — ワンコマンド `run.py`
- **変更ファイル**: `run.py`（新規）
- **実装**: 環境を判定（ターミナル/CTF/ブラウザ）→ text モード または web+open を自動選択。
- **検証**: `python run.py` がいずれかのモードで起動する。

### Step 70 — ヘッドレス自動選択テスト
- **変更ファイル**: `tests/test_headless_launch.py`（新規）
- **実装**: GPU/SDL なし環境を想定し text モードが選ばれることを assert（モック）。
- **検証**: `pytest tests/test_headless_launch.py` が GREEN。

### Step 71 — CHANGELOG 追記
- **変更ファイル**: `CHANGELOG.md`
- **実装**: 3機能（テキストモード/アクセシビリティ/ワンタップWeb）を追加項目として記載。
- **検証**: 該当エントリが存在。

### Step 72 — lint / typecheck の最終確認
- **変更ファイル**: なし（検証のみ）
- **実装**: 変更した `.py` に対して `ruff` と `mypy`（設定ファイル通り）を実行し警告を解消。
- **検証**: `ruff .` と `mypy` がエラー0。

---

## 実装の進め方（LLM向け）
1. 必ず **1ステップずつ** 実装し、そのステップの「検証」を満たしてから次へ。
2. 検証に `pytest` が含まれるステップは、テストファイルを先に書いてから本体を実装（TDD）。
3. ステップ間で import エラーが出たら、依存する「前のステップ」だけを確認する（広く探さない）。
4. 72完了時に `python run.py` で「GPUなし→テキストモード」「GPUあり→ブラウザ自動起動＋タッチ操作」の両方が動くことを確認。
