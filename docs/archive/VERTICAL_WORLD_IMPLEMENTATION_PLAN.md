# 垂直ワールド拡張実装計画書（10,000字程度）
## 地上・地下・異界・天界の4層構造 × バイオーム × 深度 × 次元マトリクス

### 実装概要
単一マップから多層ワールドへ拡張し、探索ボリュームを10倍以上に増加。バイオーム×深度×次元の3軸マトリクスを定義し、各層に固有モンスタ・資源・ボス・ギミックを配置。

---

## ステップ1-6: 基礎設計とデータ構造

### ステップ1: 現在のマップシステム分析 (Complete)
- `map_engine.py` の `GameMap` クラス分析済み
- タイルシステム、部屋生成、階段システムの理解
- `dungeon_themes.yaml` の現在構造把握

### ステップ2: 垂直ワールドの4層ゾーン設計
**ゾーン定義:**
1. **地上界 (Surface)**: 深度 0-10 (Y=0地表から上昇)
2. **地下界 (Underground)**: 深度 11-50 (従来のダンジョン範囲)
3. **異界 (Otherworld)**: 深度 51-100 (異次元的空間)
4. **天界 (Heaven)**: 深度 101-200 (神聖な高次元空間)

### ステップ3: 次元システム設計
**3つの次元:**
1. **物質次元 (Material)**: 通常の物理法則が適用される世界
2. **精神次元 (Ethereal)**: 魔法・精神・魂にフォーカスした世界
3. **虚無次元 (Void)**: 時間・空間が歪んだ異形の世界

### ステップ4: バイオーム分類設計
**8つのバイオームタイプ:**
- 平原 (Plains)
- 森林 (Forest)
- 山岳 (Mountains)
- 沼地 (Swamp)
- 砂漠 (Desert)
- 凍土 (Tundra)
- 火山地帯 (Volcanic)
- 遺跡地帯 (Ruins)

### ステップ5: 3軸マトリクス構造設計
**マトリクス構造: [ゾーン] × [バイオーム] × [深度] × [次元]**
- 各組み合わせに固有のテーマ・モンスタ・資源を設定
- 例: 地下界 × 森林 × 深度25 × 物質次元 = "腐敗した古代の森"
- 例: 天界 × 平原 × 深度150 × 精神次元 = "神聖なる光の草原"

### ステップ6: データスキーマ拡張計画
`dungeon_themes.yaml` の拡張構造:
```yaml
dungeon_themes:
  # 新しい構造: zone.biome.depth.dimension
  surface:
    plains:
      depth_0_5:
        material:
          theme_id: "surface_plains_shallow_material"
          # ... theme details
      depth_6_10:
        material:
          theme_id: "surface_plains_mid_material"
    # ... other biomes and depths
  underground:
    # ... similar structure
  otherworld:
    # ... similar structure
  heaven:
    # ... similar structure
```

---

## ステップ7-12: データファイル拡張

### ステップ7: dungeon_themes.yaml のベース構造拡張
4層ゾーン構造を追加し、各ゾーンにバイオーム・深度・次元のネスト構造を定義。

### ステップ8: モンスタープール拡張設計
各テーマに以下を設定:
- `common_enemies`: 一般的な出現モンスター
- `uncommon_enemies`: 時々出現するモンスター
- `rare_enemies`: 稀に出現するモンスター
- `unique_boss`: その層固有のボス
- `special_spawns`: 特殊条件での出現

### ステップ9: 資源・アイテムテーブル設計
各層・バイオーム・次元ごとに固有の:
- 採掘可能鉱石
- 採取可能ハーブ
- 宝箱アイテムテーブル
- 特殊アイテムドロップ

### ステップ10: ボス・ギミック設計
各層に固有の:
- ボスキャラクター（ステータス・スキル・行動パターン）
- 環境ギミック（トラップ・パズル・ギミックイベント）
- 特殊イベントトリガー
- 隠し要素・秘密エリア

### ステップ11: 階層間移動システム設計
移動手段:
- **階段**: 従来の上下移動（隣接深度間のみ）
- **ポータル**: 同一深度での次元間移動
- **儀式場**: 特殊条件下での遠距離層間移動
- **風穴・裂け目**: ランダムな次元間・層間移動

### ステップ12: 初期データ投入・バランス調整
- 各マトリクスセルに初期テーマデータを投入
- モンスター難易度曲線の調整
- 資源レア度のバランス調整
- ボス強度の段階的設計

---

## ステップ13-18: コアエンジン実装

### ステップ13: WorldLayerクラス実装
`world_layer.py` に新規作成:
```python
class WorldLayer:
    """単一のワールド層を表すクラス"""

    def __init__(self, zone: str, biome: str, depth: int, dimension: str):
        self.zone = zone  # surface, underground, otherworld, heaven
        self.biome = biome  # plains, forest, mountains, etc.
        self.depth = depth  # 0-200 (actual depth level)
        self.dimension = dimension  # material, ethereal, void
        self.game_map: Optional[GameMap] = None
        self.theme_data: Dict[str, Any] = {}

    def load_theme(self) -> None:
        """dungeon_themes.yaml からテーマデータをロード"""

    def generate_map(self, width: int, height: int) -> GameMap:
        """テーマに基づいてマップを生成"""

    def get_monster_pool(self) -> Dict[str, List[str]]:
        """現在の層に基づくモンスタープールを取得"""

    def get_resources(self) -> Dict[str, Any]:
        """資源・アイテムテーブルを取得"""
```

### ステップ14: WorldMapManagerクラス実装
`world_map_manager.py` に新規作成:
```python
class WorldMapManager:
    """マルチレイヤーワールドを管理するクラス"""

    def __init__(self):
        self.layers: Dict[Tuple[str, str, int, str], WorldLayer] = {}
        self.active_layers: Set[Tuple[str, str, int, str]] = set()
        self.player_position: Dict[str, Any] = {}  # 現在のプレイヤー位置（層別）

    def get_or_create_layer(
        self, zone: str, biome: str, depth: int, dimension: str
    ) -> WorldLayer:
        """指定された層を取得または作成"""

    def load_layer(self, zone: str, biome: str, depth: int, dimension: str) -> GameMap:
        """層をロードしてGameMapを返す"""

    def unload_layer(self, zone: str, biome: str, depth: int, dimension: str) -> None:
        """使用していない層をアンロード（メモリ節約）"""

    def get_adjacent_layers(
        self, zone: str, biome: str, depth: int, dimension: str
    ) -> List[WorldLayer]:
        """移動可能な隣接層を取得"""
```

### ステップ15: GameMapクラス拡張（マルチレイヤー対応）
`map_engine.py` の `GameMap` クラスに追加:
```python
# GameMapクラスに追加
def __init__(
    self,
    width: int,
    height: int,
    map_type: str = "dungeon",
    floor_level: int = 1,
    world_layer: Optional[WorldLayer] = None,
):
    # ... existing code ...
    self.world_layer = world_layer  # 新規追加


def is_stairs_down_available(self) -> bool:
    """下り階段が次の層へ続くかチェック"""


def is_stairs_up_available(self) -> bool:
    """上り階段が前の層へ続くかチェック"""


def get_layer_transition_info(self) -> Dict[str, Any]:
    """階層間移動に必要な情報を取得"""
```

### ステップ16: 階層間移動ロジック実装
`map_engine.py` に移動処理を追加:
```python
def handle_stairs_interaction(
    self, player_x: int, player_y: int, world_manager: WorldMapManager
) -> Optional[Tuple[int, int, str]]:
    """
    階段との相互作用を処理し、必要なら層移動を返す
    返り値: (new_x, new_y, target_layer_key) または None（移動なし）
    """
    # 下り階段に立っているかチェック
    if self.tiles[player_x][player_y] == TILE_STAIRS_DOWN:
        # 現在の層情報を取得
        if self.world_layer:
            current_key = (
                self.world_layer.zone,
                self.world_layer.biome,
                self.world_layer.depth,
                self.world_layer.dimension,
            )

            # 次の層を決定（ゾーン境界も考慮）
            target_layer = self._calculate_target_layer_down(world_manager)
            if target_layer:
                # 次の層の入口座標を計算（通常は上り階段の位置）
                entrance_pos = target_layer.get_entrance_position()
                return (
                    entrance_pos[0],
                    entrance_pos[1],
                    f"{target_layer.zone}:{target_layer.biome}:{target_layer.depth}:{target_layer.dimension}",
                )

    # 上り階段の同様の処理
    # ...
    return None
```

### ステップ17: バイオーム固有マップジェネレーター実装
各バイオームタイプごとに特殊な地形生成ロジックを実装:
- 森林: 木の密度・大きさの変化・光のフィルター効果
- 山岳: 階段状地形・洞窟・崖
- 沼地: 水たまり・毒沼・動く地面
- 砂漠: オアシス・砂嵐・遺跡
- 凍土: 氷・雪・吹雪・凍った湖
- 火山地帯: ラバ流・火山噴火・熱ダメージゾーン
- 遺跡地帯: 破壊された建物・トラップ・謎解き要素

### ステップ18: モンスタースポーンシステム連携
`world_layer.py` にモンスターゲネレーションロジックを実装:
```python
def spawn_monsters_for_area(
    self, game_map: GameMap, area_rect: Tuple[int, int, int, int]
) -> List[Entity]:
    """
    指定領域にテーマに基づくモンスターをスポーン
    """
    monster_pool = self.get_monster_pool()
    spawned = []

    # エリアサイズに基づくスポーン数計算
    area_size = (area_rect[2] - area_rect[0]) * (area_rect[3] - area_rect[1])
    spawn_count = int(area_size * self.get_spawn_density())

    for _ in range(spawn_count):
        # モンスタープールから重み付きランダム選択
        monster_type = self._select_monster_by_rarity(monster_pool)
        # 出現位置決定（プレイヤーから一定距離確保など）
        pos = self._find_valid_spawn_position(game_map, area_rect)
        if pos:
            entity = self._create_monster_entity(monster_type, pos)
            spawned.append(entity)

    return spawned
```

---

## ステップ19-24: 統合とシステム連携

### ステップ19: WorldStateSystemとの統合
`world_state_system.py` に層情報の永続化を追加:
```python
# WorldStateTemplateに追加
player_layer_history: List[Dict[str, Any]] = field(default_factory=list)
visited_layers: Set[str] = field(default_factory=set)  # ゾーン:バイオーム:深度:次元形式
layer_discoveries: Dict[str, Any] = field(default_factory=dict)
```

### ステップ20: セーブ/ロードシステム拡張
セーブデータに層スタック情報を含める:
```yaml
# savegame.yaml の構造例
player:
  position: {x: 50, y: 30}
  current_layer: "underground:forest:25:material"
layer_states:
  underground:forest:25:material:
    explored_tiles: [...]  # 探索済みタイル
    spawned_entities: [...]  # 現在存在するエンティティ
    map_modifications: [...]  # プレイヤーによるマップ変更
  surface:plains:5:material:
    # ... 同様の構造
```

### ステップ21: UI・表示システム連携
プレイヤーに現在の位置情報を表示:
- 画面上部にゾーム・バイオーム・深度・次元を表示
- ミニマップに層移動可能な方向を示す矢印
- 層移動時のエフェクト・トランジション実装

### ステップ22: クエスト・イベントシステム連携
特定の層でのイベントトリガー:
- 「天界の門を開けよ」クエスト（特定の天界層到達で発動）
- 「異界の封印を解く」イベント（特殊な儀式の実施必要）
- 深度別の達成度システム（「地下100階到達」等）

### ステップ23: バランシング・難易度調整システム
層ごとの難易度曲線を実装:
```python
def get_difficulty_multiplier(self) -> float:
    base_difficulty = 1.0
    # ゾーンベースの難易度
    zone_multipliers = {
        "surface": 0.5,
        "underground": 1.0,
        "otherworld": 2.0,
        "heaven": 3.0,
    }
    # 深度による補正
    depth_factor = 1.0 + (self.depth * 0.01)  # 1階層ごとに1%増加
    # 次元による補正
    dimension_multipliers = {"material": 1.0, "ethereal": 1.5, "void": 2.0}

    return (
        zone_multipliers.get(self.zone, 1.0)
        * depth_factor
        * dimension_multipliers.get(self.dimension, 1.0)
    )
```

### ステップ24: パフォーマンス最適化
- 非アクティブ層のアンロード・メモリ解放
- チャンクベースのレイヤー読み込み
- 描画範囲外のタイルの更新頻度削減
- モンスタAIの層間非アクティブ時の停止

---

## ステップ25-30: テスト・バランス・調整

### ステップ25: 基本機能テスト
- 各層への正常な移動・戻り
- 階段・ポータルによる層間移動の正常動作
- マップ生成の各層・バイオーム・次元別の違い確認

### ステップ26: モンスターバランステスト
- 各層でのモンスタ出現頻度・種類の適切性
- 難易度曲線の滑らかさ確認（急激なジャンプがないか）
- ボス戦の適切な難易度・報酬バランス

### ステップ27: 探索ボリューム測定
10倍以上の探索ボリューム達成確認のため:
- 各層の平均マップサイズ × アクティブ層数の計算
- 実際のプレイテストによる探索時間測定
- コンテンツ量（モンスタ種類・アイテム種類・イベント数）の比較

### ステップ28: リソース・経済バランステスト
- 各層での資源入手難易度の適切性
- レアアイテムの分布バランス（天界層に神器が集中しすぎないか）
- インフレ防止のためのゴールド・資源供給量調整

### ステップ29: ストレステスト・パフォーマンス検証
- 多数の層同時ロード時のメモリ使用量
- 頻繁な層間移動時のラグ・チラつき
- 大規模マップ生成時のロード時間
- 長時間プレイ時のメモリリークチェック

### ステップ30: フィードバックベースの調整
- プレイテスト結果に基づく難易度調整
- つまらない・同じような層の識別・改善
- アクセス困難・不親切な層移動手段の改善

---

## ステップ31-36: 最終仕上げ・ドキュメント・リリース準備

### ステップ31: コード品質チェック・リファクタリング
- コーディング規約への準拠確認
- 重複コードの除去・関数の適切な分割
- エラーハンドリングの充実
- 型ヒント・docstringの追加

### ステップ32: 既存機能との後方互換性確認
- 従来のシングルマッププレイがまだ可能か
- 既存セーブデータの読み込み・変換処理
- 既存MOD・カスタムコンテンツへの影響評価

### ステップ33: ローカライズ対応
- 新規追加されたすべてのテキストの国際化対応
- 日本語・英語・その他言語での表示確認
- フォントサイズ・UIレイアウトへの対応

### ステップ34: ドキュメント作成・チュートリアル実装
- プレイヤー向けマルチレイヤーシステム説明
- 開発者向けテーマ追加ガイド
- チュートリアルマップでの段階的層システム紹介

### ステップ35: リリース前最終テスト
- 完全なプレイフローテスト（チュートリアル→エンディング）
- 異常系・エッジケースのテスト
- マルチプレイ・コオプモードでの動作確認（該当する場合）

### ステップ36: リリース準備・メタデータ更新
- バージョン番号の更新（1.0.0 → 2.0.0）
- チェンジログの作成（「垂直ワールドシステム実装」等）
- パッケージング・配布準備
- リリースノートの作成

---

## 詳細実装スケジュール概算

**フェーズ1: 基盤構築 (ステップ1-12)** 約3-4日
- デザイン・データ構造設計
- YAMLスキーマ設計・初期データ投入

**フェーズ2: コアエンジン実装 (ステップ13-18)** 約5-6日
- WorldLayer・WorldMapManager実装
- GameMap拡張・移動ロジック実装

**フェーズ3: システム統合 (ステップ19-24)** 約4-5日
- ワールドステート・セーブロード連携
- UI・クエスト・バランシングシステム連携

**フェーズ4: テスト・調整 (ステップ25-30)** 約3-4日
- 各種テスト・バランス調整・パフォーマンス最適化

**フェーズ5: 仕上げ (ステップ31-36)** 約2-3日
- コード品質・ドキュメント・最終テスト

**総 estimated: 約17-22日**

---

## 期待される効果

### 探索ボリュームの10倍以上達成
- 従来: 1マップタイプ × 約50階層の深度
- 新システム: 4ゾーン × 8バイオーム × 200深度 × 3次元 = 19,200潜在的組み合わせ
- 実際のアクティブ組み合わせ（制約後でも）: 約500-1000+のユニークなマップ

### 新たなゲームプレイの可能性
- 層間移動をパズル要素として活用（「天界に到達するには特殊な条件が必要」）
- 次元間の資源交換経済（「虚無次元のレア鉱石を物質次元で高価販売」）
- ストーリー要素としての層探索（「失われた天界の文明を地下遺跡で発見」）

### モデラー・コンテンツクリエイターへの恩恵
- テーマ追加の容易さ（YAMLファイル追加のみで新しい層が追加可能）
- 階層・バイオーム・次元ごとの細かいチューニング可能
- 既存のモンスター・アイテムデータの流用が可能

---

## リスク管理と代替案

### 主要リスク
1. **パフォーマンス劣化**: レイヤー数増加によるメモリ・CPU負荷増大
   - 対策: レイヤーアンロード機能・チャンクロード・描画最適化

2. **設計の複雑さ増大**: 実装・デバッグの難易度上昇
   - 対策: モジュラー設計・段階的実装・各ステップでのテスト

3. **ゲームバランスの崩壊**: 一部の層が極端に易しすぎ／難しすぎ
   - 対策: 難易度曲線関数による自動調整・プレイテストベースの微調整

### 代替アプローチ（段階的実装）
もしフル実装が困難な場合の最小構成:
1. ステップ1-6: 基礎設計のみ実装
2. ステップ7-9: dungeon_themes.yaml拡張・基本データ投入
3. ステップ13-15: WorldLayer・WorldMapManager基本実装
4. ステップ16: 基本的な階層間移動（階段のみ）
5. 残りは後のアップデートで段階的に追加

この計画により、単一マップから多層ワールドへの拡張を体系的に実装し、探索ボリューム10倍以上の目標を達成しながら、ゲームの楽しさとバランスを維持できます。
