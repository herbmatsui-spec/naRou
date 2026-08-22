# SkillEaterDungeonFloorManager - 72ステップ実装計画

## 概要
現状のフラットな4部屋（`DungeonRoom`）から、テーマ別フロア構造・フロア間移動・深度スケーリング・音響/エモート演出を統合した多層ダンジョンシステムを構築する。

**対象ファイル**: `skill_eater_dungeon_floor_manager.py` (新規作成)
**連携**: `skill_eater_exploration_system.py`, `skill_eater_audio_system.py`, `skill_eater_presentation_system.py`, `procedural_dungeon_generator.py`, `data/dungeon_themes.yaml`

---

## フェーズ 1: データ構造定義 (Steps 1-12)

### Step 1: `DungeonFloor` データクラス定義
```python
@dataclass
class DungeonFloor:
    floor_id: str
    depth: int
    theme: str  # INDUSTRIAL_RUINS / NEON_SEWERS / MIDAS_LABS / BABEL_CORE
    rooms: list[DungeonRoom]
    boss_room: DungeonRoom | None = None
    exit_to_next: dict | None = None  # {"type": "stairs|elevator", "position": (x,y), "target_floor": str}
    hazard_level: int = 0  # 0-100 概念侵食レベル
    cleared: bool = False
```
- `skill_eater_dungeon_floor_manager.py` 新規作成、冒頭に配置
- `DungeonRoom` は既存のものを import して再利用

### Step 2: `DungeonTheme` Enum 定義
```python
class DungeonTheme(Enum):
    INDUSTRIAL_RUINS = "industrial_ruins"      # 廃工場
    NEON_SEWERS = "neon_sewers"                # ネオン下水道
    MIDAS_LABS = "midas_labs"                  # ミダス研究棟
    BABEL_CORE = "babel_core"                  # バベル核心
```
- テーマIDは `data/dungeon_themes.yaml` のキーと整合させる

### Step 3: `FloorTransitionType` Enum 定義
```python
class FloorTransitionType(Enum):
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"
    ELEVATOR = "elevator"
    EMERGENCY_SHAFT = "emergency_shaft"  # 緊急脱出用
```

### Step 4: `DepthScalingConfig` データクラス定義
```python
@dataclass
class DepthScalingConfig:
    base_enemy_tier: int = 1
    enemy_tier_per_depth: float = 0.1
    base_trap_density: float = 0.1
    trap_density_per_depth: float = 0.02
    base_reward_multiplier: float = 1.0
    reward_multiplier_per_depth: float = 0.05
    boss_spawn_depth_interval: int = 10
```

### Step 5: テーマ別設定 YAML 追加 (`data/dungeon_themes.yaml`)
```yaml
dungeon_themes:
  industrial_ruins:
    theme_id: "industrial_ruins"
    name: "廃工場跡"
    base_layout: "factory_grid"
    difficulty_modifier: 1.2
    depth_range: [1, 15]
    enemy_pools:
      common: ["scrap_golem", "rust_stalker", "oil_slime"]
      elite: ["assembly_line_overseer", "toxic_furnace"]
    environmental_hazards: ["conveyor_belt", "chemical_leak", "spark_shower"]
    special_rooms: ["control_room", "storage_warehouse", "maintenance_shaft"]
    transition_sounds:
      stairs: "stair_creak.ogg"
      elevator: "elevator_hum.ogg"
    transition_emotes:
      down: "emote_arrow_down.png"
      up: "emote_arrow_up.png"

  neon_sewers:
    theme_id: "neon_sewers"
    name: "ネオン下水道"
    base_layout: "sewer_network"
    difficulty_modifier: 1.4
    depth_range: [16, 30]
    enemy_pools:
      common: ["neon_rat", "glow_slime", "pipe_wraith"]
      elite: ["sewer_king", "chemical_abomination"]
    environmental_hazards: ["toxic_current", "neon_gas", "electrified_water"]
    special_rooms: ["pump_station", "filtration_chamber", "junction_box"]
    transition_sounds:
      stairs: "stair_creak.ogg"
      elevator: "elevator_hum.ogg"
    transition_emotes:
      down: "emote_arrow_down.png"
      up: "emote_arrow_up.png"

  midas_labs:
    theme_id: "midas_labs"
    name: "ミダス研究棟"
    base_layout: "lab_complex"
    difficulty_modifier: 1.8
    depth_range: [31, 50]
    enemy_pools:
      common: ["test_subject", "security_drone", "mutated_scientist"]
      elite: ["lab_director", "prototype_weapon"]
    environmental_hazards: ["containment_breach", "radiation_zone", "mind_control_field"]
    special_rooms: ["experiment_log", "specimen_vault", "server_room"]
    transition_sounds:
      stairs: "stair_creak.ogg"
      elevator: "elevator_hum.ogg"
    transition_emotes:
      down: "emote_arrow_down.png"
      up: "emote_arrow_up.png"

  babel_core:
    theme_id: "babel_core"
    name: "バベル核心"
    base_layout: "core_chamber"
    difficulty_modifier: 2.5
    depth_range: [51, 99]
    enemy_pools:
      common: ["babel_guardian", "concept_warden", "law_enforcer"]
      elite: ["master_skill_holder", "reality_anchor"]
    environmental_hazards: ["reality_erosion", "concept_collapse", "time_dilation"]
    special_rooms: ["master_chamber", "concept_archive", "world_core"]
    transition_sounds:
      stairs: "stair_creak.ogg"
      elevator: "elevator_hum.ogg"
    transition_emotes:
      down: "emote_arrow_down.png"
      up: "emote_arrow_up.png"
```

### Step 6: `DungeonThemeRegistry` へのテーマ別設定読み込み対応
- `procedural_dungeon_generator.py` の `DungeonThemeRegistry.load()` を拡張
- 新しいテーマ構造（`depth_range`, `transition_sounds`, `transition_emotes`）をパース
- 既存テーマとの互換性維持

### Step 7: `SkillEaterDungeonFloorManager` クラス定義（スケルトン）
```python
class SkillEaterDungeonFloorManager:
    def __init__(
        self,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
        dungeon_generator: ProceduralDungeonGenerator | None = None,
    ):
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.generator = dungeon_generator or ProceduralDungeonGenerator()
        self.floors: dict[str, DungeonFloor] = {}
        self.current_floor_id: str | None = None
        self.current_depth: int = 0
        self.scaling_config = DepthScalingConfig()
        self.theme_registry = DungeonThemeRegistry()
```

### Step 8: シングルトンパターン実装 (`get_instance`, `reset_instance`)
- 既存システムと同じパターンで実装

### Step 9: フロア生成メソッド `_generate_floor(floor_id: str, depth: int, theme: DungeonTheme) -> DungeonFloor`
- `procedural_dungeon_generator.generate_from_spec()` を活用
- テーマ別 `depth_range` からテーマ決定
- 部屋数: `3 + depth // 5` (最小3, 最大12)
- ボス部屋: `depth % 10 == 0` で生成

### Step 10: ダンジョン全体初期化 `initialize_dungeon(max_depth: int = 99) -> None`
- 深度1から順にフロア生成
- テーマ遷移: 1-15=INDUSTRIAL_RUINS, 16-30=NEON_SEWERS, 31-50=MIDAS_LABS, 51-99=BABEL_CORE
- 各フロアの `exit_to_next` を設定（階段/エレベーターをランダム配置）

### Step 11: 現在フロア取得 `get_current_floor() -> DungeonFloor | None`

### Step 12: 現在部屋取得 `get_current_room() -> DungeonRoom | None`
- 既存 `SkillEaterExplorationSystem.current_room_id` と連携

---

## フェーズ 2: フロア移動システム (Steps 13-28)

### Step 13: `can_descend() -> bool` - 降下可能判定
- 現在フロアの `exit_to_next` が存在し、ボス部屋クリア済みなら True

### Step 14: `can_ascend() -> bool` - 上昇可能判定
- `current_depth > 1` かつ 前フロアの `exit_to_next` が双方向対応なら True

### Step 15: `can_use_elevator() -> bool` - エレベーター使用可能判定
- 現在フロアに `exit_to_next.type == "elevator"` かつ 電力確保済み（後でフラグ追加）

### Step 16: `descend_stairs() -> FloorTransitionResult` - 階段降下
```python
@dataclass
class FloorTransitionResult:
    success: bool
    message: str
    previous_floor_id: str
    new_floor_id: str | None
    transition_type: FloorTransitionType
    played_sounds: list[str]
    presentation_events: list[PresentationEvent]
    hazard_change: int
```
- 音声: `stair_creak.ogg` (3回連続) + `floor_transition_woosh.ogg`
- エモート: `emote_arrow_down.png`
- 深度+1, ハザード+5

### Step 17: `ascend_stairs() -> FloorTransitionResult` - 階段上昇
- 音声: `stair_creak.ogg` (3回連続, 高めピッチ) + `floor_transition_woosh.ogg`
- エモート: `emote_arrow_up.png`
- 深度-1, ハザード-10 (最小0)

### Step 18: `use_elevator(target_depth: int | None = None) -> FloorTransitionResult` - エレベーター移動
- 音声: `elevator_hum.ogg` (ループ風長め) + `floor_transition_woosh.ogg`
- エモート: `emote_arrow_down.png` または `emote_arrow_up.png`
- 対象フロア指定可能（未指定なら次フロア）
- ハザード変化なし（安全移動）

### Step 19: 共通遷移処理 `_perform_transition(target_floor_id: str, transition_type: FloorTransitionType) -> FloorTransitionResult`
- 現在フロアのクリーンアップ
- 新フロアの初期化（入口部屋を `current_room_id` に設定）
- `SkillEaterExplorationSystem.current_room_id` 更新
- 演出キュー・音声キューへの登録

### Step 20: 階段降下用演出シーケンス `_build_stairs_down_sequence() -> tuple[list[str], list[PresentationEvent]]`
- `stair_creak.ogg` x3 (間隔200ms)
- `floor_transition_woosh.ogg` x1
- `emote_arrow_down.png` + メッセージ「階段を降りる...」

### Step 21: 階段上昇用演出シーケンス `_build_stairs_up_sequence()`
- `stair_creak.ogg` x3 (ピッチ+10%)
- `floor_transition_woosh.ogg` x1
- `emote_arrow_up.png` + メッセージ「階段を登る...」

### Step 22: エレベーター用演出シーケンス `_build_elevator_sequence(direction: str)`
- `elevator_hum.ogg` (2秒間ループ風)
- `floor_transition_woosh.ogg` x1
- 方向に応じたエモート + メッセージ「エレベーターで移動中...」

### Step 23: 移動失敗時の演出 `_build_failed_transition_sequence(reason: str)`
- `buzzer.ogg` または `error.ogg`
- `emote_alert.png` + 失敗理由メッセージ

### Step 24: `emergency_escape() -> FloorTransitionResult` - 緊急脱出（地上へ強制帰還）
- 深度に関わらず depth=0 (surface) へ
- 音声: `warp.ogg` + `floor_transition_woosh.ogg`
- エモート: `emote_exclamation.png`
- ペナルティ: 所持スキル1つ喪失、ハザードリセット

### Step 25: フロアクリア判定 `check_floor_clear() -> bool`
- 現在フロアの全必須部屋探索済み かつ ボス部屋クリア済み

### Step 26: フロアクリア処理 `clear_current_floor() -> FloorClearResult`
```python
@dataclass
class FloorClearResult:
    success: bool
    cleared_floor: str
    next_floor: str | None
    rewards: list[str]
    hazard_purge_amount: int
    concept_shards: int
```
- ハザード -50 (最小0)
- 報酬: 深度ベーススケーリング適用

### Step 27: 次フロア自動生成 `_ensure_next_floor_exists() -> str`
- 存在しないなら生成して返す

### Step 28: 移動履歴管理 `transition_history: list[FloorTransitionRecord]`
```python
@dataclass
class FloorTransitionRecord:
    timestamp: float
    from_floor: str
    to_floor: str
    transition_type: FloorTransitionType
    hazard_before: int
    hazard_after: int
```

---

## フェーズ 3: 深度スケーリングシステム (Steps 29-40)

### Step 29: 敵ティア計算 `calculate_enemy_tier(depth: int) -> int`
- 式: `base_tier + int(depth * enemy_tier_per_depth)`
- ティア1=コモン, 2=アンコモン, 3=レア, 4=エリート, 5=ボス級

### Step 30: トラップ密度計算 `calculate_trap_density(depth: int) -> float`
- 式: `min(0.8, base_trap_density + depth * trap_density_per_depth)`
- 部屋生成時のトラップ配置確率に使用

### Step 31: 報酬倍率計算 `calculate_reward_multiplier(depth: int) -> float`
- 式: `base_reward_multiplier + depth * reward_multiplier_per_depth`
- 上限 3.0倍

### Step 32: テーマ別敵プール選択 `get_enemy_pool_for_depth(depth: int) -> dict`
- 現在のテーマから `enemy_pools` 取得
- ティアに応じて common/uncommon/rare/elite を選択

### Step 33: テーマ別ハザード選択 `get_hazards_for_depth(depth: int) -> list[str]`
- 現在テーマの `environmental_hazards` から密度に応じて選択

### Step 34: テーマ別特殊部屋選択 `get_special_rooms_for_depth(depth: int) -> list[str]`
- 現在テーマの `special_rooms` から深度に応じて選択

### Step 35: ボス生成判定 `should_spawn_boss(depth: int) -> bool`
- `depth % boss_spawn_depth_interval == 0`

### Step 36: ボス敵選択 `select_boss_for_depth(depth: int) -> str`
- テーマ別 `enemy_pools.unique_boss` または `elite` から選択

### Step 37: フロア生成時のスケーリング適用 `_apply_depth_scaling(floor: DungeonFloor) -> None`
- 部屋の敵・トラップ・報酬にスケーリング適用
- `DungeonRoom.enemies` を深度適正ティアで再生成

### Step 38: ハザードレベル更新 `update_hazard_level(delta: int) -> int`
- 0-100 でクランプ
- 閾値超過時のデバフ適用通知

### Step 39: ハザードデバフ取得 `get_hazard_debuffs() -> list[str]`
- 30以上: "Concept Leaking: MP Cost +20%"
- 60以上: "Gravity Distortion: Turn Time -30%"
- 90以上: "Total Reality Breakdown: Continuous HP Erosion"

### Step 40: マップ構造変化トリガー `check_map_mutation() -> str | None`
- ハザード50以上でショートカット遮断など
- 既存 `BankDungeonManager` のロジックを参考に統合

---

## フェーズ 4: 音響・エモート演出統合 (Steps 41-52)

### Step 41: 必要音声ファイル確認・配置ガイド作成
```
assets/audio/
├── stair_creak.ogg        # 階段きしみ音（共通）
├── elevator_hum.ogg       # エレベーター稼働音（共通）
├── floor_transition_woosh.ogg  # フロア遷移ウーシュ音（共通）
├── warp.ogg               # 緊急脱出ワープ音
└── buzzer.ogg             # 失敗ブザー音
```
- 既存 `AUDIO_DIR` (`assets/audio/`) に配置
- なければ無音スキップ（既存 `play_sound` 仕様準拠）

### Step 42: 必要エモートファイル確認・配置ガイド作成
```
assets/emote/pixel/style1/
├── emote_arrow_down.png   # 下矢印（降下・エレベーター下）
├── emote_arrow_up.png     # 上矢印（上昇・エレベーター上）
├── emote_exclamation.png  # 既存使用中
├── emote_alert.png        # 既存使用中
└── emote_dots2.png        # 既存使用中
```
- 既存 `EMOTE_DIR` に配置

### Step 43: テーマ別遷移音声上書き機能
- `DungeonThemeData` に `transition_sounds` 追加済み（Step 5）
- フロアごとに異なる音声を上書き可能にする

### Step 44: 遷移時のテーマ別音声選択 `_get_transition_sounds(theme: DungeonTheme, transition_type: FloorTransitionType) -> dict`
```python
return {
    "loop": theme.transition_sounds.get("elevator", "elevator_hum.ogg"),
    "step": theme.transition_sounds.get("stairs", "stair_creak.ogg"),
    "woosh": "floor_transition_woosh.ogg"
}
```

### Step 45: 遷移時のテーマ別エモート選択 `_get_transition_emotes(theme: DungeonTheme, direction: str) -> str`
- `direction`: "down" | "up"
- `theme.transition_emotes[direction]` を返す

### Step 46: 演出システムへの登録ヘルパー `_queue_transition_presentation(sounds: list[str], emote: str, message: str)`
- `presentation.add_event()` を順次呼び出し
- `audio.play_sound()` も並行実行

### Step 47: 遷移中の「移動中」表示用イベント `_create_traveling_event(duration_ms: int) -> PresentationEvent`
- `vr_grid_effect: True` でグリッドエフェクト表示
- メッセージ: "次のフロアへ移動中..."

### Step 48: 到着時の部屋進入演出 `_create_room_entry_event(room: DungeonRoom) -> PresentationEvent`
- テーマ別入室音（既存 `doorOpen_1.ogg` をベースにテーマ音追加）
- エモート: `emote_dots2.png` (通常) / `emote_exclamation.png` (ボス部屋)

### Step 49: ボス部屋前演出 `_create_boss_approach_event() -> list[PresentationEvent]`
- 警告音 `alarm.ogg` または `warning.ogg`
- エモート: `emote_alert.png` x2 + `emote_exclamation.png`
- メッセージ: "強大な気配を感じる..."

### Step 50: フロアクリア演出 `_create_floor_clear_event(floor: DungeonFloor) -> list[PresentationEvent]`
- ファンファーレ `fanfare.ogg` または `victory.ogg`
- エモート: `emote_star.png` + `emote_heart.png`
- メッセージ: "フロアクリア！ 次の階層へ進めます。"

### Step 51: ハザード上昇時演出 `_create_hazard_rise_event(level: int) -> PresentationEvent`
- 不気味な音 `ambience_dark.ogg` または `heartbeat.ogg`
- エモート: `emote_alert.png`
- メッセージ: f"概念侵食レベル {level}% - 現実が歪み始めた..."

### Step 52: 音声・エモート欠損時のフォールバック
- ファイル不在時はログ出力のみで継続
- `is_mock_only=True` モードでのテスト対応

---

## フェーズ 5: ExplorationSystem 統合 (Steps 53-60)

### Step 53: `SkillEaterExplorationSystem` に `floor_manager` 参照追加
```python
def __init__(..., floor_manager: SkillEaterDungeonFloorManager | None = None):
    self.floor_manager = floor_manager or SkillEaterDungeonFloorManager.get_instance()
```

### Step 54: `move_to_room` 拡張 - フロア境界チェック
- 対象部屋が現在フロアに存在しない場合、フロア移動トリガーを返す

### Step 55: 新アクションタイプ追加 `MOVE_FLOOR` - `ExplorationResult.action_type` に追加

### Step 56: `try_descend() -> ExplorationResult` - 探索システムからの降下試行
- `floor_manager.descend_stairs()` 呼び出し
- 結果を `ExplorationResult` に変換して返す

### Step 57: `try_ascend() -> ExplorationResult` - 探索システムからの上昇試行

### Step 58: `try_elevator(target_depth: int | None = None) -> ExplorationResult` - エレベーター試行

### Step 59: 現在フロア情報取得 `get_floor_info() -> dict`
- フロア名、深度、テーマ、ハザード、クリア状況を含む

### Step 60: UI連携用 `get_available_transitions() -> list[FloorTransitionType]`
- 現在利用可能な移動手段をリスト返却

---

## フェーズ 6: 永続化・セーブ/ロード (Steps 61-66)

### Step 61: `to_dict() -> dict` - 状態シリアライズ
```python
{
    "current_floor_id": str,
    "current_depth": int,
    "floors": {floor_id: floor.to_dict() for floor_id, floor in self.floors.items()},
    "transition_history": [record.to_dict() for record in self.transition_history],
    "scaling_config": asdict(self.scaling_config)
}
```

### Step 62: `DungeonFloor.to_dict() -> dict` 実装
- rooms: room_id のみ保存（詳細探索状態は別管理）

### Step 63: `FloorTransitionRecord.to_dict() -> dict` 実装

### Step 64: `from_dict(cls, data: dict) -> SkillEaterDungeonFloorManager` クラスメソッド
- フロア再構築、探索システムとの再連携

### Step 65: `save_to_file(filepath: str) -> None` - JSON保存
- `json.dump()` 使用

### Step 66: `load_from_file(filepath: str) -> SkillEaterDungeonFloorManager` クラスメソッド
- ファイル読み込み→`from_dict()`

---

## フェーズ 7: テスト・検証 (Steps 67-72)

### Step 67: 単体テスト `test_skill_eater_dungeon_floor_manager.py` 作成
- `DungeonFloor` 作成・シリアライズ
- `DepthScalingConfig` 計算検証
- テーマ判定ロジック

### Step 68: 移動テスト - 階段上下・エレベーター
- `descend_stairs()` / `ascend_stairs()` / `use_elevator()` 正常系
- 失敗系（ボス未クリア、深度制限等）

### Step 69: 深度スケーリングテスト
- 深度1, 10, 25, 50, 99 で敵ティア・トラップ密度・報酬倍率検証
- テーマ遷移境界（15/16, 30/31, 50/51）検証

### Step 70: 演出統合テスト
- 音声キュー・エモートキューに正しいファイルが入るか
- `PresentationEvent` の `duration_ms`, `vr_grid_effect` 検証

### Step 71: ExplorationSystem 統合テスト
- `try_descend()` 等から `ExplorationResult` 正常返却
- `current_room_id` 更新確認

### Step 72: E2Eシナリオテスト
- 新規ダンジョン初期化 → 深度1探索 → ボス撃破 → 階段降下 → 深度2探索 → エレベーターで深度5へ → 緊急脱出 → セーブ/ロード → 継続
- 全フェーズ通しでエラーなし・データ整合性確認

---

## 実装順序の推奨

| 週 | 実装ステップ | 成果物 |
|---|---|---|
| 1 | Steps 1-12 | データ構造・フロア生成基盤 |
| 2 | Steps 13-28 | フロア移動・遷移ロジック |
| 3 | Steps 29-40 | 深度スケーリング・ハザード |
| 4 | Steps 41-52 | 音響・エモート演出 |
| 5 | Steps 53-60 | ExplorationSystem統合 |
| 6 | Steps 61-66 | セーブ/ロード |
| 7 | Steps 67-72 | テスト・検証・バグ修正 |

---

## 依存関係マップ

```
skill_eater_dungeon_floor_manager.py (新規)
├── imports: DungeonRoom, ExplorationResult (from skill_eater_exploration_system)
├── imports: SkillEaterAudioSystem, SkillEaterPresentationSystem, PresentationEvent
├── imports: ProceduralDungeonGenerator, DungeonThemeRegistry, DungeonThemeData
├── uses: data/dungeon_themes.yaml (拡張済み)
├── integrates: SkillEaterExplorationSystem (双方向参照)
└── tests: test_skill_eater_dungeon_floor_manager.py (新規)
```

---

## 注意事項・制約

1. **既存コード破壊禁止**: `SkillEaterExplorationSystem` の公開APIは維持、内部で `floor_manager` を委譲
2. **音声ファイル未配備対応**: `play_sound()` はファイル不在でも `False` 返却のみで継続
3. **モックモード対応**: `is_mock_only=True` 時は全音声・演出スキップ
4. **パフォーマンス**: フロア生成は遅延評価（初回アクセス時）推奨
5. **互換性**: 既存 `BankDungeonManager` は Phase 3 専用として共存、新システムは汎用ダンジョン用

---

## 完了基準

- [ ] Steps 1-72 全実装完了
- [ ] `test_skill_eater_dungeon_floor_manager.py` 全テストパス
- [ ] 既存テスト (`test_skill_eater_presentation_integration.py`, `test_skill_eater_audio_integration.py`) リグレッションなし
- [ ] E2Eシナリオ（深度1→99→脱出→ロード）手動確認OK
- [ ] 音声・エモートファイル配置ガイドに従いアセット配置済み