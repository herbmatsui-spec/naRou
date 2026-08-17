# naRou: Masterpiece Edition (Commercial Release v1.0.0)

『naRou: Masterpiece Edition』は、本格ローグライクRPGの深遠なゲーム性と自由度をベースに、疎結合アーキテクチャ・ECS（Entity Component System）・スキルツリー・ジョブ・ギルド・派閥戦争・輪廻転生・ペット進化/融合・ストーリーテラー・Webクライアント連携を完全統合した商用クオリティのローグライクゲームです。

---

## 🎬 ゲームプレイ・デモ

<div align="center">
  <img src="demo_gameplay.gif" alt="naRou: Masterpiece Edition ゲームプレイデモ" width="700">
  <p><em>▲ 拠点〜ダンジョン探索〜ボス戦〜輪廻転生 NG+ のループプレビュー</em></p>
</div>

### 🎥 インタラクティブ実況プレイ & シーンギャラリー
ブラウザで直接動かして体験できる完全再現デモを提供しています：
- **実況プレイデモ（全24章・初心者ガイド付き）**: [`elona_playthrough.html`](elona_playthrough.html)
- **24シーン グランドショーケース**: [`demos/gallery_24_scenes.html`](demos/gallery_24_scenes.html)
- **絵文字グラフィックモード**: [`emoji_showcase.html`](emoji_showcase.html)

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

## 📄 ライセンス & クレジット
- **Version**: 1.0.0 (Commercial Edition)
- **Engine Architecture**: SystemManager ECS-coupled Engine

---

## 🌟 WebGLポストプロセス・ライティング拡張（ブランチ: feature/webgl-postprocess）

現在、`feature/webgl-postprocess` ブランチで、Webクライアントの没入感向上を目的とした拡張を開発中です。主な実装済み・検討中内容は以下の通りです。

### ✅ 実装済み
- **PixiJS v7 導入**: WebGLレンダラーへ移行し、レイヤー分離レンダリングを構築
- **レイヤー分離**: `backgroundLayer`, `tileLayer`, `entityLayer`, `effectLayer` を分離し、描画順を最適化
- **フォントテクスチャアトラス**: `tools/generate_font_atlas.py` で `demos/assets/font_atlas.png` / `font_atlas.json` を生成。`TextureAtlas.js` でグリフテクスチャを提供
- **タイル・エンティティ・アイテムのテクスチャ描画**: `TextureAtlas` を用いた Sprite 描画に置き換え、未使用時は Graphics フォールバック
- **動的ライティング**: `LightingSystem.js` によりサーバー側 `light_map` / `light_sources` を視覚化
- **パーティクルシステム**: `ParticleSystem.js` で移動・ヒット・魔法・回復・ダメージ演出を発生
- **ポストプロセス**: `PostProcessManager.js` でブルーム、グレイン、ビネットを提供
- **スクリーンシェイク**: `ScreenShake.js` でダメージ・爆発時の振動演出を実装
- **デモ**: `demos/particle_demo.html`, `demos/lighting_demo.html`, `demos/bloom_shake_demo.html` を追加

### 🚧 未反映の変更（未マージ・未反映）
現在、`feature/webgl-postprocess` ブランチ上にありますが、main ブランチへはまだマージされていません。

- **web_game_client.html**: PixiJS初期化、レイヤー定義、テクスチャアトラス読込、各システム統合
- **demos/lib/**: `TextureAtlas.js`, `LightingSystem.js`, `ParticleSystem.js`, `PostProcessManager.js`, `ScreenShake.js`
- **demos/assets/**: `font_atlas.png`, `font_atlas.json`
- **tools/**: `generate_font_atlas.py`
- **デモHTML**: `demos/particle_demo.html`, `demos/lighting_demo.html`, `demos/bloom_shake_demo.html`
- **Python バックエンド**: 本拡張では未変更（既存 `/api/state` JSON API を利用）

### ⚠️ 既知の注意点
- Python テスト一式は、本拡張とは無関係な既存インポートエラー（例: `title_manager.TITLE_MANAGER`）のために現在実行不可。Web クライアント単体では PixiJS CDN + モジュールロード後に初期化される構造に修正済み
- フォントアトラスは自動生成済みだが、より高度なタイルセット・モンスター固有グリフの追加は今後の拡張候補

---

## 🔧 開発者向け情報
