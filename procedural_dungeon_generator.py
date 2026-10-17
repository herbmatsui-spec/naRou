"""
Procedural Dungeon Generator with Story Integration (Steps 54-59 + Phase 5 Step 19)
クエスト仕様充足モード対応: generate_from_spec(spec)
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from typing_extensions import Self

if TYPE_CHECKING:
    from ecs.entity import Entity

# Phase 5 Step 18: 仕様型のインポート
try:
    from quest_dungeon_spec import (
        DungeonSpec,
        DungeonVerificationResult,
        EnemyRole,
        EnemySpec,
        FloorSpec,
        RoomSpec,
        RoomType,
        TrapSpec,
        TrapType,
        verify_dungeon_against_spec,
    )

    _HAS_DUNGEON_SPEC = True
except ImportError:
    _HAS_DUNGEON_SPEC = False


# Step 55: DungeonThemeData
@dataclass
class DungeonThemeData:
    """ダンジョンテーマデータ (Step 55)"""

    theme_id: str
    name: str = ""
    base_layout: str = "cavern"
    difficulty_modifier: float = 1.0
    enemy_pools: dict[str, list[str]] = field(default_factory=dict)
    environmental_hazards: list[str] = field(default_factory=list)
    special_rooms: list[str] = field(default_factory=list)
    story_hooks: list[str] = field(default_factory=list)
    depth_range: list[int] = field(default_factory=list)
    transition_sounds: dict[str, str] = field(default_factory=dict)
    transition_emotes: dict[str, str] = field(default_factory=dict)


# Step 56, 57: DungeonThemeRegistry
class DungeonThemeRegistry:
    """ダンジョンテーマレジストリ (Step 56, 57)"""

    _instance: DungeonThemeRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._themes = {}
        return cls._instance

    def load(self, file_path: str = "data/dungeon_themes.yaml") -> None:
        """YAMLからダンジョンテーマを読み込む (Step 57)"""
        self._themes = {}
        if not os.path.exists(file_path):
            self._themes["goblin_cave"] = DungeonThemeData(
                theme_id="goblin_cave", name="ゴブリンの洞窟"
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        t_dict = raw.get("dungeon_themes", {})
        for tid, tdata in t_dict.items():
            self._themes[tid] = DungeonThemeData(
                theme_id=tid,
                name=tdata.get("name", tid),
                base_layout=tdata.get("base_layout", "cavern"),
                difficulty_modifier=float(tdata.get("difficulty_modifier", 1.0)),
                enemy_pools=tdata.get("enemy_pools", {}),
                environmental_hazards=tdata.get("environmental_hazards", []),
                special_rooms=tdata.get("special_rooms", []),
                story_hooks=tdata.get("story_hooks", []),
                depth_range=tdata.get("depth_range", []),
                transition_sounds=tdata.get("transition_sounds", {}),
                transition_emotes=tdata.get("transition_emotes", {}),
            )

    def get(self, theme_id: str) -> DungeonThemeData | None:
        return self._themes.get(theme_id)

    def all_themes(self) -> dict[str, DungeonThemeData]:
        return dict(self._themes)


REGISTRY = DungeonThemeRegistry()


# Step 58, 59: ProceduralDungeonGenerator
class ProceduralDungeonGenerator:
    """プロシージャルダンジョン生成器 (Steps 58, 59)"""

    def __init__(self, registry: DungeonThemeRegistry | None = None):
        self.registry = registry or REGISTRY

    def select_theme_by_story(self, player: Entity) -> DungeonThemeData:
        """ストーリー状態に基づくテーマ選択 (Step 59)"""
        if player and player.story_flags.get("goblin_invasion_active"):
            t = self.registry.get("goblin_cave")
            if t:
                return t

        # デフォルトフォールバック
        all_t = list(self.registry.all_themes().values())
        return all_t[0] if all_t else DungeonThemeData(theme_id="default", name="通常迷宮")

    def generate_dungeon(self, player: Entity, width: int = 40, height: int = 30) -> dict[str, Any]:
        """ダンジョン生成スタブ"""
        theme = self.select_theme_by_story(player)
        return {"theme": theme, "width": width, "height": height}

    # Phase 5 Step 19: 仕様充足モード生成
    def generate_from_spec(
        self,
        spec: DungeonSpec,
        player: Entity | None = None,
    ) -> dict[str, Any]:
        """仕様書に基づいてダンジョンを生成（充足モード）"""
        if not _HAS_DUNGEON_SPEC:
            raise RuntimeError("quest_dungeon_spec モジュールが必要です")

        # テーマ決定
        theme = None
        if spec.theme_id:
            theme = self.registry.get(spec.theme_id)
        if not theme:
            theme = DungeonThemeData(theme_id="default", name="通常迷宮")

        # フロア数決定（仕様に定義されたフロア数を上限にする）
        max_defined_floors = len(spec.floor_specs)
        num_floors = random.randint(spec.min_floors, min(spec.max_floors, max_defined_floors))

        floors = []
        for floor_idx in range(num_floors):
            floor_number = floor_idx + 1

            # 該当する FloorSpec を探す
            floor_spec = None
            for fs in spec.floor_specs:
                if fs.floor_number == floor_number:
                    floor_spec = fs
                    break

            if not floor_spec:
                # デフォルトフロア仕様
                floor_spec = FloorSpec(
                    floor_number=floor_number,
                    min_rooms=3,
                    max_rooms=6,
                )

            floor = self._generate_floor(floor_spec, theme, floor_number, spec)
            floors.append(floor)

        result = {
            "spec_id": spec.spec_id,
            "theme": theme,
            "width": spec.width,
            "height": spec.height,
            "floors": floors,
            "generated_floors": num_floors,
        }

        # 検証（デバッグ用）
        if _HAS_DUNGEON_SPEC:
            verification = verify_dungeon_against_spec(result, spec)
            result["verification"] = verification

        return result

    def _generate_floor(
        self,
        floor_spec: FloorSpec,
        theme: DungeonThemeData,
        floor_number: int,
        dungeon_spec: DungeonSpec,
    ) -> dict[str, Any]:
        """単一フロア生成"""
        # 部屋数決定
        num_rooms = random.randint(floor_spec.min_rooms, floor_spec.max_rooms)

        rooms = []
        room_id_counter = 0

        # 必須部屋を先に配置
        for req_room in floor_spec.required_rooms:
            room = self._build_room_from_spec(req_room, theme, floor_number)
            room["floor"] = floor_number
            rooms.append(room)
            room_id_counter += 1

        # オプション部屋から残りを埋める
        remaining_slots = num_rooms - len(floor_spec.required_rooms)
        optional_rooms = list(floor_spec.optional_rooms)
        random.shuffle(optional_rooms)

        for i in range(min(remaining_slots, len(optional_rooms))):
            opt_room = optional_rooms[i]
            room = self._build_room_from_spec(opt_room, theme, floor_number)
            room["floor"] = floor_number
            rooms.append(room)
            room_id_counter += 1

        # ボス部屋（ボスフロアの場合）
        if floor_spec.is_boss_floor and floor_spec.boss_room_spec:
            boss_room = self._build_room_from_spec(floor_spec.boss_room_spec, theme, floor_number)
            boss_room["floor"] = floor_number
            boss_room["is_boss_room"] = True
            rooms.append(boss_room)

        # 入口・出口の接続情報
        entrance_pos = (
            random.randint(0, dungeon_spec.width // 4),
            random.randint(0, dungeon_spec.height // 4),
        )
        exit_pos = (
            random.randint(3 * dungeon_spec.width // 4, dungeon_spec.width),
            random.randint(3 * dungeon_spec.height // 4, dungeon_spec.height),
        )

        return {
            "floor_number": floor_number,
            "rooms": rooms,
            "entrance_pos": entrance_pos if floor_spec.entrance_from_above else None,
            "exit_pos": exit_pos if floor_spec.exit_to_below else None,
            "theme_override": floor_spec.theme_override,
        }

    def _build_room_from_spec(
        self,
        room_spec: RoomSpec,
        theme: DungeonThemeData,
        floor_number: int,
    ) -> dict[str, Any]:
        """RoomSpec から部屋データ構築"""
        # サイズ計算
        width = room_spec.max_x - room_spec.min_x
        height = room_spec.max_y - room_spec.min_y
        if width <= 0:
            width = random.randint(6, 12)
        if height <= 0:
            height = random.randint(6, 12)

        # 位置（ランダム配置、実際の実装ではより高度な配置アルゴリズムが必要）
        x = random.randint(5, 50)
        y = random.randint(5, 50)

        # トラップ配置
        traps = []
        for trap_spec in room_spec.traps:
            traps.append(
                {
                    "trap_id": trap_spec.trap_id,
                    "trap_type": trap_spec.trap_type.name,
                    "position": trap_spec.position,
                    "damage": trap_spec.damage,
                    "effect_duration": trap_spec.effect_duration,
                    "trigger_condition": trap_spec.trigger_condition,
                    "disarm_difficulty": trap_spec.disarm_difficulty,
                }
            )

        # 敵配置
        enemies = []
        for enemy_spec in room_spec.enemies:
            enemies.append(
                {
                    "enemy_id": enemy_spec.enemy_id,
                    "monster_id": enemy_spec.monster_id,
                    "role": enemy_spec.role.name,
                    "position": enemy_spec.position,
                    "level_modifier": enemy_spec.level_modifier,
                    "equipment_overrides": enemy_spec.equipment_overrides,
                    "ai_hints": enemy_spec.ai_hints,
                    "spawn_condition": enemy_spec.spawn_condition,
                }
            )

        return {
            "room_id": room_spec.room_id,
            "room_type": room_spec.room_type.name,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "required_connections": room_spec.required_connections,
            "preferred_connections": room_spec.preferred_connections,
            "traps": traps,
            "enemies": enemies,
            "items": room_spec.items,
            "is_required": room_spec.is_required,
            "is_locked": room_spec.is_locked,
            "lock_key_id": room_spec.lock_key_id,
            "metadata": room_spec.metadata,
        }

    # 既存メソッドとの互換性のためのラッパー
    def generate(self, *args, **kwargs) -> dict[str, Any]:
        """generate_dungeon のエイリアス"""
        return self.generate_dungeon(*args, **kwargs)
