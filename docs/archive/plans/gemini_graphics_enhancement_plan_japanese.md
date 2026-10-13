# naRou Gemini活用 グラフィック底上げ 実装計画書

## 概要
Geminiアプリ（画像生成・編集機能）を活用し、naRou: Masterpiece Edition のグラフィック全般を商用レベルへ引き上げるための詳細実装計画。既存の `ui_ux_visual_upgrade_plan_japanese.md`（フェーズ1-4）を補完・拡張し、AI生成アセットの品質管理・一括生成・スタイル統一・継続的改善のワークフローを確立する。

---

## フェーズ0：基盤準備・ワークフロー設計（Week 1-2）

### 0-A. Gemini連携環境構築
- **成果物**: `tools/gemini_asset_generator.py`, `tools/gemini_prompt_templates.yaml`, `assets/gemini_workspace/`
- **手順**:
  1. Google AI Studio / Vertex AI API キーを `.env` に登録（`GEMINI_API_KEY`）
  2. `tools/gemini_asset_generator.py` 作成:
     - 入力: プロンプトテンプレート + パラメータ（サイズ、スタイル、バリアント数）
     - 出力: `assets/gemini_workspace/{category}/{asset_name}_v{version}.png` + メタデータJSON
     - 機能: バッチ生成、リトライ、品質フィルタ（解像度・透過・色数チェック）、自動リネーム
  3. `tools/gemini_prompt_templates.yaml` にカテゴリ別プロンプトテンプレートを定義（後述 0-C）
  4. `assets/gemini_workspace/` 以下に `terrain/` `entity/` `object/` `effect/` `ui/` `background/` `portrait/` ディレクトリを作成
- **受入基準**: `python tools/gemini_asset_generator.py --category terrain --count 50` で50枚の地形アセットが生成・保存される

### 0-B. スタイルガイド・リファレンスアセット作成
- **成果物**: `assets/style_guide/STYLE_GUIDE.md`, `assets/style_guide/reference/*.png`
- **手順**:
  1. 目指すアートスタイルを言語化（ピクセルアート / ハイビット / 16色制限 / アウトライン有無 / 陰影方向 / パレット）
  2. リファレンス画像 20-30枚を収集・整理（パブリックドメイン・CC0・自作含む）
  3. `STYLE_GUIDE.md` に以下を記載:
     - カラーパレット（16色 / 32色 / 64色の階層）
     - 光源方向（左上 45度固定等）
     - アウトライン色・太さルール
     - アニメーションフレーム数標準（idle: 4, walk: 6-8, attack: 6-10）
     - タイルサイズ・グリッド配置規則
     - ネガティブプロンプト集（避けるべき表現）
  4. 既存アセット（`assets/tiles/` 等）との整合性チェック
- **受入基準**: チーム全員が同一スタイルで生成・判断できるドキュメントが完成

### 0-C. カテゴリ別プロンプトテンプレート定義
`tools/gemini_prompt_templates.yaml` に以下を定義:

```yaml
categories:
  terrain:
    base_prompt: |
      {style} pixel art tile, {biome} terrain, {time_of_day} lighting,
      16x16 grid, top-down view, {palette} color palette,
      clean edges, seamless tiling, no noise, sharp details
    params:
      biome: [grassland, forest, desert, snow, swamp, volcanic, crystal, void, dungeon_stone, dungeon_wood]
      time_of_day: [day, night, dawn, dusk, magical_gloom]
      palette: [16color_standard, 16color_autumn, 16color_winter, 32color_rich, 64color_hd]
    negative: "blurry, gradient, anti-aliasing, watermark, text, signature, 3d render, photo, realistic"
    variants_per_combo: 4
    size: "16x16"

  entity:
    base_prompt: |
      {style} pixel art character sprite, {race} {class} {gender},
      {pose} pose, {equipment} equipment, {palette} color palette,
      32x32 or 64x64, transparent background, distinct silhouette
    params:
      race: [human, elf, dwarf, beastkin, undead, construct, slime, dragonkin]
      class: [warrior, mage, rogue, cleric, ranger, alchemist, summoner, berserker]
      gender: [male, female, androgynous]
      pose: [idle_front, idle_back, idle_side, walk_1, walk_2, walk_3, walk_4, attack_1, attack_2, hurt, die]
      equipment: [none, sword, staff, bow, dagger, axe, hammer, shield, robe, armor_light, armor_heavy]
      palette: [16color_standard, 32color_rich]
    negative: "blurry, gradient, anti-aliasing, watermark, text, extra limbs, deformed, asymmetric"
    variants_per_combo: 3
    size: "32x32"

  effect:
    base_prompt: |
      {style} pixel art effect animation, {element} {effect_type},
      {frame_count} frames, {palette} color palette,
      transparent background, loopable, additive blend ready
    params:
      element: [fire, ice, lightning, poison, holy, dark, arcane, physical, blood, wind, earth, water]
      effect_type: [explosion, projectile, aura, buff, debuff, heal, slash, pierce, blast, nova, ring, trail]
      frame_count: [4, 6, 8, 12, 16]
      palette: [16color_standard, 16color_glow, 32color_hdr]
    negative: "blurry, gradient, anti-aliasing, watermark, text, static, non-loopable"
    variants_per_combo: 4
    size: "32x32"

  ui:
    base_prompt: |
      {style} pixel art UI element, {component_type}, {theme} theme,
      {palette} color palette, 9-slice ready, sharp corners
    params:
      component_type: [panel, button, frame, icon_frame, progress_bar, slider, checkbox, radio, tab, tooltip, dialog, inventory_slot, hotbar_slot, skill_icon, item_icon]
      theme: [default, dark, fantasy, magitech, ancient, corrupted, celestial]
      palette: [16color_ui, 32color_ui]
    negative: "blurry, gradient, anti-aliasing, watermark, text, 3d, realistic, photo"
    variants_per_combo: 3
    size: "variable"

  portrait:
    base_prompt: |
      {style} pixel art portrait, {race} {class} {gender},
      {expression} expression, {lighting} lighting, {palette} color palette,
      64x64 or 128x128, bust shot, transparent background
    params:
      race: [human, elf, dwarf, beastkin, undead, construct, dragonkin]
      class: [warrior, mage, rogue, cleric, ranger, alchemist, summoner, berserker, noble, merchant, villain]
      gender: [male, female, androgynous]
      expression: [neutral, happy, angry, sad, surprised, determined, suspicious, confident, weary, maniacal]
      lighting: [neutral, dramatic, rim_light, magical_glow, candlelight]
      palette: [32color_rich, 64color_hd]
    negative: "blurry, gradient, anti-aliasing, watermark, text, full_body, deformed, asymmetric_face"
    variants_per_combo: 3
    size: "64x64"

  background:
    base_prompt: |
      {style} pixel art background, {biome} {time_of_day} {weather},
      parallax layers: {layer_count}, {palette} color palette,
      seamless horizontal, atmospheric perspective
    params:
      biome: [overworld, forest, desert, snow, swamp, volcanic, crystal, void, dungeon, city, ruin, sky_island]
      time_of_day: [day, night, dawn, dusk, eclipse, aurora]
      weather: [clear, rain, snow, fog, sandstorm, ash, magical_storm]
      layer_count: [3, 4, 5]
      palette: [16color_standard, 32color_rich, 64color_hd]
    negative: "blurry, gradient, anti-aliasing, watermark, text, characters, foreground_objects"
    variants_per_combo: 2
    size: "256x144"
```

---

## フェーズ1：大量生成・一次スクリーニング（Week 2-4）

### 1-A. 地形タイル全バイオーム生成
- **対象**: `terrain` カテゴリ全組み合わせ（biome 10 × time_of_day 5 × palette 5 = 250 コンボ × 4 variants = 1,000枚）
- **手順**:
  1. `python tools/gemini_asset_generator.py --category terrain --all-combos`
  2. 生成完了後、`tools/asset_quality_filter.py` で自動スクリーニング:
     - 解像度チェック（16x16 厳守）
     - 透過ピクセル率チェック（地形は原則不透過）
     - 色数チェック（指定パレット色数以内）
     - シームレスタイル検証（上下左右繋がり）
     - 明度ヒストグラムチェック（極端に暗い/明るい除外）
  3. 合格アセットを `assets/src/terrain/` へ移動・リネーム（`terrain_{biome}_{time}_{palette}_v{num}.png`）
  4. 不合格・要修正を `assets/gemini_workspace/terrain/rejected/` へ隔離
- **受入基準**: 全バイオーム・時間帯・パレットで最低3バリアント以上の合格アセット確保

### 1-B. エンティティスプライト生成（主要種族・職業）
- **対象**: `entity` カテゴリ優先組み合わせ（race 8 × class 8 × pose 10 × equipment 5 = 2,560 コンボ × 3 variants = 7,680枚 → 優先度付けで約2,000枚に絞込）
- **優先順位**:
  1. プレイヤーキャラ候補（human/elf/dwarf/beastkin × warrior/mage/rogue/cleric × 全ポーズ × 基本装備）
  2. 主要敵NPC（undead/construct/slime/dragonkin × 基本クラス × idle/hurt/die）
  3. ボス・ユニーク敵（大型サイズ 64x64/128x128 対応）
- **手順**: 1-A と同フロー。アニメーションフレーム整合性チェック追加（歩行サイクルの足位置・体重移動）
- **受入基準**: プレイアブル種族・職業の全基本アクション揃う。ボス用大型スプライト確保。

### 1-C. エフェクトアニメーション生成
- **対象**: `effect` カテゴリ全組み合わせ（element 12 × effect_type 12 × frame_count 5 × palette 3 = 2,160 コンボ × 4 variants = 8,640枚 → 実用的な組み合わせに絞込）
- **重点元素**: fire/ice/lightning/poison/holy/dark/arcane/physical（8元素）
- **重点タイプ**: explosion/projectile/aura/buff/debuff/heal/slash/trail（8タイプ）
- **手順**: ループ可否・加算合成対応・フレーム間整合性を自動検証
- **受入基準**: 全主要元素・タイプでループ可能なアニメーション確保

### 1-D. UIコンポーネント生成
- **対象**: `ui` カテゴリ全組み合わせ（component_type 14 × theme 7 × palette 2 = 196 コンボ × 3 variants = 588枚）
- **手順**: 9-slice対応（枠・角・中心分離）検証。ステート別（normal/hover/pressed/disabled/focus）生成
- **受入基準**: 全UIコンポーネントで全テーマ・ステート揃う

---

## フェーズ2：品質向上・スタイル統一・手作業修正（Week 4-8）

### 2-A. 人手によるキュレーション・選別
- **成果物**: `assets/src/` への最終採用アセット、 `assets/gemini_workspace/_curated/`
- **手順**:
  1. 全生成アセットを人間が目視確認（Aseprite/画像ビューアで一括表示）
  2. 評価基準: スタイル適合度 / 独自性 / ゲーム内での視認性 / アニメーション滑らかさ
  3. 採用/却下/要修正の3段階タグ付け（ファイル名に `_A` `_R` `_M` サフィックス）
  4. 採用アセットのみ `assets/src/{category}/` へコピー
  5. 却下理由を `curation_log.csv` に記録（次回プロンプト改善用）
- **工数見積**: 1,000枚/日 × 5日 = 5,000枚処理可能。総生成数約1万枚 → 2週間で完了

### 2-B. 要修正アセットのリファイン（イテラティブ生成）
- **手順**:
  1. `_M` タグのアセットについて、欠点をプロンプトにフィードバック
  2. `tools/gemini_asset_refiner.py` 作成:
     - 入力: 元画像 + 修正指示プロンプト（"アウトラインを濃く" "影を濃く" "色数減らす" 等）
     - Gemini の画像編集（img2img / inpainting）機能を使用
     - 複数バリアント生成 → 再スクリーニング
  3. 修正版を `_M_v2`, `_M_v3` として保存、再評価
  4. 合格すれば採用、不合格なら却下
- **受入基準**: 要修正アセットの 80% 以上を合格ラインへ引き上げ

### 2-C. パレット統一・色数削減（自動化）
- **成果物**: `tools/palette_unifier.py`, 統一済みアセット
- **手順**:
  1. `design_tokens.json`（既存フェーズ1-B成果）のマスターパレットを基準色とする
  2. 全採用アセットを対象に、最近傍色置換でパレット統一
  3. 16色・32色・64色の各ティアで出力
  4. 色数削減による劣化を `tools/visual_diff.py` で検出（SSIM < 0.95 は手動確認）
- **受入基準**: 全アセットが指定ティアのパレット色のみで構成される

### 2-D. アトラス統合・メタデータ生成
- **成果物**: `assets/tiles/{16x16,32x32,64x64}/atlas.png`, `assets/tilesets/tileset_*.json`
- **手順**: 既存 `tools/build_atlas.py`（フェーズ1-A）を拡張し、Gemini生成アセット対応
  - アニメーションメタデータ（フレーム数・ループ・アンカー・ヒットボックス）自動付与
  - バリアント管理（同一IDで複数見た目）
- **受入基準**: `TileRegistry` / `AnimationController` が全アセットを正常読み込み

---

## フェーズ3：ゲーム固有アセット・差別化（Week 6-10 並行）

### 3-A. ユニークボス・レア敵・NPC肖像画
- **対象**: `entity`（大型 64x64/128x128）、`portrait`（64x64/128x128）
- **手順**:
  1. ゲームデザイン文書から「固有ボス 20体」「レア敵 50種」「主要NPC 30名」を抽出
  2. 各々に専用プロンプトを手作成（シルエット・配色・モチーフ指定）
  3. 高解像度生成 → ダウンサンプル → 手作業ピクセル修正（Aseprite）
  4. 複数フェーズ（通常/第2形態/怒り/敗北）分のバリアント生成
- **受入基準**: 全固有キャラに専用スプライト・肖像画・複数フェーズ分が揃う

### 3-B. 環境・背景・パララックスレイヤー
- **対象**: `background` カテゴリ
- **手順**:
  1. マップ種別（ダンジョン階層 / 地上バイオーム / 都市 / 特殊次元）ごとに必要レイヤー数定義
  2. 遠景・中景・近景・前景の4-5レイヤー構成で生成
  3. 水平シームレス検証、視差スクロール速度係数メタデータ付与
  4. 時間経過（昼/夜/魔法の嵐）差分生成
- **受入基準**: 全マップタイプでパララックス背景が動作

### 3-C. アイテムアイコン・スキルアイコン・ステータスアイコン
- **対象**: `ui` の `item_icon` `skill_icon` 拡張
- **手順**:
  1. アイテムマスタ（`data/items/*.yaml`）から必要アイコン数算出（目標 500-1,000種）
  2. カテゴリ別プロンプト（武器/防具/消費/素材/鍵/クエスト/宝珠/書/食料/宝石）
  3. レアリティ別フレーム（common/uncommon/rare/epic/legendary/artifact）統一デザイン
  4. スキルアイコンはエフェクト要素を簡略化し 16x16/32x32 両対応
- **受入基準**: 全実装済みアイテム・スキル・ステータスに専用アイコンが割り当て済み

---

## フェーズ4：アニメーション・エフェクト強化・パイプライン自動化（Week 8-12）

### 4-A. アニメーションフレーム補間・滑らか化
- **成果物**: `tools/animation_interpolator.py`, 補間済みスプライトシート
- **手順**:
  1. Gemini生成のキーフレーム（4-8フレーム）を入力
  2. ピクセルアート専用補間アルゴリズム（最近傍+手動修正ガイド）で中間フレーム生成
  3. 目標フレーム数: idle 8f, walk 12f, attack 10-16f, skill 12-20f
  4. 滑らかさ検証: フレーム間ピクセル差分・動きベクトルの連続性チェック
- **受入基準**: 全主要アニメーションが目標フレーム数・滑らかさ達成

### 4-B. パーティクル・エフェクト高度化
- **手順**:
  1. Gemini生成の単体エフェクトフレームを素材として、コード側 `ParticleSystem.js` でプロシージャル合成
  2. パラメータ: 発生率・寿命・重力・風・色変化・スケール変化・回転・加算/乗算ブレンド
  3. プリセット化: `data/particle_presets.yaml` に定義
  4. エディタ連携: `tools/particle_editor.html` でリアルタイム調整・エクスポート
- **受入基準**: 主要スキル・環境エフェクトがプロシージャルで豊かに表現される

### 4-C. 継続的生成パイプライン（CI/CD統合）
- **成果物**: `.github/workflows/gemini_assets.yml`, `tools/asset_regression_test.py`
- **手順**:
  1. 週次スケジュール / 新規データ追加時 / 手動トリガーで自動生成実行
  2. 差分検知: `data/` 変更時に該当カテゴリのみ再生成
  3. リグレッションテスト: 既存採用アセットとの視覚的差分検出（意図しない劣化防止）
  4. 生成レポートを GitHub Actions Summary / Discord Webhook へ通知
  5. 承認フロー: 自動合格 → `assets/src/` 直マージ / 要確認 → PR 作成
- **受入基準**: 新規コンテンツ追加時に対応アセットが自動生成・検証・マージされる

---

## フェーズ5：検証・最適化・ドキュメント整備（Week 10-12）

### 5-A. 視覚的品質ベンチマーク
- **成果物**: `docs/graphics_quality_report.md`, スクリーンショット比較集
- **手順**:
  1. Before/After 比較: プレースホルダー版 vs 現行版 vs Gemini強化版
  2. 指標: フレームレート影響 / VRAM使用量 / ロード時間 / 視認性（コントラスト比） / スタイル一貫性
  3. プレイテスト: 実プレイ 30分での主観評価（没入感 / 見やすさ / 飽きなさ）
- **受入基準**: 全指標で現行版以上、商用インディーゲーム水準以上

### 5-B. パフォーマンス最適化
- **手順**:
  1. アトラスパッキング最適化（空白削減・回転許可・回転メタデータ付与）
  2. 未使用アセット削除（`tools/find_unused_assets.py` で静的解析）
  3. 圧縮: WebP lossless / Basis Universal への変換検討（WebGL対応）
  4. 遅延読み込み: マップ別・シーン別アセットバンドル分割
- **受入基準**: 初期ロード < 3秒、VRAM < 512MB、60fps 維持（推奨スペック）

### 5-C. ドキュメント・ナレッジベース整備
- **成果物**: `docs/GEMINI_ASSET_WORKFLOW.md`, `docs/PROMPT_ENGINEERING_GUIDE.md`, `docs/ASSET_NAMING_CONVENTION.md`
- **内容**:
  - Gemini生成からゲーム導入までの全ワークフロー図解
  - 効果的なプロンプトパターン・アンチパターン集（実例付き）
  - 命名規則・ディレクトリ構造・メタデータスキーマ
  - トラブルシューティング FAQ
  - 新規メンバー向けオンボーディング手順

---

## 予算・コスト試算

| 項目 | 見積もり | 備考 |
|------|----------|------|
| Gemini API (画像生成) | $200-500/月 | 生成枚数約2万枚 × $0.01-0.03/枚相当 |
| Gemini API (画像編集) | $100-200/月 | リファイン用 |
| 人手キュレーション | 80-120時間 | 時給換算 $2,000-3,000 相当 |
| 開発ツール作成 | 40-60時間 | 自動化スクリプト群 |
| **合計** | **$2,500-4,000 相当** | 内部工数含む |

※ Gemini Free Tier / プロモーションクレジット活用で実質コスト削減可能

---

## リスク・対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| 生成品質のバラつき | 高 | 高 | 多バリアント生成 + 自動フィルタ + 人手選別の3段階 |
| スタイル不統一 | 高 | 中 | 厳格なスタイルガイド + パレット強制統一 + リファレンス画像活用 |
| API制限・コスト超過 | 中 | 中 | バッチ制御・キャッシュ・ローカル代替（Stable Diffusion等）検討 |
| 著作権・ライセンス問題 | 低 | 低 | Gemini利用規約確認・商用利用可確認・生成ログ保存 |
| 既存パイプラインとの衝突 | 中 | 低 | フェーズ1のアセットパイプライン完成後に本格開始 |

---

## マイルストーン・スケジュール

| 週 | マイルストーン | 成果物 |
|----|----------------|--------|
| 1-2 | 環境構築・スタイルガイド・テンプレート完成 | `tools/gemini_*.py`, `STYLE_GUIDE.md`, `prompt_templates.yaml` |
| 2-4 | 大量生成・一次スクリーニング完了 | `assets/gemini_workspace/` に約1.5万枚生成済み |
| 4-6 | キュレーション・リファイン・パレット統一完了 | `assets/src/` に採用アセット約3,000枚 |
| 6-8 | アトラス統合・ゲーム導入・動作確認完了 | `web_game_client.html` で実アート描画確認 |
| 8-10 | 固有ボス・背景・アイコン等ゲーム固有分完了 | 全コンテンツに専用アセット割当完了 |
| 10-12 | アニメーション補間・エフェクト強化・CI統合完了 | 自動生成パイプライン稼働・品質レポート提出 |

---

## 既存計画との整合性

| 既存フェーズ | 本計画の対応フェーズ | 依存関係 |
|-------------|---------------------|----------|
| フェーズ1 (1-A, 1-B) | フェーズ0-1 前半 | アセットパイプライン・デザイントークン完成後に本格開始推奨 |
| フェーズ2 (2-A, 2-B, 2-C) | フェーズ1-2 並行 | ライティング・アニメーション・UI実装と並行してアセット投入 |
| フェーズ3 (3-A, 3-B, 3-C) | フェーズ3-4 | システム深度可視化に必要なエフェクト・UIアイコンを優先生成 |
| フェーズ4 (4-A) | 継続的改善 | tcod側パレット統一で恩恵を受ける |

---

## クイックスタート（最初の1日でやること）

```bash
# 1. APIキー設定
echo "GEMINI_API_KEY=your_key_here" >> .env

# 2. ツール雛形作成
mkdir -p tools assets/gemini_workspace/{terrain,entity,object,effect,ui,background,portrait}
touch tools/gemini_asset_generator.py tools/gemini_prompt_templates.yaml

# 3. スタイルガイド雛形作成
mkdir -p assets/style_guide/reference
cat > assets/style_guide/STYLE_GUIDE.md << 'EOF'
# naRou アートスタイルガイド

## 目標スタイル
- 16-bit era JRPG 風ピクセルアート（クロノトリガー / FF6 / ロマサガ2 風）
- 16色基本パレット + アクセント色
- 左上45度光源、ドット単位の手描き感

## パレット（16色基本）
# ここに16進カラーコード列挙

## 禁止事項
- アンチエイリアス（手動で入れる場合のみ）
- グラデーション塗り
- 3Dレンダリング風陰影
EOF

# 4. 最初のテスト生成
python tools/gemini_asset_generator.py --category terrain --biome grassland --time day --palette 16color_standard --count 4
```

---

## 成功指標（KPI）

| 指標 | 目標値 | 測定方法 |
|------|--------|----------|
| アセット採用率 | > 60% | 採用枚数 / 生成総枚数 |
| 手作業修正率 | < 20% | 修正必要枚数 / 採用枚数 |
| 生成→導入リードタイム | < 24時間 | 新規データ追加からアトラス反映まで |
| 視覚的品質スコア | > 4.0/5.0 | プレイテストアンケート平均 |
| スタイル一貫性スコア | > 4.5/5.0 | 開発チーム内評価 |
| VRAM使用量 | < 512MB | ブラウザDevTools / プロファイラ |
| 初期ロード時間 | < 3秒 | Lighthouse / 実測 |

---

## 付録：プロンプトエンジニアリング Tips（実践編）

### 良いプロンプトの構成要素
```
[スタイル] + [主題詳細] + [技術仕様] + [品質指定] + [ネガティブ]
```

### 実例比較
```
❌ 悪い: "fireball sprite"
✅ 良い: "16-bit pixel art fireball explosion animation, 8 frames, orange yellow red palette, transparent background, loopable, additive blend, sharp pixel edges, no blur, no gradient, game asset"
```

### カテゴリ別コツ
- **地形**: "seamless tiling" "top-down" "grid aligned" を必ず入れる
- **キャラ**: "distinct silhouette" "readable at small size" "consistent proportions"
- **エフェクト**: "loopable" "additive blend ready" "frame count specified"
- **UI**: "9-slice ready" "sharp corners" "multiple states"
- **背景**: "parallax layers" "horizontal seamless" "atmospheric perspective"

### 反復改善サイクル
1. 生成 → 2. 失敗パターン分類 → 3. ネガティブプロンプト追加 / ベースプロンプト修正 → 4. 再生成
2-3回のイテレーションで劇的に改善することが多い

---

*作成日: 2026-08-19*
*バージョン: 1.0*
*担当: グラフィック強化タスクフォース*
