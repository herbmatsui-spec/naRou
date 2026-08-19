# naRou: Masterpiece Edition

**Elona風ローグライクRPG** - Python + tcod で作られた本格派ダンジョン探索ゲーム

## 🎮 これは何？

`naRou` は、日本のフリーゲーム「Elona」にインスパイアされたローグライクRPGです。ダンジョンを探索し、モンスターと戦い、キャラクターを育成し、装備を集め、より深い階層を目指します。

**主な特徴：**
- 🏰 **プロシージャル生成ダンジョン** - 毎回違うマップで冒険
- ⚔️ **ターン制戦闘** - 戦略的なバトルシステム
- 🌳 **スキルツリー・ジョブシステム** - 70種類以上のスキルと転職
- 🐾 **ペットシステム** - 仲間モンスターの契約・進化・融合
- 🏛️ **ギルド・派閥システム** - 所属勢力による恩恵と対立
- ♾️ **輪廻転生（ニューゲーム+）** - 周回プレイで強くなるメタ進行
- 🌐 **Webブラウザ対応** - インストール不要でブラウザからプレイ可能
- 🎨 **絵文字グラフィックモード** - 文字だけでなく視覚的にも楽しめる

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
```

---

## 🌐 Webクライアントについて

`web_game_client.html` と `web_server.py` でブラウザプレイに対応しています。

- **WebSocket** でリアルタイム通信
- **ローカルネットワーク内**ならスマホからも接続可能
- `web/theme.css` でテーマカスタマイズ可能

---

## 📚 学習リソース（初心者向け）

ローグライク開発に興味がある方へ：

1. **Python基礎** → [Python公式チュートリアル](https://docs.python.org/ja/3/tutorial/)
2. **tcodライブラリ** → [python-tcod ドキュメント](https://python-tcod.readthedocs.io/)
3. **ローグライク開発** → [Roguelike Tutorial (Python+tcod)](https://rogueliketutorials.com/tutorials/tcod/)
4. **ECSアーキテクチャ** → [Entity Component System 解説](https://en.wikipedia.org/wiki/Entity_component_system)

---

## 🤝 貢献・フィードバック

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