# テキスト(ASCII)モード

GPU/SDL が使えない環境（ヘッドレスサーバー、古い PC、ブラウザ不可）でも
`naRou` をプレイできる軽量モードです。ANSI エスケープシーケンスで端末に
ダンジョンを描画します。

## 起動方法

1. 統合メニューから `3. テキストモードで起動`
   ```sh
   python main.py
   # -> 3 を選択
   ```
2. または直接
   ```sh
   python main_text.py
   ```
3. 環境変数 / 設定で自動有効化（SDL 失敗時に自動フォールバック）
   ```sh
   COLOR_VISION=none python -c "from feature_flags import set_text_mode_enabled; set_text_mode_enabled(True)"
   ```
   `config.yaml` の `accessibility.text_mode: true` でも有効化できます。

## 操作

| キー | 動作 |
|------|------|
| `w` `a` `s` `d` / `h` `j` `k` `l` | 移動（上下左右） |
| `.` または Space | 待機（1ターン経過） |
| `q` | 終了 |

## 表示内容

- マップ: `#` 壁 / `.` 床 / `>` 下り階段 / `<` 上り階段 / `~` 水 / `^` 罠
- エンティティ: `@` プレイヤー / `p` ペット / その他 モンスター（頭文字）
- 上部 HUD: `HP:x/y MP:x/y Lv:n D:n`
- 下部: 直近のメッセージログ

## 制限

- グラフィカルな演出（パーティクル、照明、MSDF フォント）は省略されます。
- マウス/タッチ操作はありません。キーボードのみ。
- 画面は 80x50 の固定ビューポート（プレイヤー中心）です。
