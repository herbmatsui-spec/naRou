# 🌌 naRou: Masterpiece Edition & Multi-World Architecture

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/World-A:%20Skill%20Eater-purple.svg" alt="World A: Skill Eater">
  <img src="https://img.shields.io/badge/Presentation-Emote%20%2B%20Audio-orange.svg" alt="Presentation Foley">
  <img src="https://img.shields.io/badge/Tests-43%2F43%20Passing-brightgreen.svg" alt="Tests">
</p>

**Elona風本格ローグライクRPG** (Python + tcod) ＋ **『異世界マルチバース構想：Aの世界（スキル喰い RPG）』**

最底辺の解析スキルから始まり、敵のスキルを強奪・捕食（Devour）して自己の存在を書き換えていくダークファンタジー・ローグライク。認可外キメラ合成、資本主義闇市場、そして世界法則の上書き（ROOT Hack）による輪廻転生へ。

---

## 🕹️ インタラクティブ Web ショーケース

ブラウザ上で「スキル喰い」システムの戦闘、解析、捕食、キメラ合成、ROOTハック演出を今すぐ体験できます！

👉 **[Web Showcase デモをブラウザで開く (demos/demo_skill_eater_showcase.html)](demos/demo_skill_eater_showcase.html)**

---

## 🎬 Aの世界：スキル喰い（Skill Eater） 4大コアシステム

> 📺 以下のデモGIFは、ゲームの実際の描画パイプライン（`render_system.py` / `uirenderer.py` / `map_renderer.py` 等）に準拠して **実際のゲーム画面と同じコンソールUI（HUD・ミニマップ凡例・シネマティックログ）** でレンダリングされています。再生成は `python generate_readme_gifs.py` で行えます。

### 1. ⚔️ 【捕食とシナジー】 深度解析・強奪・エレメント爆発
敵の構造をスキャン解析し、弱体化した隙に《喰らい》を発動。胃袋内での属性衝突（熱爆発・磁気嵐）をコントロールせよ。

<p align="center">
  <img src="assets/demo_combat_devour.gif" alt="Combat & Devour Demo" width="760">
</p>

- **深度解析（Scan）**: 敵のスキル構成、弱点、核残量を可視化
- **捕食（Devour）**: 敵のスキルを核ごと吸収し、永続ステータスボーナスと固有アビリティを獲得
- **属性連鎖シナジー**: 火×風（熱爆発）、雷×水（放電麻痺）など胃袋内でシナジー発動

---

### 2. 🧪 【キメラ合成と経済】 禁忌の錬金炉・密売闇市場・監査官レイド
強奪したスキルを炉で融合し、新たな認可外キメラスキルを創出。不要なスキルは闇市場で高値で売り抜けろ。

<p align="center">
  <img src="assets/demo_synthesis_economy.gif" alt="Synthesis & Economy Demo" width="760">
</p>

- **動的キメラ合成（Procedural Synthesis）**: 2つのスキルを掛け合わせ、強力な複合スキルを錬成
- **闇市場（Underground Market）**: 認可外スキルの密売と相場価格の乱高下
- **異端審問官レイド（Inquisition Raid）**: 監査レベルが臨界に達した時、教団の武装部隊が急襲

---

### 3. 💻 【メタシステムと輪廻転生】 世界法則上書き（ROOT Hack）とカルマ継承
生命力と精神侵食（Sanity）を代償に、ゲーム世界の根幹パラメータ（ダメージ倍率、ドロップ率など）をハックして改変。

<p align="center">
  <img src="assets/demo_meta_reincarnation.gif" alt="Meta ROOT Hack & Reincarnation Demo" width="760">
</p>

- **ROOT Law Override**: 世界の物理定数・倍率パラメータをリアルタイム書き換え
- **精神侵食度（Sanity Erosion）**: ハックの代償として最大HP低下と知覚の歪みが発生
- **輪廻転生（Cycle Settlement）**: 世界崩壊時、前世の功績をカルマに変換し、遺伝スキルを継承して再誕

---

### 4. 🤖 【使い捨てタレット従属者】 Husk操縦と自壊の美学
スキルを抜き取られた敵の抜け殻（Husk）に魔力回路を繋ぎ、使い捨ての自動射撃タレットとして使役。

<p align="center">
  <img src="assets/demo_husk_servant.gif" alt="Husk Servant Turret Demo" width="760">
</p>

- **魔力回路移植**: Huskにスキルを再注入し、自律迎撃タレット化
- **寿命カウントダウン（Lifespan）**: 限られたターン数のみ稼働し、主人公を援護
- **過負荷自壊（Overload Disassemble）**: 寿命到達時に爆散し、周囲の敵を巻き込む

---

## 🏛️ クラシック機能（naRou Core）

- 🏰 **プロシージャル・ダンジョン**: 毎回変化する広大な多層ダンジョン探索
- 📜 **スキルツリー＆転職**: 70種類以上のスキルと15種のジョブクラス
- 🐾 **ペット育成システム**: 契約・進化・融合による相棒モンスターの育成
- 🌐 **Webブラウザプレイ対応**: `pyodide` / `brython` によるクライアントレス起動

---

## 🚀 クイックスタート

### 1. 必要な環境
- **Python 3.10 以上** (3.11〜3.14 推奨)
- **依存パッケージ**: `tcod`, `pygame`, `pillow`, `pyyaml`, `scipy`

### 2. インストールと起動

```bash
# 1. リポジトリのクローン
git clone <Repository_URL>
cd narou2

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. ゲーム起動
python main.py
```

### 3. アクセシビリティ（誰でも遊べる）

- **テキストモード（GPU不要）**: `python main.py` → `3` を選択、または `python main_text.py`。SDL/WebGL が使えない環境でもプレイ可能。
- **色覚多様性**: 起動メニューで `none/deutan/protan/tritan` を選択、または `COLOR_VISION=deutan` / Web `?a11y=deutan` / `config.yaml` の `accessibility.color_vision`。
- **難易度**: `easy/normal/hard` を選択（被ダメージ・敵HP・回復を補正）。
- **チュートリアル**: Web 起動時に操作手順を表示。詳細は `docs/accessibility_report.md`。

### 4. どこでも遊ぶ

- **ワンタッチ Web 起動**: `python main.py --open` でバックエンドを起動し、ブラウザを開く。
- **デバッグフレンドリー**: `run.py` スクリプトで環境を自動判定（GPU/テキストモード）して最適な起動方法を選択。
- **モバイル対応**: タッチジェスチャー、オンスクリーン D-pad、レスポンシブレイアウトに対応。
- **自動品質調整**: FPS が低下したらシェーダー効果を軽減し、快適なプレイを維持。

### 5. テストの実行

```bash
# Aの世界（スキル喰い）全統合テストの実行 (43 Tests)
python -m unittest tests/test_skill_eater_presentation_integration.py

# 各種フェーズ別単体テストの実行
python -m unittest discover tests/ "test_skill_eater_*.py"
```


---

## 🎨 Asset Pack Integration

naRou integrates three high-quality asset packs for richer graphics and immersion:

### Tiny Rogue (16x16 Tiles)
- **132 tiles** covering floors, walls, monsters, items, UI, effects, and player/NPC sprites
- Directional animation (4 directions × 4 frames) for monsters and player
- Packed atlas: `assets/tiles/tiny_rogue_atlas_16x16.png` (509×115)
- Mapped via `data/tile_mappings/tiny_rogue_dungeon.yaml`

### Audio SFX Pack
- **51 OGG sound effects** for footsteps, doors, UI interactions, ambient, combat
- Organized by category: `se_` (sound effects), `ui_` (UI), `amb_` (ambient)
- Manifest: `assets/audio/manifest.csv` with suggested_id mapping

### Emote Pack
- **256 emote sprites** across 8 pixel styles (32 per style)
- 18 emote types: anger, heart, question, sleep, laugh, alert, etc.
- Tilesheets for animated sequences: `assets/emote/tilesheets/pixel_style1.png` etc.

### Quick Usage
```python
from asset_manager import ASSET_MANAGER
from emote_system import play_emote, get_emote_frame, update_emotes

# Initialize
import yaml
with open("config.yaml") as f:
    ASSET_MANAGER.initialize(yaml.safe_load(f))

# Get tile atlas info
atlas_info = ASSET_MANAGER.get_tile_atlas_info("TR_FLOOR_01")

# Play sound by suggested_id
footstep = ASSET_MANAGER.get_audio_sfx_by_id("se_footstep_00")

# Play emote on entity
play_emote("player", "anger")
frame = get_emote_frame("player")

# Update each frame
update_emotes(delta_time)
```

See [ASSETS.md](ASSETS.md) for complete documentation.

---

## 🎨 臨場感・演出拡張システム (Audio / Emote / Visual FX)

Kenneyアセット（`audio`, `emote`, `tiny rogue`）を最大限に活用し、探索・戦闘・UIの臨場感を引き上げる**72ステップの演出モジュール**を統合しています。

- 🎵 **ダイナミックオーディオ (`audio/dynamic_audio.py`)**:
  - 10種類の足音のランダム選定 + 動的ピッチ揺らぎ（0.95〜1.05）
  - 本を開く音・布擦れ・コインなどのダイエグゼティックUI効果音
  - 距離減衰と左右パンニングによる3D空間オーディオ（敵の足音や開扉音の察知）
- 💬 **エモート＆フィードバック (`emote_feedback_system.py`)**:
  - 発見（！）や状態異常（汗・怒り・睡眠）の頭上ポップアップ
  - インタラクティブ対象接近時の弾むイージング（バウンス）アニメーション予兆
  - クリティカルヒット時の星アイコン・数字飛び出し演出（Floating Feedback）
- 🌟 **2Dライティング＆グラフィック演出 (`visual_fx_system.py`)**:
  - 松明の揺らぎ・暗闇レイヤー・視界くり抜きによる2D動的ライティング
  - 攻撃ヒット時のスクワッシュ＆ストレッチ変形＋画面シェイク（Juicy Animation）
  - ダンジョン内の浮遊ダスト粒子＆雪・泥・砂タイルの足跡デカール

---

## 🛠️ リポジトリ構成

```text
narou2/
├── skill_eater_presentation_system.py # 視覚＋聴覚 演出統括エンジン（Foley System）
├── skill_eater_combat_system.py       # 戦闘・捕食・深度解析ロジック
├── skill_eater_synthesis_system.py    # キメラ合成・錬金炉ロジック
├── skill_eater_economy_system.py      # 闇市場・支店買収・監査官レイド
├── skill_eater_servant_system.py      # Husk従属者タレットロジック
├── skill_eater_meta_quest_system.py   # ROOTハック・輪廻転生・世界法則改変
├── generate_rich_gifs.py              # 高品質フレームアニメーションGIF生成エンジン
├── generate_readme_gifs.py            # README用デモGIF生成（実ゲーム画面準拠のコンソール再現）
├── asset_manager.py                   # 統合アセット管理（Tiny Rogue / Audio / Emote）
├── emote_system.py                    # エモート再生・管理システム
├── scripts/
│   ├── resize_assets.py               # 画像リサイズツール
│   ├── convert_audio.py               # 音声変換ツール
│   └── generate_previews.py           # アセットプレビューHTML生成
├── demos/
│   └── demo_skill_eater_showcase.html # ブラウザ用インタラクティブWebデモ
├── assets/
│   ├── demo_combat_devour.gif         # GIF1: 捕食・戦闘篇
│   ├── demo_synthesis_economy.gif     # GIF2: 合成・経済篇
│   ├── demo_meta_reincarnation.gif    # GIF3: メタハック・輪廻転生篇
│   └── demo_husk_servant.gif          # GIF4: 従属者タレット篇
├── tiles/
│   ├── tiny_rogue_atlas_16x16.png     # パック済みタイルアトラス (509×115)
│   ├── tiny_rogue_atlas_16x16.json    # アトラスメタデータ (UV座標・アニメ情報)
│   └── tileset_*.png/.json            # 既存タイルセット (16/32/64)
├── tiny_rogue/                        # Tiny Rogue ソース画像 (132枚)
│   └── tiles/tile_0000.png - tile_0131.png
├── audio/                             # SFXオーディオアセット (51種)
│   ├── footstep00.ogg - footstep09.ogg
│   ├── doorOpen_*.ogg, doorClose_*.ogg
│   ├── book*.ogg, cloth*.ogg, metal*.ogg
│   └── manifest.csv                   # カテゴリ・suggested_id マッピング
├── emote/                             # エモートスプライト (256枚)
│   ├── pixel/style1/ - style8/        # 32エモート × 8スタイル
│   ├── tilesheets/pixel_style1.png - style8.png
│   ├── tilesheets/vector_style1.png - style8.png
│   └── spritesheets/                  # 予約領域
├── output/previews/                   # 生成プレビュー (HTML)
│   ├── index.html, tiles.html, audio.html, emotes.html
└── data/tile_mappings/
    └── tiny_rogue_dungeon.yaml        # 標準タイル→TR_* マッピング
```

## 🏗️ アーキテクチャ (リファクタリング後)

本プロジェクトは「Feature Package Architecture」に基づく疎結合設計です。

- **Kernel** (`packages/core/kernel/`): システム登録・依存解決・イベント配送のみを担う薄いカーネル。
- **Packages** (`packages/*/package.py`): Core/Gameplay/Character/Social/Meta/World/Narrative/Platform の各機能ドメイン。
- **Components** (`components.py`): ECS データコンポーネント（Attributes, Title, GuildFaction, Achievement, Reincarnation, Skill*, Storyteller, Archaeology, BaseStats, Economy, Level, Affection, PetProfile, Emote, PetAI）。
- **Managers** (`managers/`): Engine から抽出した処理単位（Combat, SkillReward, PetBond, WorldNews, Persistence, Faction, ContextMenu, StateMachine, SetupCoordinator）。
- **Entity** (`entity.py`): コンポーネントコンテナとしてのキャラクター基底クラス。`GodInfo` は `god_system.py` に分離。

詳細は `ARCHITECTURE.md` / `API.md` を参照。

---

## 📜 ライセンス
MIT License