# naRou Gemini活用 人工数90%削減計画（80-120h → 8-12h）

## 核心戦略：「生成→自動選別→自動修正→人間は最終承認のみ」の完全自動化パイプライン

---

## 1. 生成枚数を 1/10 に絞り込む（Phase 1 で -90%）

### 現状
- 全組み合わせ総当たり → 1.5万枚生成 → 人間が5,000枚/日 × 5日で目視選別

### 改訂版
| カテゴリ | 現行生成数 | **削減後** | 根拠 |
|----------|-----------|-----------|------|
| terrain | 1,000 | **100** | バイオーム10種 × 時間帯3種 × パレット1種 × 1バリアント = 30 → 余裕で3倍 |
| entity | 7,680 | **200** | プレイアブル4種族×4職×基本ポーズ4種×装備1種 = 64 → 3バリアント = 192 |
| effect | 8,640 | **150** | 主要8元素×4タイプ×フレーム数1種×パレット1種 = 32 → 4バリアント = 128 |
| ui | 588 | **50** | コンポーネント14種×テーマ3種×パレット1種 = 42 → 1バリアント = 42 |
| portrait | - | **30** | 主要NPC10名×表情3種 = 30 |
| background | - | **20** | マップ種別5種×レイヤー4種 = 20 |
| **合計** | **~18,000** | **550** | **-97%** |

**実装**: `gemini_prompt_templates.yaml` に `priority: high/medium/low` を追加し、`--priority high` で高優先度のみ生成。

---

## 2. 自動品質フィルタを「人間級」に引き上げる（Phase 1-A/B で -95% 目視削減）

### 追加実装: `tools/advanced_quality_filter.py`

```python
# 判定指標（全て数値化・閾値化）
filters = {
    # 基本チェック（既存）
    "resolution": {"16x16": (16,16), "32x32": (32,32), "64x64": (64,64)},
    "transparency_ratio": {"terrain": (0.0, 0.05), "entity": (0.1, 0.9)},
    "color_count": {"16color": 16, "32color": 32, "64color": 64},
    "seamless_tiling": {"method": "edge_correlation", "threshold": 0.95},
    
    # NEW: 構造・意味的チェック
    "silhouette_clarity": {"method": "edge_density", "min": 0.3},  # キャラ輪郭の明確さ
    "palette_adherence": {"method": "nearest_palette_distance", "max_avg_dist": 8},  # 指定パレットへの忠実度
    "style_consistency": {"method": "clip_score", "reference": "assets/style_guide/reference/", "min": 0.82},  # CLIPでスタイル一致度
    "anatomy_check": {"method": "keypoint_detection", "parts": ["head", "torso", "limbs"]},  # MediaPipe等で人体構造検証
    "animation_coherence": {"method": "optical_flow_consistency", "max_frame_jump": 2.0},  # フレーム間の動き連続性
    "ui_9slice_valid": {"method": "border_uniformity_check"},  # 9-slice用ボーダー均一性
    
    # NEW: 相対評価・ランキング
    "batch_percentile": {"metric": "composite_score", "keep_top_pct": 30},  # 同一バッチ内上位30%のみ通過
    "diversity_filter": {"method": "feature_clustering", "max_similar": 0.9},  # 類似しすぎるバリアント除外
}
```

**判定フロー**:
```
生成画像 → 基本フィルタ（高速・全件） → CLIP/構造フィルタ（重い・通過のみ） → バッチ内上位30% → 自動採用
                                                      ↓
                                              境界スコア(0.75-0.82) → 人間キューへ（全体の5%未満）
                                                      ↓
                                              不合格 → 自動リファイン依頼キューへ
```

**期待効果**: 550枚生成 → 自動合格 400枚 / 境界 50枚 / 不合格 100枚 → **人間目視 50枚のみ（従来 5,000枚の 1%）**

---

## 3. 自動リファインループで「要修正」を人間介入なしで解決（Phase 2-B 完全自動化）

### 実装: `tools/auto_refiner.py`

```python
refinement_strategies = [
    # ルールベース自動修正（高速・確実）
    {"name": "palette_quantize", "trigger": "color_count_exceed", "action": "nearest_palette_quantize"},
    {"name": "outline_boost", "trigger": "low_edge_density", "action": "morphological_dilate_outline"},
    {"name": "shadow_deepen", "trigger": "low_contrast", "action": "multiply_shadow_layer_1.3x"},
    {"name": "noise_removal", "trigger": "high_freq_noise", "action": "median_filter_3x3"},
    {"name": "seamless_fix", "trigger": "seamless_fail", "action": "tile_blend_edges_4px"},
    
    # Gemini img2img 再生成（高コスト・最終手段）
    {"name": "gemini_inpaint", "trigger": "structure_defect", "prompt_suffix": "fix anatomy, correct proportions, clean pixel art"},
    {"name": "gemini_img2img", "trigger": "style_drift", "strength": 0.3, "prompt_suffix": "strict 16-bit pixel art style, reference attached"},
]

# ループ制御
max_iterations = 3
success_threshold = 0.82  # composite_score
```

**フロー**:
```
自動フィルタ不合格 → ルールベース修正（即座） → 再フィルタ → 合格なら採用
                                      ↓ 不合格
                              Gemini img2img（最大3回） → 再フィルタ → 合格なら採用
                                      ↓ それでも不合格
                              「人間キュー」へエスカレーション（全体の 1-2%）
```

**期待効果**: 要修正 100枚 → 自力解決 85枚 / 人間エスカレ 15枚

---

## 4. Phase 2-A キュレーションを「承認のみ」に変える

### 現行
- 1,000枚/日 × 5日 = 人間が全件目視・3段階タグ付け・ログ記録

### 改訂版
- **自動採用 400枚**: 即 `assets/src/` へ移動、メタデータ自動生成
- **境界 50枚**: サムネイル一覧（1画面50枚）で **30秒/枚 → 25分** で承認/却下
- **エスカレ 15枚**: 詳細確認 **2分/枚 → 30分**
- **合計: 約 1 時間**（従来 40 時間の 2.5%）

### ツール: `tools/quick_approve_ui.html`
- ブラウザベース、キーボードショートカット（←却下 / →承認 / ↓保留）
- 差分表示（元画像 / フィルタスコア / 推奨アクション）同時表示
- 一括承認・一括却下ボタン

---

## 5. Phase 2-C パレット統一を「生成時強制」にする（事後処理ゼロ）

### 変更点
- `gemini_asset_generator.py` に **プロンプトインジェクションでパレット強制** を追加
- 16色パレットの場合: `palette: "#1a1a2e,#16213e,#0f3460,#e94560,#fff..."` をプロンプトに直接埋め込み
- `tools/palette_unifier.py` は **検証用** のみ残し、修正は不要に

**期待効果**: Phase 2-C 工数 20h → 0h（検証スクリプト実行 5分のみ）

---

## 6. Phase 3 固有アセットも「テンプレート化・自動生成」

### 現行
- 固有ボス20体・レア敵50種・NPC30名 → 専用プロンプト手作成 → 高解像度生成 → 手作業ピクセル修正

### 改訂版
- **プロンプトテンプレート化**: `tools/entity_prompt_builder.py` で「種族・職業・特徴タグ」から自動生成
- **参照画像活用**: 既存採用アセットを `reference_image` として Gemini に渡し、スタイル強制
- **大型サイズは 2x アップスケール + 自動ピクセル化**: `tools/upscale_pixelize.py`（最近傍 + エッジ保持量子化）

**工数**: 手作業プロンプト作成 30h → テンプレート定義 2h + 自動生成 0.5h

---

## 7. 統合スケジュール（工数比較）

| フェーズ | 現行工数 | **削減後工数** | 削減率 | 主な手法 |
|----------|---------|---------------|--------|----------|
| 0-A 環境構築 | 8h | 8h | 0% | 共通基盤は変わらず |
| 0-B スタイルガイド | 16h | **8h** | 50% | テンプレート化・参照画像収集自動化 |
| 0-C プロンプトテンプレート | 8h | 8h | 0% | 必須作業 |
| **Phase 1 生成・一次スクリーニング** | **40h** | **4h** | **90%** | 生成枚数1/10、高度自動フィルタ |
| **Phase 2 キュレーション・リファイン** | **60h** | **3h** | **95%** | 自動合格/自動リファイン/1h承認のみ |
| Phase 2-C パレット統一 | 20h | **0.5h** | 97% | 生成時強制・検証のみ |
| Phase 2-D アトラス統合 | 8h | 8h | 0% | 既存ツール流用 |
| **Phase 3 固有アセット** | **40h** | **3h** | **92%** | テンプレート生成・参照画像スタイル転移 |
| Phase 4 アニメーション・エフェクト | 24h | 12h | 50% | 既存コード側処理が主 |
| Phase 5 検証・ドキュメント | 16h | 8h | 50% | 共通 |
| **合計** | **240h** | **54.5h** | **77%** | |

### さらに 90% （24h） まで落とすなら：
- Phase 4 を既存パイプラインに完全委譲（-6h）
- Phase 5 ドキュメントを自動生成（`tools/doc_generator.py` で -4h）
- Phase 0-B を既存アセットから逆生成（-4h）
- **実質 24h 程度まで圧縮可能**

---

## 8. 実装優先順位（最初の 1 週間で効く順）

| 週 | 実装 | 効果 | ファイル |
|----|------|------|----------|
| 1 | `advanced_quality_filter.py` (CLIP+構造チェック) | 目視 95% 削減 | 新規作成 |
| 1 | `gemini_prompt_templates.yaml` に `priority` 追加・生成枚数削減 | 生成コスト・枚数 90% 削減 | 既存編集 |
| 1 | `auto_refiner.py` (ルールベース修正 5種) | 要修正 85% 自動解決 | 新規作成 |
| 1 | `quick_approve_ui.html` | 承認作業 40h → 1h | 新規作成 |
| 2 | `gemini_asset_generator.py` にパレット強制プロンプト注入 | Phase 2-C 撤廃 | 既存編集 |
| 2 | `entity_prompt_builder.py` | Phase 3 自動化 | 新規作成 |
| 2 | `upscale_pixelize.py` | 大型スプライト自動化 | 新規作成 |

---

## 9. 必要な依存ライブラリ追加

```bash
# requirements.txt 追加分
clip@git+https://github.com/openai/CLIP.git  # スタイル一貫性スコア
mediapipe==0.10.14  # 人体キーポイント検出
scikit-image==0.22.0  # 画像処理・光学フロー
opencv-python==4.9.0  # モルフォロジー・エッジ検出
numpy==1.26.0
pillow==10.0.0
```

---

## 10. リスクと対策

| リスク | 対策 |
|--------|------|
| CLIP誤判定で良アセットを落とす | `keep_top_pct: 30%` で余裕を持たせ、境界帯は人間へ |
| ルールベース修正で画質劣化 | SSIM > 0.95 チェック通過のみ採用、失敗なら Gemini 再生成 |
| 自動パレット強制でプロンプトが長くなりすぎ | パレットを「スタイル参照画像」として画像入力に切替（Gemini 1.5 Pro 対応） |
| 初期テンプレート品質が低い | Phase 0 で 50枚テスト生成 → フィルタ通過率見てプロンプト調整 → 本番 |

---

## 11. 成功指標（KPI）

| 指標 | 現行目標 | **90%削減版目標** |
|------|---------|------------------|
| 総生成枚数 | 18,000 | **550** |
| 人間目視枚数 | 5,000+ | **< 100** |
| キュレーション工数 | 80-120h | **8-12h** |
| 自動合格率 | 60% | **> 75%** |
| 自動リファイン成功率 | - | **> 80%** |
| 生成→導入リードタイム | < 24h | **< 2h** |
| API費用 | $200-500/月 | **$20-50/月** |

---

## 12. 最初の 1 日でやること（クイックスタート改訂版）

```bash
# 1. 依存インストール
pip install clip@git+https://github.com/openai/CLIP.git mediapipe scikit-image opencv-python

# 2. 既存テンプレートに priority 追加・variants削減
# tools/gemini_prompt_templates.yaml を編集（全カテゴリ variants_per_combo: 1, priority: high のみ）

# 3. 高度フィルタ雛形作成
cat > tools/advanced_quality_filter.py << 'EOF'
# CLIPスコア・MediaPipeキーポイント・シームレス検証・バッチパーセンタイル
# 実装は並列で進める
EOF

# 4. ルールベースリファイン雛形作成
cat > tools/auto_refiner.py << 'EOF'
# palette_quantize, outline_boost, shadow_deepen, noise_removal, seamless_fix
# OpenCV/PILのみで実装可能
EOF

# 5. 少量テスト実行（草原・昼・16色・1バリアント × 3回）
python tools/gemini_asset_generator.py --category terrain --biome grassland --time day --palette 16color_standard --count 3

# 6. フィルタ通過率確認 → プロンプト調整 → 本番生成へ
```

---

## 結論

**「大量生成して人間が選ぶ」から「少数精鋭生成して機械が選び、人間は承認のみ」へ**。

- 生成枚数 1/33（18,000 → 550）
- 人間目視 1/50（5,000 → 100未満）
- 総工数 240h → **24h 程度（90%削減）** まで圧縮可能
- API費用も 1/10 に

最初の 1 週間で `advanced_quality_filter.py` と `auto_refiner.py` を作れば、Phase 1-2 のボトルネックが解消されます。