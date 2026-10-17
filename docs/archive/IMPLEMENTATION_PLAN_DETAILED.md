# 詳細実装計画書 — 偏執的グラフィック強化 9フェーズ・72ステップ

> メタ計画書（`IMPLEMENTATION_META_PLAN.md`）に基づき作成。
> 各フェーズ 8 ステップ、合計 72 ステップ。
> 進捗は `[ ]` → `[x]` で管理。ブランチ: `feat/phase-X-step-Y`

---

## Phase 1: 動的ライティング・シャドウシステム

**目標**: WebGL2 + カスタムシェーダーでタイル単位の動的光源・リアルタイム影・ボリュームライトを実装。

**前提**: Three.js r160+ 導入、WebGL2 コンテキスト利用可能。

### Step 1.1: レンダリング基盤の WebGL2 移行
- [ ] Task: Three.js を r160 以上にアップグレード、WebGL2 強制
- [ ] Task: 既存 HTML デモの `canvas` を `WebGLRenderer({ antialias:true })` に差し替え
- [ ] Task: 既存の CSS grid-map を `OrthographicCamera` 付きシーンにマッピング
- **成果物**: `src/render/Renderer.ts` / `demo_scene_template.html`
- **受入**: 既存 24 シーンのうち 3 つが WebGL 描画で 60fps

### Step 1.2: タイルジオメトリ・アトラス生成
- [ ] Task: 各タイルを 3D ボックス/プレーンに変換するビルダー作成
- [ ] Task: テクスチャアトラス（壁/床/装飾）を 2048×2048 で生成
- [ ] Task: タイル → UV インデックス マッピング定義
- **成果物**: `src/render/TileMesh.ts`, `assets/tiles_atlas.png`
- **受入**: 全タイル種が正しくテクスチャマップされる

### Step 1.3: 点光源・スポットライト管理システム
- [ ] Task: `LightManager` クラス（光源追加/削除/更新）
- [ ] Task: 松明・魔法・溶岩用プリセット定義
- [ ] Task: 光源ごとの影響半径・減衰カーブ設定
- **成果物**: `src/render/LightManager.ts`, `data/light_presets.yaml`
- **受入**: シーン内で 8 光源が同時処理される

### Step 1.4: 影マップ（Shadow Map）実装
- [ ] Task: 深度シャドウマップ（2048²）生成パス追加
- [ ] Task: PCF ソフトシャドウサンプリング
- [ ] Task: バイアス/ノーマルバイアス調整でアクネ除去
- **成果物**: `src/render/ShadowPass.ts`
- **受入**: 壁・床にキャラ影が落下、シャドウアクネなし

### Step 1.5: SSAO / レイマーチング AO
- [ ] Task: 深度 + 法線バッファ出力 G-Buffer
- [ ] Task: SSAO カーネルサンプリング（16 サンプル）
- [ ] Task: レイマーチング AO による凹部陰影補完
- **成果物**: `src/render/SSAOPass.ts`
- **受入**: 凹型地形の隅が暗くなり立体感向上（SSIM 差分確認）

### Step 1.6: ボリュームライト（ゴッドレイ）
- [ ] Task: 放射状ブラー（Radial Blur）パス追加
- [ ] Task: 遮蔽バッファからの光条生成
- [ ] Task: 霧/魔法エフェクトへの合成
- **成果物**: `src/render/VolumetricLightPass.ts`
- **受入**: 祭壇ジュアの光が大気中に可視化される

### Step 1.7: 曜日・時間帯・天候別ライティング
- [ ] Task: 環境光カラーグラデーション（昼夜）定義
- [ ] Task: 天候（晴/雨/嵐）別アンビエント設定
- [ ] Task: `world_state.yaml` と連携し動的切替
- **成果物**: `src/render/EnvironmentLighting.ts`, `data/daynight_cycle.yaml`
- **受入**: シーン起動時に天候・時間帯が反映される

### Step 1.8: 統合・ベンチマーク
- [ ] Task: 全 24 シーンのライティング統合
- [ ] Task: フレーム時間プロファイル（GPU/CPU 分離）
- [ ] Task: レファレンス画像との SSIM 比較テスト追加
- **成果物**: `benches/lighting_bench.json`, CI テスト
- **受入**: 全シーン 60fps、GPU ms < 12ms

**Phase 1 依存**: → Phase 2 (パーティクル光源利用), Phase 4 (ポスト統合)

---

## Phase 2: パーティクル・エフェクトフレームワーク

**目標**: GPU インスタンシングで 10 万パーティクル/フレーム、物理ベースシミュレーション。

**前提**: Phase 1 完了、Three.js + WebGL2。

### Step 2.1: GPU パーティクル基盤
- [ ] Task: `InstancedBufferGeometry` によるポイントスプライト
- [ ] Task: 頂点シェーダー内での位置更新（Transform Feedback 代替）
- [ ] Task: ライフサイクル（生成→更新→死亡）状態管理
- **成果物**: `src/particles/GPUParticleSystem.ts`
- **受入**: 1 万パーティクルが 60fps で動作

### Step 2.2: 物理シミュレーション（風/重力/渦）
- [ ] Task: ベクトル場（風場）ノイズ生成
- [ ] Task: 重力・浮力・ドラッグ計算
- [ ] Task: 渦（Curl Noise）による乱流
- **成果物**: `src/particles/Physics.ts`
- **受入**: エーテル風が自然な渦を描く

### Step 2.3: エミッター DSL（YAML）
- [ ] Task: エミッター定義スキーマ策定
- [ ] Task: 「火花→重力→消滅」等の挙動データ駆動化
- [ ] Task: バリデーターとホットリロード
- **成果物**: `src/particles/EmitterDSL.ts`, `data/emitters/*.yaml`
- **受入**: YAML のみで新エフェクト追加可能

### Step 2.4: 衝突判定・地形相互作用
- [ ] Task: タイルマップとのレイキャスト衝突
- [ ] Task: 床着弾時のスプラッシュ生成
- [ ] Task: 壁反射ベクトル計算
- **成果物**: `src/particles/Collision.ts`
- **受入**: 爆発が床に沿って広がる

### Step 2.5: レンダリング（加算/アルファ）
- [ ] Task: 加算合成ブレンドモード
- [ ] Task: 深度ソート（半透明対応）
- [ ] Task: ソフトパーティクル（深度フェード）
- **成果物**: `src/particles/ParticleRenderer.ts`
- **受入**: 魔法エフェクトが発光感を持つ

### Step 2.6: LOD ・カリング
- [ ] Task: カメラ距離によるパーティクル数動的調整
- [ ] Task: 画面外エミッターのポーズ
- [ ] Task: 重要度（優先度）ベース維持数
- **成果物**: `src/particles/LODController.ts`
- **受入**: 遠景で 30% パーティクル削減、見栄え維持

### Step 2.7: エフェクトライブラリ整備
- [ ] Task: 爆発/魔法/血飛沫/風/霧/火花 を 24 シーン分定義
- [ ] Task: プレハブ化とプレビュー HTML
- [ ] Task: デモ `particle_demo.html` 拡張
- **成果物**: `data/emitters/*.yaml`, `demos/particle_showcase.html`
- **受入**: 全シーンに最低 1 エフェクト配置

### Step 2.8: 統合・プロファイル
- [ ] Task: 全シーンで 10 万パーティクル目標検証
- [ ] Task: GPU メモリ使用量監視
- [ ] Task: ベンチマーク自動化
- **成果物**: `benches/particle_bench.json`
- **受入**: 戦闘シーンで 10 万 / 60fps

**Phase 2 依存**: → Phase 4 (ポスト適用), Phase 7 (音連動)

---

## Phase 3: アニメーションスプライトシステム

**目標**: スプライトアトラス自動生成 + スケルタルアニメ + ステートマシン。

**前提**: Phase 1 完了（ライティング反映先）。

### Step 3.1: スプライトアトラス自動生成
- [ ] Task: Aseprite/LDtk エクスポート → ビルド時 PNG+JSON 結合
- [ ] Task: パッキング最適化（最大 4096²）
- [ ] Task: アトラス差分ビルド（変更のみ再生成）
- **成果物**: `tools/atlas_builder.py`, `assets/sprites/*.json`
- **受入**: 全キャラ 1 アトラスに収束、差分ビルド < 5s

### Step 3.2: スケルタルアニメ導入
- [ ] Task: Spine/Rive ランタイム統合（または自製ボーン）
- [ ] Task: ボーン階層・IK ソルバ
- [ ] Task: 装備差分（武器/防具オーバーレイ）
- **成果物**: `src/anim/SkeletalAnimator.ts`
- **受入**: キャラが歩行時に手足が追従

### Step 3.3: ステートマシン（ブレンドツリー）
- [ ] Task: Idle/Walk/Attack/Death/Hurt 状態定義
- [ ] Task: クロスフェード・ブレンドツリー
- [ ] Task: 優先度ベース割り込み
- **成果物**: `src/anim/StateMachine.ts`
- **受入**: 攻撃中に被弾しても自然に遷移

### Step 3.4: フレーム同期（60fps 固定）
- [ ] Task: 固定タイムステップ更新ループ
- [ ] Task: 入力遅延 1 フレーム以内保証
- [ ] Task: デルタタイム補間
- **成果物**: `src/anim/FrameSync.ts`
- **受入**: 異デバイスで同一アニメ速度

### Step 3.5: 色置換・装備差分システム
- [ ] Task: パレットスワップ（チームカラー等）
- [ ] Task: 装備スロットごとのスプライト合成
- [ ] Task: 動的リロード（装備変更即反映）
- **成果物**: `src/anim/PaletteSwap.ts`
- **受入**: 武器持ち替えが即座に反映

### Step 3.6: キャラ/モンスター定義データ
- [ ] Task: `data/monsters.yaml` とアニメ定義紐付
- [ ] Task: プレイヤー/シエル専用モーション
- [ ] Task: 表情/ポーズ差分
- **成果物**: `data/animations.yaml`
- **受入**: 全モンスターに歩行/攻撃アニメ

### Step 3.7: デモ・統合
- [ ] Task: `scene_*.html` の絵文字をスプライトに差し替え
- [ ] Task: アニメプレビュー HTML
- [ ] Task: タイトル画面デモ拡張
- **成果物**: `demos/animation_showcase.html`
- **受入**: 3 シーンでキャラがアニメ再生

### Step 3.8: 最適化・テスト
- [ ] Task: スキン描画バッチング
- [ ] Task: アニメキャッシュ（GPU インスタンシング）
- [ ] Task: 単体テスト（ステート遷移）
- **成果物**: `tests/anim.test.ts`
- **受入**: 50 キャラ同時描画 60fps

**Phase 3 依存**: → Phase 4 (ポスト適用), Phase 6 (UIアイコン)

---

## Phase 4: ポストプロセス・シェーダースタック

**目標**: Fullscreen Quad チェーンで Bloom/CA/FilmGrain/ColorGrading/CRT を統合。

**前提**: Phase 1, 2 完了（入力バッファとして利用）。

### Step 4.1: ポストプロセスパイプライン基盤
- [ ] Task: `EffectComposer` 風のパスチェイン実装
- [ ] Task: RenderTarget プール（メモリ再利用）
- [ ] Task: パス有効/無効トグル
- **成果物**: `src/post/PostPipeline.ts`
- **受入**: 空パスで元画像をそのまま出力

### Step 4.2: Bloom パス
- [ ] Task: 輝度閾値抽出
- [ ] Task: セパラブルガウスブラー（2-3 段）
- [ ] Task: 加算合成（threshold/radius/intensity 調整）
- **成果物**: `src/post/BloomPass.ts`
- **受入**: 魔法/溶岩が発光する

### Step 4.3: クロマティックアベレーション
- [ ] Task: RGB チャンネル分離サンプリング
- [ ] Task: 放射/線形モード切替
- [ ] Task: 速度連動ストレングス
- **成果物**: `src/post/ChromaticAberrationPass.ts`
- **受入**: 画面端で色収差が見える

### Step 4.4: フィルムグレイン + ビネット
- [ ] Task: 時間変調ノイズテクスチャ
- [ ] Task: ISO/ビネット強度パラメータ
- [ ] Task: テクスチャノイズ事前生成
- **成果物**: `src/post/FilmGrainPass.ts`
- **受入**: シネマ風質感が付与

### Step 4.5: カラーグレーディング (3D LUT)
- [ ] Task: 3D LUT テクスチャ読み込み
- [ ] Task: 露光/カラーバランス適用
- [ ] Task: シーン別 LUT プリセット
- **成果物**: `src/post/ColorGradingPass.ts`, `assets/luts/*.cube`
- **受入**: 夕暮れ/夜/洞窟で異なる色調

### Step 4.6: CRT / スキャンライン
- [ ] Task: 曲率ディストーション
- [ ] Task: スキャンライン + 蛍光減衰
- [ ] Task: レトロモード切替
- **成果物**: `src/post/CRTPass.ts`
- **受入**: レトロモードで CRT 風に

### Step 4.7: パラメータ統合・プリセット
- [ ] Task: YAML でポスト設定定義
- [ ] Task: プリセット（標準/シネマ/レトロ/ドリーム）
- [ ] Task: ランタイム切替 UI
- **成果物**: `data/post_presets.yaml`
- **受入**: 1 キーでプリセット切替

### Step 4.8: 統合・ベンチマーク
- [ ] Task: 全パス有効時のフレーム測定
- [ ] Task: 半解像度ポスト適用最適化
- [ ] Task: SSIM リグレッションテスト
- **成果物**: `benches/post_bench.json`
- **受入**: 全パスで 60fps、GPU ms < 14ms

**Phase 4 依存**: → Phase 9 (最適化対象)

---

## Phase 5: プロシージャル地形・ダンジョン生成

**目標**: WFC + グラフ制約で自然なダンジョンをシード再現可能に生成。

**前提**: Phase 1 (地形レンダリング), Phase 2 (エフェクト配置)。

### Step 5.1: WFC タイル制約エンジン
- [ ] Task: タイルセット・エッジルール定義
- [ ] Task: WFC ソルバ（バックトラック付き）
- [ ] Task: 重み付きサンプリング
- **成果物**: `src/proc/WFC.ts`, `data/wfc_rules.yaml`
- **受入**: 洞窟/遺跡が自然に生成

### Step 5.2: グラフベース構造生成
- [ ] Task: 部屋ノード DAG 生成
- [ ] Task: 廊下接続（最小スパニングツリー）
- [ ] Task: 宝物庫/ボス部屋配置制約
- **成果物**: `src/proc/GraphGenerator.ts`
- **受入**: 必ず開始→ボス到達可能

### Step 5.3: バイオームブレンド
- [ ] Task: ノイズ（FBM/ワープ）重ね合わせ
- [ ] Task: 森林⇔砂漠⇔雪原 シームレス遷移
- [ ] Task: 高度・湿度マップ生成
- **成果物**: `src/proc/Biome.ts`
- **受入**: 境界が途切れず自然

### Step 5.4: シード・再現性管理
- [ ] Task: シードハッシュ → 決定論的生成
- [ ] Task: 同一シード再生成テスト
- [ ] Task: シード共有フォーマット
- **成果物**: `src/proc/SeedManager.ts`
- **受入**: 同じシードで同一地形

### Step 5.5: 装飾・エンティティ配置
- [ ] Task: 部屋タイプ別家具/罠配置
- [ ] Task: モンスタースポーン密度ルール
- [ ] Task: 宝箱/イベントマーカー
- **成果物**: `data/proc_placement.yaml`
- **受入**: 部屋ごとに適切な装飾

### Step 5.6: メッシュ・テクスチャ合成
- [ ] Task: タイル→3D メッシュ自動変換
- [ ] Task: バイオーム別マテリアル
- [ ] Task: 法線/ AO マップ焼き込み
- **成果物**: `src/proc/MeshBaker.ts`
- **受入**: 生成地形が Phase1 で描画

### Step 5.7: エディタ・プレビュー
- [ ] Task: シード入力→即プレビュー HTML
- [ ] Task: 生成統計（部屋数/長さ）表示
- [ ] Task: エクスポート（JSON/画像）
- **成果物**: `demos/proc_preview.html`
- **受入**: ブラウザで生成確認可能

### Step 5.8: 統合・パフォーマンス
- [ ] Task: 生成時間 < 100ms 最適化
- [ ] Task: チャンク分割・ストリーミング生成
- [ ] Task: 24 シーンへの適用テスト
- **成果物**: `benches/proc_bench.json`
- **受入**: 200×200 マップを 100ms 内生成

**Phase 5 依存**: → Phase 9 (LOD/ストリーミング)

---

## Phase 6: UI/UX マイクロインタラクション

**目標**: FLIP + スプリング物理で自然な UI アニメ、アクセシビリティ対応。

**前提**: Phase 3 (スプライトアイコン), Phase 4 (ポストは UI 外)。

### Step 6.1: FLIP アニメーション基盤
- [ ] Task: `First-Last-Invert-Play` ユーティリティ
- [ ] Task: `transform` のみで位置/サイズ変化
- [ ] Task: `will-change` 自動管理
- **成果物**: `src/ui/flip.ts`
- **受入**: レイアウト変化が 60fps

### Step 6.2: スプリング物理エンジン
- [ ] Task: `stiffness/damping` ベース解釈
- [ ] Task: 複数プロパティ同時スプリング
- [ ] Task: 中断・再開サポート
- **成果物**: `src/ui/spring.ts`
- **受入**: `stiffness:300, damping:30` で自然追従

### Step 6.3: 状態別トランジション
- [ ] Task: hover → `scale(1.02)`
- [ ] Task: press → `scale(0.98)`
- [ ] Task: release → `scale(1.0)` 弾性
- **成果物**: `src/ui/transitions.css`
- **受入**: 全ボタンに統一感触

### Step 6.4: ログ・トースト・ダイアログ
- [ ] Task: 戦闘ログのスライドイン
- [ ] Task: トースト通知スタック
- [ ] Task: モーダル開閉スプリング
- **成果物**: `src/ui/widgets.ts`
- **受入**: ログが滑らかに表示

### Step 6.5: メニュー・インベントリ
- [ ] Task: グリッド整列 FLIP アニメ
- [ ] Task: ドラッグ&ドロップ物理
- [ ] Task: ツールチップ遅延表示
- **成果物**: `src/ui/inventory.ts`
- **受入**: アイテム移動が直感的

### Step 6.6: タイトル・HUD 刷新
- [ ] Task: `ui_title_display.py` の視覚拡張
- [ ] Task: HP/MP バーアニメ
- [ ] Task: ミニマップ拡大縮小
- **成果物**: `src/ui/hud.ts`
- **受入**: 称号取得でポップアニメ

### Step 6.7: reduced-motion 対応
- [ ] Task: `prefers-reduced-motion` 検知
- [ ] Task: 全モーション即時完了フォールバック
- [ ] Task: 設定画面トグル
- **成果物**: `src/ui/a11y.ts`
- **受入**: 設定 ON でアニメ無効化

### Step 6.8: 統合・テスト
- [ ] Task: 全 UI コンポーネント統合
- [ ] Task: キーボードナビゲーション完全対応
- [ ] Task: 視覚回帰テスト（スナップショット）
- **成果物**: `tests/ui.test.ts`
- **受入**: 全操作がキーボードで完結

**Phase 6 依存**: → Phase 8 (アクセシビリティ統合)

---

## Phase 7: サウンド連動ビジュアライゼーション

**目標**: Web Audio API + シェーダー uniform で音に同期した視覚演出。

**前提**: Phase 2 (パーティクル), Phase 4 (ポスト), `sound_manager.py` 既存。

### Step 7.1: Web Audio 解析基盤
- [ ] Task: `AudioContext` セットアップ
- [ ] Task: `AnalyserNode` 256bin FFT
- [ ] Task: オンセット（ビート）検出
- **成果物**: `src/audio/Analyser.ts`
- **受入**: BPM 検出精度 ±5%

### Step 7.2: uniform ブリッジ
- [ ] Task: `u_audio[256]` を GPU に送信
- [ ] Task: 低/中/高域 平均値抽出
- [ ] Task: スムージング（EMA）
- **成果物**: `src/audio/UniformBridge.ts`
- **受入**: 音変化が 1 フレーム以内反映

### Step 7.3: ビート同期エフェクト
- [ ] Task: 画面フラッシュ・パーティクルバースト
- [ ] Task: カメラシェイク（ビート連動）
- [ ] Task: スプリング復帰
- **成果物**: `src/audio/BeatSync.ts`
- **受入**: ドラムで画面が脈打つ

### Step 7.4: 楽器別マッピング
- [ ] Task: 低音→画面揺れ振幅
- [ ] Task: 高音→パーティクル色相シフト
- [ ] Task: ボーカル→UI 強調
- **成果物**: `data/audio_mapping.yaml`
- **受入**: 音域で異なる反応

### Step 7.5: 空間オーディオ
- [ ] Task: `PannerNode` 3D 位置
- [ ] Task: ステレオパン・リバーブ送信
- [ ] Task: `monsters.yaml` 座標と連携
- **成果物**: `src/audio/SpatialAudio.ts`
- **受入**: 敵の位置で音が左右する

### Step 7.6: ミュート・ボリューム制御
- [ ] Task: マスターボリューム
- [ ] Task: BGM/SFX 分離
- [ ] Task: ビジュアライズのみ OFF モード
- **成果物**: `src/audio/Mixer.ts`
- **受入**: 視覚同期を独立 OFF 可能

### Step 7.7: デモ・統合
- [ ] Task: `scene_06_tavern`（演奏）に適用
- [ ] Task: 音楽同期デモ HTML
- [ ] Task: `audio_config.yaml` 拡張
- **成果物**: `demos/audio_viz.html`
- **受入**: バイオリン演奏で粒子が舞う

### Step 7.8: 最適化・テスト
- [ ] Task: FFT コスト測定
- [ ] Task: オーディオなし時のゼロオーバーヘッド
- [ ] Task: 自動テスト（ビート検出）
- **成果物**: `tests/audio.test.ts`
- **受入**: 音あり/なし 両方 60fps

**Phase 7 依存**: → Phase 9 (コスト統合)

---

## Phase 8: アクセシビリティ・カラーグレーディング

**目標**: WCAG AAA 対応、色覚多様性シミュ、コントラスト自動補正。

**前提**: Phase 4 (カラーグレーディング基盤), Phase 6 (UI 連携)。

### Step 8.1: 色覚多様性シミュレータ
- [ ] Task: プロタノピア/デュータノ/トリタノ 変換行列
- [ ] Task: シェーダーでのリアルタイムプレビュー
- [ ] Task: 開発者用オーバーレイ
- **成果物**: `src/a11y/ColorVision.ts`
- **受入**: 3 型の色覚特性を再現表示

### Step 8.2: コントラスト自動補正
- [ ] Task: 輝度比計算（WCAG 2.1）
- [ ] Task: 7:1 未満を検知し輝度のみ調整
- [ ] Task: パレット自動生成
- **成果物**: `src/a11y/ContrastFix.ts`
- **受入**: 全テキストが 7:1 達成

### Step 8.3: ハイコントラストモード
- [ ] Task: `prefers-contrast: more` 検知
- [ ] Task: 白黒反転 + 太縁取りスタイル
- [ ] Task: フォーカスリング強化
- **成果物**: `src/a11y/HighContrast.ts`
- **受入**: モード ON で視認性最大化

### Step 8.4: フォーカス可視化
- [ ] Task: `3px solid currentColor` + offset 2px
- [ ] Task: キーボード操作トラッキング
- [ ] Task: 視覚的迷子防止（パン演出）
- **成果物**: `src/a11y/FocusRing.ts`
- **受入**: 全要素が Tab で到達可能

### Step 8.5: テキスト・フォント最適化
- [ ] Task: 動的フォントサイズ（視力設定）
- [ ] Task: 読みやすさ指標（CPS/行長）監視
- [ ] Task: フォントアトラス拡張（`font_atlas_generator.html`）
- **成果物**: `assets/font_atlas_ext.png`
- **受入**: 最小 16px で判読可能

### Step 8.6: 音声・読上げ連携
- [ ] Task: ARIA ラベル完全付与
- [ ] Task: ログのスクリーンリーダー通知
- [ ] Task: `aria-live` リージョン設定
- **成果物**: `src/a11y/ARIA.ts`
- **受入**: NVDA/VoiceOver で操作可能

### Step 8.7: 設定画面・プロファイル
- [ ] Task: アクセシビリティ設定パネル
- [ ] Task: プロファイル保存（localStorage）
- [ ] Task: クイックプリセット（弱視/色覚/運動）
- **成果物**: `src/a11y/Settings.ts`
- **受入**: 設定が永続化される

### Step 8.8: 統合・コンプライアンステスト
- [ ] Task: 全シーンで a11y 監査（axe-core）
- [ ] Task: コントラスト自動テスト
- [ ] Task: キーボード操作 E2E
- **成果物**: `tests/a11y.test.ts`
- **受入**: axe-core 重大違反 0 件

**Phase 8 依存**: → Phase 9 (最終統合)

---

## Phase 9: パフォーマンス最適化・LODシステム

**目標**: フレーム予算制御、動的解像度、階層カリング、プロファイル HUD。

**前提**: Phase 1-8 全完了。

### Step 9.1: フレーム予算制御
- [ ] Task: 16.67ms 予算管理ループ
- [ ] Task: GPU/CPU 時間分離計測
- [ ] Task: 超過時のグレースケール化
- **成果物**: `src/perf/BudgetManager.ts`
- **受入**: 予算内で安定 60fps

### Step 9.2: 動的解像度
- [ ] Task: `setPixelRatio(min(2, 60/fps))`
- [ ] Task: 滑らかな解像度遷移
- [ ] Task: 最小/最大比クランプ
- **成果物**: `src/perf/DynamicRes.ts`
- **受入**: 負荷増で自動解像度低下

### Step 9.3: 階層カリング
- [ ] Task: Frustum カリング
- [ ] Task: Occlusion クエリ
- [ ] Task: Distance + Importance 削減
- **成果物**: `src/perf/Culling.ts`
- **受入**: 視野外オブジェクト 0 描画

### Step 9.4: LOD メッシュ・テクスチャ
- [ ] Task: 距離別メッシュ段階（3 段）
- [ ] Task: ミップマップ自動選択
- [ ] Task: 重要度ベース維持
- **成果物**: `src/perf/LOD.ts`
- **受入**: 遠景でポリゴン 70% 削減

### Step 9.5: バッチング・インスタンシング
- [ ] Task: 同マテリアル統合描画
- [ ] Task: `InstancedMesh` 活用
- [ ] Task: 描画コール数削減
- **成果物**: `src/perf/Batching.ts`
- **受入**: draw call < 100 / シーン

### Step 9.6: メモリ・GC 最適化
- [ ] Task: オブジェクトプール
- [ ] Task: テクスチャ/バッファ再利用
- [ ] Task: GC ポーズ監視
- **成果物**: `src/perf/Memory.ts`
- **受入**: GC ポーズ < 2ms 安定

### Step 9.7: プロファイル HUD
- [ ] Task: `performance.mark/measure` 連携
- [ ] Task: FPS/GPU ms/メモリ表示
- [ ] Task: Chrome DevTools Timeline 出力
- **成果物**: `src/perf/ProfilerHUD.ts`
- **受入**: リアルタイムでボトルネック表示

### Step 9.8: 最終統合・回帰テスト
- [ ] Task: 全 24 シーンでの総合ベンチ
- [ ] Task: 低スペックデバイス検証（目標 30fps）
- [ ] Task: CI での SSIM/フレーム ゲート追加
- **成果物**: `benches/final_bench.json`, CI ワークフロー
- **受入**: 全フェーズ統合で 60fps（高）/30fps（低）

**Phase 9 依存**: なし（最終フェーズ）

---

## マイルストーン

| マイルストーン | 完了条件 | 推定週 |
|---------------|----------|--------|
| M1: 描画基盤 | Phase 1-2 完了 | W6 |
| M2: 演出層 | Phase 3-4 完了 | W11 |
| M3: コンテンツ生成 | Phase 5 完了 | W14 |
| M4: 体験品質 | Phase 6-7 完了 | W18 |
| M5: 包摂・最適化 | Phase 8-9 完了 | W23 |

## クリティカルパス
```
Phase1 → Phase2 → Phase4 → Phase9
Phase1 → Phase3 → Phase6 → Phase8 → Phase9
Phase1 → Phase5 → Phase9
Phase2 → Phase7 → Phase9
```

## リスク登録簿（抜粋）
| リスク | 影響 | 対策 |
|--------|------|------|
| WebGPU 未対応ブラウザ | 高 | WebGL2 フォールバック維持 |
| 10万パーティクル GPU 上限 | 中 | 段階的スケール + LOD |
| ポストプロセス合計コスト | 高 | 半解像度適用・パス統合 |
| プロシージャル生成遅延 | 中 | チャンク分割・Worker 化 |
| アクセシビリティ互換 | 中 | axe-core CI ゲート |

---

> 進捗管理: 各ステップ完了時に本書の `[ ]` を `[x]` に更新し、PR にてレビュー。
> 全 72 ステップ完了で「偏執的グラフィック」実装完了。
