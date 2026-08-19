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

## 🎬 ゲームプレイ動画

### 1. メインゲームプレイ循環
探索 → 戦闘 → 祈り → スキル/インベントリ → 輪廻転生のフルループ

![Gameplay Demo](demo_gameplay.gif)

### 2. スキルツリー・ジョブシステム
70種類以上のスキル、15職業の転職、融合・覚醒・継承システム

![Skill Tree Demo](demo_skill_tree.gif)

### 3. ペットシステム & Webブラウザ版
契約・進化・融合で相棒を育成、インストール不要のブラウザプレイ

![Pet & Web Demo](demo_pet_web.gif)

---

## 🚀 クイックスタート（最初にこれだけやれば遊べます）

### 1. 必要なもの
- **Python 3.10 以上** （3.11〜3.14 推奨）
- **Git**（ソースコード取得用）

### 2. インストール・起動

```bash
# リポジトリをクローン
git clone <このリポジトリのURL>
cd naRou

# 依存パッケージをインストール
pip install -r requirements.txt

# ゲーム起動！
python main.py
```

起動するとメニューが表示されるので、**`1` を入力して Enter** でゲーム開始です。

### 3. Webブラウザで遊ぶ場合

```bash
# 1. ゲームを起動（メニューで 1 を選択）
python main.py

# 2. 別のターミナルでWebサーバーを起動
python web_server.py

# 3. ブラウザでアクセス
# http://localhost:8080
```

---

## ⌨️ 基本操作（ゲーム内で `[?]` または `[h]` でも確認可能）

| キー | アクション |
|------|------------|
| **矢印キー / テンキー** | 移動・通常攻撃（敵の方向へ移動で攻撃） |
| **Space** | 文脈アクション（拾う・会話・食べる・祈る等） |
| **i** | インベントリ開く（タブで装備/アイテム切替、Enterで使用/装備、dで捨てる） |
| **c** | キャラクターステータス・能力値・スキル確認 |
| **j** | ジョブ管理・転職メニュー |
| **Shift + S** | スキルツリー画面 |
| **Shift + G** | ギルド・派閥メニュー |
| **l** | 周囲調査（ルックモード） |
| **> / <** | 階段を下りる / 上がる |
| **? / h** | ヘルプ画面表示 |
| **F5** | セーブ実行（自動セーブもあり） |

---

## 📁 プロジェクト構成（開発者向け）

```
naRou/
├── main.py                    # エントリーポイント（メニュー表示）
├── game.py                    # ゲーム本体エンジン（1800行超）
├── requirements.txt           # Python依存パッケージ
├── pyproject.toml             # パッケージ設定
├── config.yaml                # ゲーム設定
├── constants.py               # 定数定義
├── core/                      # コアフレームワーク
│   ├── __init__.py
│   ├── palette.py             # カラーパレット
│   └── ...                    # ECS基盤、イベントバス等
├── systems/                   # ゲームシステム（戦闘、生存等）
├── entity.py                  # エンティティ定義
├── map_engine.py              # マップ生成・描画
├── skill_tree_system.py       # スキルツリー
├── job_system.py              # ジョブシステム
├── pet_*_system.py            # ペット関連システム
├── guild_*_system.py          # ギルド関連システム
├── faction_war_system.py      # 派閥戦争
├── save_system.py             # セーブ/ロード
├── web_server.py              # WebSocket/HTTPサーバー
├── web_game_client.html       # ブラウザ版クライアント
├── demos/                     # デモHTMLファイル群
├── tests/                     # テストコード（多数）
├── tools/                     # 開発用ツール
├── assets/                    # タイルセット、フォント等
└── data/                      # ゲームデータ（YAML等）
```

---

## 🛠️ 開発者向けコマンド

```bash
# テスト実行
python -m pytest

# 特定テストのみ実行
python -m pytest tests/test_gi.py -v

# バトルバランス検証（HTML/JSONレポート出力）
python tests/balance_simulator.py

# リンター・フォーマッター
python -m flake8 .
python -m black .
python -m mypy .

# デモシーン生成
python generate_24_scenes.py

# アセットビルド
python tools/build_assets.py

# データスキーマ → Pydantic/dataclass 自動生成
python tools/codegen.py

# YAML データのスキーマ検証
python tools/codegen.py --validate-data

# スキーマ構文検証
python tools/codegen.py --validate-only

# リポジトリ層テスト
python -m pytest tests/test_repositories.py -q
```

---

## 🗂️ 現在の未コミット変更（作業進捗）

このブランチには、まだコミットに反映されていない変更が多数含まれています。

### データ駆動アーキテクチャ（schema → モデル → リポジトリ）
- `data/schemas/` : アイテム/モンスター/スキル/クエスト/ダンジョン/派閥/ジョブ/神/ギルド/称号/実績/呪文/スキル融合/スキルツリーの JSON Schema
- `data/generated/` : `tools/codegen.py` が生成した Pydantic モデル（strict 型検証・`DataModel` 基底）
- `data/generated_dc/` : 同上から生成した frozen dataclass
- `data/repositories/` : リポジトリパターン（各ドメインの検索・インデックス・クエリ）
- `tools/codegen.py` : JSON Schema → Pydantic/dataclass 自動生成 ＋ YAML 検証ツール
- `data_manager.py` : スキーマ検証付きロード・リポジトリ構築へ書き直し（`DataManager()` で即利用可）
- `tests/test_repositories.py` : リポジトリ層のテスト（38検証）
- `.github/workflows/data-pipeline.yml` : スキーマ検証＋リポジトリテストの CI

> ⚠️ 既知の課題: `main_quests.yaml` / `dungeon_themes.yaml` はスキーマと構造が異なるため、DataManager は tolerant ロード（型を緩やかに構築）で対応。スキーマとの統合が残務。

### 描画・ビジュアル（WebGL / ポストプロセス / パレット）
- `core/lighting.py` `core/palette.py` `core/renderer_base.py` `core/tcod_renderer.py` : ライティング・パレット・レンダラ基盤の刷新
- `core/entity_renderer.py` `core/tile_atlas.py` `core/palette_generated.py` : エンティティ描画・タイルアトラス・生成パレット（新規）
- `core/gi.py` : 削除（機能を他へ統合）
- `entity.py` `game.py` `system_coordinator.py` `web_game_client.html` `web_server.py` : 描画統合・Web クライアント反映
- `assets/tiles/tileset_def.json` `assets/css/` `design_tokens*.json` : タイルセット・CSS・カラーブラインド対応パレット
- `demos/*` : 24 シーンデモのテンプレート化・刷新（`tools/convert_demos_to_template.py` 等）
- `webgpu/lpv.wgsl` : WebGPU ライトプロパゲーションシェーダ

### 開発ツール・ドキュメント
- `tools/` : パレット生成/検証、タイルパリティ、視覚回帰、デモ変換などの新規ツール
- `docs/` : エンティティ描画・視覚統一・ターミナル照明などの実装提案/解説

---

## 🌐 Webクライアントについて

`web_game_client.html` と `web_server.py` でブラウザプレイに対応しています。

- **WebSocket** でリアルタイム通信
- **ローカルネットワーク内**ならスマホからも接続可能
- `web/theme.css` でテーマカスタマイズ可能

### 🎮 Web版デモ手順

```bash
# ターミナル1: ゲームサーバー起動
python main.py
# → メニューで 1 を選択してゲーム開始

# ターミナル2: WebSocketサーバー起動
python web_server.py

# ブラウザでアクセス
# http://localhost:8080
# スマホから: http://<PCのローカルIP>:8080
```

**Web版の特徴:**
- ターミナル版と**完全同一のゲームロジック**で動作
- タッチ操作対応（スマホ/タブレットで快適プレイ）
- バーチャルキーパッド、ハンバーガーメニューで全機能アクセス
- ダーク/ライトテーマ切替、PWA対応でオフライン・ホーム画面追加可能

---

## 📚 学習リソース（初心者向け）

ローグライク開発に興味がある方へ：

1. **Python基礎** → [Python公式チュートリアル](https://docs.python.org/ja/3/tutorial/)
2. **tcodライブラリ** → [python-tcod ドキュメント](https://python-tcod.readthedocs.io/)
3. **ローグライク開発** → [Roguelike Tutorial (Python+tcod)](https://rogueliketutorials.com/tutorials/tcod/)
4. **ECSアーキテクチャ** → [Entity Component System 解説](https://en.wikipedia.org/wiki/Entity_component_system)

---

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

- **Issue報告**: バグや要望は GitHub Issues へ
- **プルリクエスト**: 改善提案歓迎です
- **動作確認**: Windows/macOS/Linux で動作確認済み

---

## 📄 ライセンス

MIT License - 詳細は `LICENSE` ファイル参照（または pyproject.toml の license フィールド）

---

## 🙏 謝辞

- **Elona** (by Noa) - インスピレーションの源
- **python-tcod** - ローグライク開発の強力な基盤
- **コントリビューターの皆様**

---

> **初心者の方へ**: まずは `python main.py` でゲームを起動して、`1` を選んで遊んでみてください！わからないことはゲーム内の `[?]` キーや、この README の「基本操作」を見てください。楽しんでください！