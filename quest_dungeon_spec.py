"""
Quest Dungeon Spec Module (偏執的クエストシステム / 設計書 Phase 5 Step 18)
クエスト→ダンジョン要求仕様 DSL（部屋/トラップ/敵/ボス座標）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class RoomType(Enum):
    """部屋タイプ"""

    ENTRANCE = auto()  # 入口
    CORRIDOR = auto()  # 通路
    CHAMBER = auto()  # 広間
    TREASURE = auto()  # 宝物庫
    BOSS = auto()  # ボス部屋
    PUZZLE = auto()  # パズル部屋
    TRAP = auto()  # トラップ部屋
    SHOP = auto()  # 店
    REST = auto()  # 休憩所
    SECRET = auto()  # 秘密の部屋


class TrapType(Enum):
    """トラップタイプ"""

    SPIKE = auto()  # 棘
    POISON_GAS = auto()  # 毒ガス
    FLOOR_COLLAPSE = auto()  # 床崩落
    ARROW = auto()  # 矢
    CURSE = auto()  # 呪い
    TELEPORT = auto()  # 転移
    ALARM = auto()  # 警報


class EnemyRole(Enum):
    """敵の役割"""

    GUARD = auto()  # 門番
    PATROL = auto()  # 巡回
    AMBUSH = auto()  # 待ち伏せ
    BOSS = auto()  # ボス
    MINIBOSS = auto()  # 中ボス
    ELITE = auto()  # エリート


@dataclass
class RoomSpec:
    """部屋仕様"""

    room_id: str
    room_type: RoomType
    # 位置・サイズ（相対座標、生成時に絶対座標に変換）
    min_x: int = 0
    min_y: int = 0
    max_x: int = 10
    max_y: int = 10
    # 接続要求
    required_connections: list[str] = field(default_factory=list)  # 接続すべき部屋ID
    preferred_connections: list[str] = field(default_factory=list)  # 望ましい接続
    # 内容物
    traps: list[TrapSpec] = field(default_factory=list)
    enemies: list[EnemySpec] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)
    # 特殊フラグ
    is_required: bool = True  # 必ず生成される
    is_locked: bool = False  # 鍵が必要
    lock_key_id: str = ""  # 解錠キーID
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrapSpec:
    """トラップ仕様"""

    trap_id: str
    trap_type: TrapType
    position: tuple[int, int] = (0, 0)  # 部屋内相対座標
    damage: int = 10
    effect_duration: int = 0
    trigger_condition: str = "enter"  # enter|interact|timer|hp_below
    disarm_difficulty: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnemySpec:
    """敵仕様"""

    enemy_id: str
    monster_id: str  # monsters.yaml の ID
    role: EnemyRole = EnemyRole.GUARD
    position: tuple[int, int] = (0, 0)  # 部屋内相対座標
    level_modifier: int = 0
    equipment_overrides: dict[str, str] = field(default_factory=dict)
    ai_hints: list[str] = field(
        default_factory=list
    )  # "protect_boss", "guard_entrance" 等
    spawn_condition: str = "always"  # always|quest_stage|player_level|flag
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DungeonSpec:
    """ダンジョン仕様（クエストからの要求）"""

    spec_id: str
    name: str = ""
    description: str = ""
    # 全体設定
    min_floors: int = 1
    max_floors: int = 5
    width: int = 60
    height: int = 60
    theme_id: str = ""  # 使用するテーマ
    # フロアごとの要求
    floor_specs: list[FloorSpec] = field(default_factory=list)
    # 全体制約
    global_constraints: dict[str, Any] = field(default_factory=dict)
    # クエスト連携
    quest_id: str = ""
    objective_mapping: dict[str, str] = field(
        default_factory=dict
    )  # objective_id -> room_id/trap_id/enemy_id


@dataclass
class FloorSpec:
    """フロア仕様"""

    floor_number: int = 1
    min_rooms: int = 3
    max_rooms: int = 8
    required_rooms: list[RoomSpec] = field(default_factory=list)
    optional_rooms: list[RoomSpec] = field(default_factory=list)
    # ボスフロア指定
    is_boss_floor: bool = False
    boss_room_spec: RoomSpec | None = None
    # 接続制約
    entrance_from_above: bool = True
    exit_to_below: bool = True
    # テーマ上書き
    theme_override: str = ""


# DSL パーサー（簡易版：YAML/JSON から構築）
def build_dungeon_spec_from_yaml(data: dict[str, Any]) -> DungeonSpec:
    """YAML データから DungeonSpec を構築"""
    spec = DungeonSpec(
        spec_id=data.get("spec_id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        min_floors=data.get("min_floors", 1),
        max_floors=data.get("max_floors", 5),
        width=data.get("width", 60),
        height=data.get("height", 60),
        theme_id=data.get("theme_id", ""),
        quest_id=data.get("quest_id", ""),
        objective_mapping=data.get("objective_mapping", {}),
    )

    # グローバル制約
    spec.global_constraints = data.get("global_constraints", {})

    # フロア仕様
    for floor_data in data.get("floors", []):
        floor = FloorSpec(
            floor_number=floor_data.get("floor_number", 1),
            min_rooms=floor_data.get("min_rooms", 3),
            max_rooms=floor_data.get("max_rooms", 8),
            is_boss_floor=floor_data.get("is_boss_floor", False),
            entrance_from_above=floor_data.get("entrance_from_above", True),
            exit_to_below=floor_data.get("exit_to_below", True),
            theme_override=floor_data.get("theme_override", ""),
        )

        # 必須部屋
        for room_data in floor_data.get("required_rooms", []):
            room = _parse_room_spec(room_data)
            floor.required_rooms.append(room)

        # オプション部屋
        for room_data in floor_data.get("optional_rooms", []):
            room = _parse_room_spec(room_data)
            floor.optional_rooms.append(room)

        # ボス部屋
        if floor_data.get("boss_room"):
            floor.boss_room_spec = _parse_room_spec(floor_data["boss_room"])
            floor.is_boss_floor = True

        spec.floor_specs.append(floor)

    return spec


def _parse_room_spec(data: dict[str, Any]) -> RoomSpec:
    """部屋仕様パース"""
    room_type_str = data.get("room_type", "CHAMBER")
    room_type = (
        RoomType[room_type_str]
        if room_type_str in RoomType.__members__
        else RoomType.CHAMBER
    )

    room = RoomSpec(
        room_id=data.get("room_id", ""),
        room_type=room_type,
        min_x=data.get("min_x", 0),
        min_y=data.get("min_y", 0),
        max_x=data.get("max_x", 10),
        max_y=data.get("max_y", 10),
        required_connections=data.get("required_connections", []),
        preferred_connections=data.get("preferred_connections", []),
        is_required=data.get("is_required", True),
        is_locked=data.get("is_locked", False),
        lock_key_id=data.get("lock_key_id", ""),
        metadata=data.get("metadata", {}),
    )

    # トラップ
    for trap_data in data.get("traps", []):
        trap_type_str = trap_data.get("trap_type", "SPIKE")
        trap_type = (
            TrapType[trap_type_str]
            if trap_type_str in TrapType.__members__
            else TrapType.SPIKE
        )
        trap = TrapSpec(
            trap_id=trap_data.get("trap_id", ""),
            trap_type=trap_type,
            position=tuple(trap_data.get("position", [0, 0])),
            damage=trap_data.get("damage", 10),
            effect_duration=trap_data.get("effect_duration", 0),
            trigger_condition=trap_data.get("trigger_condition", "enter"),
            disarm_difficulty=trap_data.get("disarm_difficulty", 10),
            metadata=trap_data.get("metadata", {}),
        )
        room.traps.append(trap)

    # 敵
    for enemy_data in data.get("enemies", []):
        role_str = enemy_data.get("role", "GUARD")
        role = (
            EnemyRole[role_str]
            if role_str in EnemyRole.__members__
            else EnemyRole.GUARD
        )
        enemy = EnemySpec(
            enemy_id=enemy_data.get("enemy_id", ""),
            monster_id=enemy_data.get("monster_id", ""),
            role=role,
            position=tuple(enemy_data.get("position", [0, 0])),
            level_modifier=enemy_data.get("level_modifier", 0),
            equipment_overrides=enemy_data.get("equipment_overrides", {}),
            ai_hints=enemy_data.get("ai_hints", []),
            spawn_condition=enemy_data.get("spawn_condition", "always"),
            metadata=enemy_data.get("metadata", {}),
        )
        room.enemies.append(enemy)

    # アイテム
    room.items = data.get("items", [])

    return room


# 逆変換：生成結果からスペック充足度を検証
@dataclass
class DungeonVerificationResult:
    """ダンジョン生成結果の検証結果"""

    spec_id: str
    satisfied: bool
    missing_required_rooms: list[str] = field(default_factory=list)
    missing_required_traps: list[str] = field(default_factory=list)
    missing_required_enemies: list[str] = field(default_factory=list)
    boss_room_missing: bool = False
    floor_count_mismatch: bool = False
    details: dict[str, Any] = field(default_factory=dict)


def verify_dungeon_against_spec(
    generated: dict[str, Any],
    spec: DungeonSpec,
) -> DungeonVerificationResult:
    """生成されたダンジョンがスペックを満たすか検証"""
    result = DungeonVerificationResult(spec_id=spec.spec_id, satisfied=True)

    # フロア数チェック
    generated_floors = generated.get("floors", [])
    if (
        len(generated_floors) < spec.min_floors
        or len(generated_floors) > spec.max_floors
    ):
        result.satisfied = False
        result.floor_count_mismatch = True
        result.details["floor_count"] = {
            "expected_min": spec.min_floors,
            "expected_max": spec.max_floors,
            "actual": len(generated_floors),
        }

    # 必須部屋チェック（簡易版）
    for floor_spec in spec.floor_specs:
        floor_idx = floor_spec.floor_number - 1
        if floor_idx >= len(generated_floors):
            continue
        gen_floor = generated_floors[floor_idx]
        gen_rooms = gen_floor.get("rooms", [])
        gen_room_ids = {r.get("room_id", "") for r in gen_rooms}

        for req_room in floor_spec.required_rooms:
            if req_room.room_id not in gen_room_ids:
                result.satisfied = False
                result.missing_required_rooms.append(req_room.room_id)

        # ボス部屋チェック
        if floor_spec.is_boss_floor and floor_spec.boss_room_spec:
            boss_id = floor_spec.boss_room_spec.room_id
            if boss_id not in gen_room_ids:
                result.satisfied = False
                result.boss_room_missing = True

    return result


__all__ = [
    "RoomType",
    "TrapType",
    "EnemyRole",
    "RoomSpec",
    "TrapSpec",
    "EnemySpec",
    "DungeonSpec",
    "FloorSpec",
    "DungeonVerificationResult",
    "build_dungeon_spec_from_yaml",
    "verify_dungeon_against_spec",
]
