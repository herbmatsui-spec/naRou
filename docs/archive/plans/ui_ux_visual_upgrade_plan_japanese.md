# naRou 商用ビジュアル刷新 実装計画書（フェーズ1〜4）

## 概要
本計画は、naRou: Masterpiece Edition の UI/UX・グラフィックス・ビジュアル面を商用レベルへ引き上げるための9提案を、実装担当AIが順次実行できるようフェーズ化したものです。各フェーズは前フェーズの成果物に依存します。

---

## フェーズ1：基盤構築（提案1・5）
**目的**: 全ビジュアル作業の前提となるアセットパイプラインとデザインシステムを整備する。

### 1-A. アセットビルドパイプライン（提案1）
- **成果物**: `tools/build_assets.py`, `tools/asset_manifest.json`, `assets/src/*.ase`（ソース原画）
- **手順**:
  1. `assets/src/` に Aseprite ソース（terrain/entity/object/effect 各カテゴリ）を配置する規約を定義。
  2. Pillow ベースの自作アトラス結合スクリプト `tools/build_atlas.py` を作成。入力: `assets/src/**/*.png`、出力: `assets/tiles/16x16/`, `32x32/`, `64x64/` のアトラスPNG + `tileset_*_*.json`（UV座標・バリアント・アニメーションフレーム数）。
  3. `tileset_def.json` に `animated`/`frames`/`variants` フィールドを拡張し、`TileRegistry.get_animation_frame()` が既に持つ仕組みと整合。
  4. `tools/validate_assets.py` で「定義済み全タイルIDがアトラスに存在するか」を検証。
- **受入基準**: プレースホルダー（86バイト）を廃し、実アートが `web_game_client.html` に描画されること。CIで `python tools/build_assets.py` が成功すること。

### 1-B. 統一デザインシステム（提案5）
- **成果物**: `design_tokens.json`, `web/theme.css`（CSSカスタムプロパティ）, `core/palette.py`（tcod用RGBタプル）
- **手順**:
  1. `design_tokens.json` にセマンティックカラー（danger/warning/success/mana/stamina/gold/legendary等）、スペーススケール、角丸半径、フォント階層、z-indexレイヤーを定義。
  2. `web_game_client.html` の `:root` 変数を `theme.css` へ外部化し、トークンから自動生成するビルドステップを追加。
  3. `web/` にテーマ切替（dark / high-contrast / colorblind-protan-deutan-tritan / sepia）のCSSクラスを実装し、設定を `ConfigManager` に保存。
  4. `core/palette.py` に同一トークンを RGB タプルで出力し、tcod描画とWebの視覚的パリティを担保。
- **受入基準**: Webとtcod両方で同一トークンが反映され、テーマ切替が動作すること。

---

## フェーズ2：コアゲームフィール（提案2・3・4）
**目的**: 探索・戦闘の体感を決めるライティング・アニメーション・Web UI を刷新する。

### 2-A. ダイナミックライティング & 視界（提案2）
- **対象**: `demos/lib/LightingSystem.js` を拡張、`web_game_client.html` のレンダラ
- **手順**:
  1. Python側 `fov.py` に再帰的シャドウキャスティングを実装し、`/api/state` の `light_map`（0-1）をサーバーが計算して送信。
  2. `LightingSystem.js` を「光源リスト + light_map」から乗算ブレンドへ改修。光源は減衰・色温度・揺らぎ（ノイズ）を持つ。
  3. 敵ユニットに視界コーンを追加（サーバーが `visible_to_enemy` フラグを付与）。
  4. ポストプロセス（`PostProcessManager.js`）にブルーム・ビネット・深度別カラーグレーディングを追加。
- **受入基準**: 壁裏が暗転し、松明周辺のみ光照る。ブルームで魔法が発光して見える。

### 2-B. アニメーションジュース（提案3）
- **成果物**: `web/anim/AnimationController.js`, `web/anim/particles.js`（既存 `ParticleSystem.js` 拡張）
- **手順**:
  1. `AnimationController` コンポーネント: ステート（idle/walk/attack/hurt/die）＋フレームデータ＋クロスフェード。エンティティごとに `state`/`frame` を `/api/state` が送信。
  2. ヒットポーズ（描画フリーズ 0.08s）、画面シェイク強度＝ダメージ比（`ScreenShake.js` 既存を活用）、ノックバック放物線を実装。
  3. アニメーションイベント連動パーティクル：着地ダスト・斬撃トレイル・詠唱リング。
  4. UI側：ステータス数値カウントアップ、レア度輝き、クエスト完了トースト。
- **受入基準**: 攻撃時にヒットポーズ＋シェイク＋パーティクルが同期発火する。

### 2-C. モダン Web UI（提案4）
- **成果物**: `web/` を Preact + Signals + Tailwind へ移行。`web/components/*.tsx`
- **手順**:
  1. `web/package.json`, `vite.config.ts` を追加し、`web_game_client.html` をコンポーネント化。
  2. コンポーネント: `VitalsBar`, `Hotbar`, `InventoryGrid`, `SkillTreeView`, `LogConsole`, `DialogModal`。状態は `/api/state` ポーリング（現行300ms）を Signals で保持。
  3. a11y: 全操作のキーボードナビ、ARIAラベル、フォーカストラップ、ログの `aria-live` 読み上げ。
  4. レスポンシブ: サイドバー折りたたみ、48dpタッチ領域、仮想ゲームパッドに `navigator.vibrate` フィードバック。
- **受入基準**: スクリーンリーダーでログが読まれ、スマホ幅でプレイ可能。

---

## フェーズ3：システム深度の可視化（提案6・7・8）
**目的**: 複雑なゲームシステムの理解を助ける戦闘フィードバック・音声・メタUI を実装。

### 3-A. 戦闘・スキル視覚フィードバック（提案6）
- **対象**: `web/anim/`, `/api/state` のスキル情報拡張
- **手順**:
  1. 敵/味方スキルの「テレグラフ」ゾーン（赤/青 + カウントダウン）をターン前に描画。
  2. ターゲティング時の AoE プレビュー（円/扇/線/矩形）を `ShapeRenderer` で表示。
  3. コンボUI：フローティング連携アイコン、ダメージ数値のクリティカル色・サイズ強調。
  4. エンティティ上のステータスアイコン（持続リング付）＋バフ/デバフパネルツールチップ。
- **受入基準**: AoEスキル使用中に範囲が可視化され、クリティカルが強調表示される。

### 3-B. オーディオビジュアル統合（提案7）
- **成果物**: `audio/` ディレクトリ（実ファイル）、`web/audio/AudioBus.js`
- **手順**:
  1. `data/audio_config.yaml` に定義済みの BGM・SE・環境音を実ファイル（OGG）として配置。`tools/convert_sounds.py` で統一。
  2. `AudioBus.js` でカテゴリ別ボリューム（Master/BGM/SFX/UI/Ambience）ミキサーUIを実装。
  3. AV同期：歩行SE＝床材質、詠唱＝パーティクルと同一フレーム発火（2-Bのイベントフックを利用）。
  4. 段階的導入として WebAudio 合成（現行）を実ファイルへ置換、立体音響は後段オプション。
- **受入基準**: ミキサーで各カテゴリ音量が独立調整でき、足音が床材質で変わる。

### 3-C. メタUI（提案8）
- **成果物**: `web/meta/SkillTree.tsx`, `web/meta/Codex.tsx`, `web/meta/Fusion.tsx`
- **手順**:
  1. スキルツリー：Canvas/D3 力学グラフ。ズーム/パン、検索、ビルドプランナー（URL共有・保存/読込）、前提スキルハイライト。
  2. クラフティング/融合：ドラッグドロップ釜UI、レシピ発見アニメ、結果プレビュー、失敗リスクメーター。
  3. コデックス：段階アンロックのロア、Three.js によるアーティファクト/モンスター3Dビューア、ドロップテーブル絞り込み。
- **受入基準**: スキルツリーが視覚的に操作でき、ビルドをURL共有できる。

---

## フェーズ4：プラットフォームパリティ（提案9）
**目的**: デスクトップ純粋派向け tcod クライアントの視覚的品質を Web に近づける。

### 4-A. tcod モダン化
- **対象**: `render_tcod.py`（既存描画ルーチン）
- **手順**:
  1. tcod 12+ の SDF フォントレンダリングで任意解像度シャープ表示を有効化。
  2. カスタム GLSL シェーダー（`tcod.console.SDLRenderer`）で CRTスキャンライン・ピクセルパーフェクト・パレットスワップ（Game Boy/CGA/Amiga）を実装。
  3. `core/palette.py`（1-B成果）を tcod 描画ルーチンへ適用し HUD/インベントリ/メニューの共通レイアウト JSON を Web と共有。
  4. 入力パリティ：SDL2 ゲームパッド、マウスホバーツールチップ、コンテキストラジアルメニュー。
- **受入基準**: tcod と Web で同一トークン・同一レイアウトが描画され、パレット切替が動作する。

---

## 優先順位・依存関係まとめ
| フェーズ | 提案 | 依存 | 期間目安 |
|----------|------|------|----------|
| 1 | 1, 5 | なし（最優先） | 1-2週 |
| 2 | 2, 3, 4 | 1-B（トークン） | 1ヶ月 |
| 3 | 6, 7, 8 | 2 | 2-3ヶ月 |
| 4 | 9 | 1-B | 継続 |

**クイックウィン**: フェーズ1の 1-A と 1-B を並行開始。これらが完了すると、以降の全フェーズの視覚表現が初めて実アート・統一トークンで動作するようになります。
