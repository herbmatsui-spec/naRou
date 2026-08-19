# naRou: Masterpiece Edition (Commercial Release v1.0.0)

『naRou: Masterpiece Edition』は、本格ローグライクRPGの深遠なゲーム性と自由度をベースに、疎結合アーキテクチャ・ECS（Entity Component System）・スキルツリー・ジョブ・ギルド・派閥戦争・輪廻転生・ペット進化/融合・ストーリーテラー・Webクライアント連携を完全統合した商用クオリティのローグライクゲームです。

## 🎬 ゲームプレイ・デモ

<div align="center">
  <img src="demo_gameplay.gif" alt="naRou: Masterpiece Edition ゲームプレイデモ" width="700">
  <p><em>▲ 拠点〜ダンジョン探索〜ボス戦〜輪廻転生 NG+ のループプレビュー</em></p>
</div>

### 🎥 インタラクティブ実況プレイ & シーンギャラリー
ブラウザで直接動かして体験できる完全再現デモを提供しています：
- **統合マスターショーケース（多層ワールド・考古学解読・最新演出）**: [`integrated_master_showcase.html`](integrated_master_showcase.html)
- **実況プレイデモ（全24章・初心者ガイド付き）**: [`elona_playthrough.html`](elona_playthrough.html)
- **24シーン グランドショーケース**: [`demos/gallery_24_scenes.html`](demos/gallery_24_scenes.html)
- **グラフィック強化ショーケース**: [`graphics_showcase_demo.html`](graphics_showcase_demo.html)
- **絵文字グラフィックモード**: [`emoji_showcase.html`](emoji_showcase.html)
- **Webクライアント（WebSocket/HTTP 実プレイ）**: [`web_game_client.html`](web_game_client.html)
- **チュートリアルデモ**: [`tutorial_demo.html`](tutorial_demo.html)
- **UI コンポーネントカタログ**: [`ui_catalog.html`](ui_catalog.html)

### 🗺️ 個別シーン プレビュー（全24シーン）
`demos/` 配下に各シーンの独立プレビューを用意しています：
[`scene_01_base_home.html`](demos/scene_01_base_home.html) ·
[`scene_02_adventurers_guild.html`](demos/scene_02_adventurers_guild.html) ·
[`scene_03_job_system.html`](demos/scene_03_job_system.html) ·
[`scene_04_skill_tree.html`](demos/scene_04_skill_tree.html) ·
[`scene_05_skill_fusion.html`](demos/scene_05_skill_fusion.html) ·
[`scene_06_skill_evolution_awakening.html`](demos/scene_06_skill_evolution_awakening.html) ·
[`scene_07_skill_meta.html`](demos/scene_07_skill_meta.html) ·
[`scene_08_pet_contract.html`](demos/scene_08_pet_contract.html) ·
[`scene_09_pet_evolution.html`](demos/scene_09_pet_evolution.html) ·
[`scene_10_pet_fusion.html`](demos/scene_10_pet_fusion.html) ·
[`scene_11_procedural_dungeon.html`](demos/scene_11_procedural_dungeon.html) ·
[`scene_12_combat_system.html`](demos/scene_12_combat_system.html) ·
[`scene_13_monsters_ai.html`](demos/scene_13_monsters_ai.html) ·
[`scene_14_gods_faith.html`](demos/scene_14_gods_faith.html) ·
[`scene_15_faction_war.html`](demos/scene_15_faction_war.html) ·
[`scene_16_guilds_detail.html`](demos/scene_16_guilds_detail.html) ·
[`scene_17_reincarnation.html`](demos/scene_17_reincarnation.html) ·
[`scene_18_ng_plus.html`](demos/scene_18_ng_plus.html) ·
[`scene_19_meta_progression.html`](demos/scene_19_meta_progression.html) ·
[`scene_20_storyteller.html`](demos/scene_20_storyteller.html) ·
[`scene_21_procedural_quests.html`](demos/scene_21_procedural_quests.html) ·
[`scene_22_save_migration.html`](demos/scene_22_save_migration.html) ·
[`scene_23_balance_simulator.html`](demos/scene_23_balance_simulator.html) ·
[`scene_24_ecs_architecture.html`](demos/scene_24_ecs_architecture.html)

### ✨ ビジュアル・エフェクト デモ
描画エンジンの演出を個別に確認できます：
- **ブルーム＆シェイク演出**: [`demos/bloom_shake_demo.html`](demos/bloom_shake_demo.html)
- **ライティング演出**: [`demos/lighting_demo.html`](demos/lighting_demo.html)
- **パーティクル演出**: [`demos/particle_demo.html`](demos/particle_demo.html)
- **WebGL テンプレート**: [`demos/webgl_template.html`](demos/webgl_template.html)
- **フォントアトラス生成**: [`demos/font_atlas_generator.html`](demos/font_atlas_generator.html)

### 🧪 開発・ツール用デモ
- **デモ再生/録画**: [`demo_recorder.html`](demo_recorder.html) · [`demo.html`](demo.html) · [`ui_test.html`](ui_test.html)
- **関係性システムデモ（Python）**: [`demos/relationship_demo.py`](demos/relationship_demo.py)

---

## 🎮 主な機能と特徴

1. **ECS & 疎結合アーキテクチャ (`SystemManager`, `BaseSystem`)**
   - 責務分離されたモジュール構成による高保守性・高拡張性。
2. **商用セーブデータシステム (`SaveSystem`, `MigrationManager`)**
   - SHA256チェックサム検証付き JSON/Gzip シリアライズ。
   - 自動バックアップローテーション（最大3世代）およびデータスキーママイグレーション。
3. **奥深いキャラクタービルド & メタ進行**
   - **スキルツリー & ジョブシステム**: スキル合成・進化・覚醒・特化。
   - **輪廻転生 & ニューゲーム+**: 周回ごとのボーナス、カルマ変動、固有ダンジョン開放。
   - **ペット契約・進化・融合**: 相棒ペットの育成と多段進化。
4. **自動生成ストーリー & ギルド・派閥システム**
   - ランダムイベント、派閥戦争、NPC関係性システム。
5. **デュアルUI環境**
   - **tcod (コンソール/GUI)** & **モダンWebクライアント (`web_game_client.html`, WebSocket/HTTP)**。
6. **自動バトルバランス検証システム (`BalanceSimulator`)**
   - YAML基準値による自動戦闘シミュレーションと HTML レポート出力。

---

## 🚀 インストールと起動方法

### 1. 動作環境・必要要件
- Python 3.10 以上 (Python 3.11〜3.14 対応)
- Windows / macOS / Linux

### 2. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 3. ゲームの起動

#### メニューからの起動 (推奨)
```bash
python main.py
```
メニューから `1` を選択してゲームを開始します。

#### Webクライアントでのプレイ
ゲーム起動後、ブラウザで以下にアクセスします：
```
http://localhost:8080
```

#### バトルバランス検証の実行
```bash
python tests/balance_simulator.py
```
実行後、`balance_report.json` および `balance_report.html` が出力されます。

#### 自動テストの実行
```bash
python -m pytest
```

---

## ⌨️ 基本操作一覧

| 操作キー | アクション |
| :--- | :--- |
| **矢印キー / テンキー** | 移動・通常攻撃 |
| **[Space]** | 文脈アクション（アイテム拾い、会話、食事、祈り等） |
| **[i]** | インベントリを開く（タブ切り替え、装備、使用、破棄） |
| **[c]** | キャラクターステータス・能力・スキル確認 |
| **[j]** | ジョブ管理・転職メニュー |
| **[Shift + S]** | スキルツリー画面 |
| **[Shift + G]** | ギルド・派閥メニュー |
| **[l]** | 周囲調査（ルックモード） |
| **[>] / [<]** | 階段を下りる / 上がる |
| **[?] / [h]** | ヘルプ画面表示 |
| **[F5] / 自動** | セーブ実行 |

---
## 📝 最近の変更 (Recent Changes)

### 🌟 偏執的グラフィック強化 & 2.5D レンダリングパイプライン
- **法線マップ動的ライティング (`LightingSystem.js`)**: `normal_atlas.png` と 2.5D法線マップシェーダーによる微細な凹凸陰影、SDF影生成、ボリュメトリックフォグ光線（ゴッドレイ）、フリッカー光源を実装。
- **流体シミュレーション (`FluidRenderer.js`)**: 表面張力・メタボールシェーダーによる血痕・毒沼のリアルタイム拡散・凝集レンダリング。
- **デカール永続化 (`DecalSystem.js`)**: タイルへの足跡、焦げ跡、血痕スタンプの自動フェードアウト・永続化描画。
- **自律飛行Boidsシステム (`BoidSystem.js`)**: 光源に群がる羽虫・浮遊胞子の群知能シミュレーション。
- **環境干渉 (`EnvironmentShader.js`)**: 風揺れ・エンティティ通過時の草木押し曲げ（Foliage Bending）シェーダー。
- **シネマティックポストプロセス (`PostProcessManager.js`, `ScreenShake.js`)**: 衝撃波、色収差、ダメージ歪み、CRT走査線、被写界深度・減衰シェイク。

### 🧭 垂直多層ワールド拡張 (4ゾーン×8バイオーム×3次元×深度マトリクス)
- **多層空間生成エンジン (`world_layer.py`, `world_map_manager.py`)**:
  - 地上界 (0-10F)、地下界 (11-50F)、異界 (51-100F)、天界 (101-200F) の4層ゾーン構造。
  - 平原・森林・山岳・沼地・砂漠・凍土・火山・遺跡の8バイオーム × 物質・精神・虚無の3次元マトリクス（理論上38,400組み合わせ）。
  - 階層間階段移動・ゾーン境界レイヤー遷移・次元跳躍システム。

### 📜 考古学・発掘・記憶暗号解読メタゲーム (`archaeology_system.py`)
- **暗号解読＆真理コーデックス (`data/truth_codex.yaml`, `data/memory_fragments.yaml`)**:
  - ダンジョン探索や発掘から得られる未解読記憶片（ルーン/古代文字）の収集・解読パイプライン。
  - 解読鍵（辞書・古文書）の適用による真理ノード到達と、読者/プレイヤーの解釈による物語エンディング分岐。

### 🎮 新規デモの追加 & 既存デモの改修
- **統合マスターショーケース**: [`integrated_master_showcase.html`](integrated_master_showcase.html) を新設（多層ワールド探索、考古学暗号解読、PixiJSリアルタイムバトル、全システム統合Webアプリ）。
- **グラフィック強化ショーケース**: [`graphics_showcase_demo.html`](graphics_showcase_demo.html) をES Modules直接インポート型に改修し、全9機能のシェーダー演出を即時操作可能に。

### 🎬 ゲームプレイ・デモの再構築（実システム反映）
- 旧24シーン（汎用「Elona」テーマ）を削除し、**実装済みの naRou システムに合わせた24シーン**を新規生成。
- `generate_24_scenes.py` を書き直し：出力パスを相対 `demos/` に修正、同一データからギャラリーも自動生成するよう拡張。
- `demos/gallery_24_scenes.html` を再生成（ブランディングを naRou: Masterpiece Edition に統一）。
- 新規追加：実装計画書 `plans/gameplay_demo_24_scenes_implementation_plan_japanese.md`。

### 🖼️ ゲームプレイGIFの再生成
- `generate_accurate_gif.py` の出力パスを修正し、`demo_gameplay.gif` を再生成。

### 🧩 アセットパイプライン & タイルセット
- 64×64 タイルセットを新規追加（`assets/tiles/tileset_64x64.json` / `.png`）。
- 16×16・32×32 個別PNGタイルを削除しアトラス化を推進。
- `core/palette.py`、`tools/build_assets.py`、`tools/generate_theme.py`、`tools/generate_tileset_atlas.py`、`tools/validate_assets.py` を更新。

### 🌐 Webクライアント & テーマ
- `web_game_client.html`、`web/theme.css` を更新。

### 🧪 テスト
- `tests/test_token_parity.py` を新規追加。

> 詳細なファイル差分は `git status` / `git diff` を参照。本セクションは主要な変更グループをまとめたものです。

## 📄 ライセンス & クレジット
- **Version**: 1.0.0 (Commercial Edition)
- **Engine Architecture**: SystemManager ECS-coupled Engine

※ スキルツリー・ジョブシステムは、72段階の詳細実装計画に従って完全実装済み。
