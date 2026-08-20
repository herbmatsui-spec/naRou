# アクセシビリティ対応レポート

`naRou: Masterpiece Edition` は「誰でも面白く遊べる」ことを目指し、以下の
アクセシビリティ機能を提供します。

## 1. 色覚多様性対応（CVD）
- 4 つのカラーバリアントを用意: `none` / `deutan` / `protan` / `tritan`
- 対応トークン: `design_tokens.<variant>.json`
- 高コントラスト版: `design_tokens.high_contrast.json`
- 選択方法:
  - 起動メニューで選択（永続化）
  - 環境変数 `COLOR_VISION=deutan`
  - Web: `?a11y=deutan` クエリ
  - 設定: `config.yaml` の `accessibility.color_vision`

## 2. 難易度プリセット
- `easy` / `normal` / `hard`
- 乗数: `player_damage_taken`（被ダメージ）, `enemy_hp`（敵HP）, `player_regen`（回復）
- easy 例: 被ダメージ 0.5x, 敵HP 0.8x, 回復 1.5x
- `core/difficulty.py` の `DifficultyManager` が管理

## 3. チュートリアル
- `data/tutorial_steps.json` に手順を定義
- `core/tutorial_controller.py` が進行管理
- Web 起動時に最初の手順をオーバーレイ表示

## 4. 操作ガイド
- テキストモード: `?` で画面下部の操作ガイドを ON/OFF
- Web: フォーカス時に明確なアウトライン（キーボード操作可視化）

## 5. フォントサイズ
- `config.yaml` の `accessibility.font_scale` で Web クライアントへ倍率を通知
