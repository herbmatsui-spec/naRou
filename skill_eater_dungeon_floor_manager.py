"""
skill_eater_dungeon_floor_manager.py
Aの世界（スキル喰い） 多層ダンジョン・フロア移動システム
Phase 3: 多層要塞ダンジョン探索とフロア遷移管理
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from procedural_dungeon_generator import (
        ProceduralDungeonGenerator,
    )
    from skill_eater_audio_system import SkillEaterAudioSystem
    from skill_eater_exploration_system import DungeonRoom
    from skill_eater_presentation_system import SkillEaterPresentationSystem


class DungeonTheme(Enum):
    """ダンジョンテーマ（Step 2）"""
    INDUSTRIAL_RUINS = "industrial_ruins"
    NEON_SEWERS = "neon_sewers"
    MIDAS_LABS = "midas_labs"
    BABEL_CORE = "babel_core"

    @classmethod
    def from_depth(cls, depth: int) -> DungeonTheme:
        if depth <= 15:
            return cls.INDUSTRIAL_RUINS
        elif depth <= 30:
            return cls.NEON_SEWERS
        elif depth <= 50:
            return cls.MIDAS_LABS
        else:
            return cls.BABEL_CORE


class FloorTransitionType(Enum):
    """フロア遷移タイプ（Step 3）"""
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"
    ELEVATOR = "elevator"
    EMERGENCY_SHAFT = "emergency_shaft"


@dataclass
class DepthScalingConfig:
    """深度スケーリング設定（Step 4）"""
    base_enemy_tier: int = 1
    enemy_tier_per_depth: float = 0.1
    base_trap_density: float = 0.1
    trap_density_per_depth: float = 0.02
    base_reward_multiplier: float = 1.0
    reward_multiplier_per_depth: float = 0.05
    boss_spawn_depth_interval: int = 10


@dataclass
class DungeonFloor:
    """ダンジョンフロア（Step 1）"""
    floor_id: str
    depth: int
    theme: DungeonTheme
    rooms: list[DungeonRoom] = field(default_factory=list)
    boss_room: DungeonRoom | None = None
    exit_to_next: dict[str, Any] | None = None
    hazard_level: int = 0
    cleared: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor_id": self.floor_id,
            "depth": self.depth,
            "theme": self.theme.value,
            "rooms": [r.room_id for r in self.rooms],
            "boss_room": self.boss_room.room_id if self.boss_room else None,
            "exit_to_next": self.exit_to_next,
            "hazard_level": self.hazard_level,
            "cleared": self.cleared,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], room_lookup: dict[str, DungeonRoom]) -> DungeonFloor:
        return cls(
            floor_id=data["floor_id"],
            depth=data["depth"],
            theme=DungeonTheme(data["theme"]),
            rooms=[room_lookup[rid] for rid in data["rooms"]],
            boss_room=room_lookup.get(data["boss_room"]) if data.get("boss_room") else None,
            exit_to_next=data.get("exit_to_next"),
            hazard_level=data.get("hazard_level", 0),
            cleared=data.get("cleared", False),
        )


@dataclass
class FloorTransitionResult:
    """フロア遷移結果"""
    success: bool
    message: str
    previous_floor_id: str
    new_floor_id: str | None
    transition_type: FloorTransitionType
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[Any] = field(default_factory=list)
    hazard_change: int = 0


@dataclass
class FloorClearResult:
    """フロアクリア結果"""
    success: bool
    cleared_floor: str
    next_floor: str | None
    rewards: list[str] = field(default_factory=list)
    hazard_purge_amount: int = 0
    concept_shards: int = 0


@dataclass
class FloorTransitionRecord:
    """フロア遷移履歴"""
    timestamp: float
    from_floor: str
    to_floor: str
    transition_type: FloorTransitionType
    hazard_before: int
    hazard_after: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["transition_type"] = self.transition_type.value
        return data


class SkillEaterDungeonFloorManager:
    """多層ダンジョン・フロア移動管理（Step 7）"""

    _instance: SkillEaterDungeonFloorManager | None = None

    def __init__(
        self,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
        dungeon_generator: ProceduralDungeonGenerator | None = None,
    ):
        from procedural_dungeon_generator import DungeonThemeRegistry, ProceduralDungeonGenerator
        from skill_eater_audio_system import SkillEaterAudioSystem
        from skill_eater_presentation_system import SkillEaterPresentationSystem

        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.generator = dungeon_generator or ProceduralDungeonGenerator()
        self.theme_registry = DungeonThemeRegistry()
        self.floors: dict[str, DungeonFloor] = {}
        self.current_floor_id: str | None = None
        self.current_depth: int = 0
        self.scaling_config = DepthScalingConfig()
        self.transition_history: list[FloorTransitionRecord] = []
        self._room_lookup: dict[str, DungeonRoom] = {}

    @classmethod
    def get_instance(cls) -> SkillEaterDungeonFloorManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def _generate_floor(self, floor_id: str, depth: int, theme: DungeonTheme) -> DungeonFloor:
        """フロア生成（Step 9）"""
        from skill_eater_exploration_system import DungeonRoom

        num_rooms = min(12, max(3, 3 + depth // 5))
        rooms = []

        for i in range(num_rooms):
            room = DungeonRoom(
                room_id=f"{floor_id}_room_{i}",
                name=f"{theme.value.replace('_', ' ').title()} - 部屋 {i+1}",
                description=f"深度 {depth} の {theme.value} エリア。",
                has_treasure=(i == num_rooms - 1 and depth % 5 == 0),
                has_trap=(random.random() < self._calculate_trap_density(depth)),
                enemies=[],
            )
            rooms.append(room)
            self._room_lookup[room.room_id] = room

        boss_room = None
        if depth % self.scaling_config.boss_spawn_depth_interval == 0:
            boss_room = DungeonRoom(
                room_id=f"{floor_id}_boss",
                name=f"{theme.value.replace('_', ' ').title()} - ボスの間",
                description="強大な気配が漂う部屋。",
                has_treasure=True,
                has_trap=True,
                enemies=[],
            )
            rooms.append(boss_room)
            self._room_lookup[boss_room.room_id] = boss_room

        exit_type = "elevator" if random.random() < 0.3 else "stairs"
        exit_to_next = {
            "type": exit_type,
            "position": (random.randint(0, 10), random.randint(0, 10)),
            "target_floor": f"floor_{depth + 1}",
        } if depth < 99 else None

        return DungeonFloor(
            floor_id=floor_id,
            depth=depth,
            theme=theme,
            rooms=rooms,
            boss_room=boss_room,
            exit_to_next=exit_to_next,
            hazard_level=0,
            cleared=False,
        )

    def _calculate_trap_density(self, depth: int) -> float:
        return min(0.8, self.scaling_config.base_trap_density + depth * self.scaling_config.trap_density_per_depth)

    def initialize_dungeon(self, max_depth: int = 99) -> None:
        """ダンジョン全体初期化（Step 10）"""
        self.floors.clear()
        self._room_lookup.clear()

        for depth in range(1, max_depth + 1):
            theme = DungeonTheme.from_depth(depth)
            floor_id = f"floor_{depth}"
            floor = self._generate_floor(floor_id, depth, theme)
            self.floors[floor_id] = floor

        self.current_depth = 1
        self.current_floor_id = "floor_1"

        # Phase 1 Step 8: 初期フロアを訪問済みに記録
        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()
        exploration._visited_floors.add(1)
        exploration.exploration_rank.max_depth_reached = 1

    def get_current_floor(self) -> DungeonFloor | None:
        """現在フロア取得（Step 11）"""
        if self.current_floor_id:
            return self.floors.get(self.current_floor_id)
        return None

    def get_current_room(self) -> DungeonRoom | None:
        """現在部屋取得（Step 12）"""
        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()
        room_id = exploration.current_room_id
        return self._room_lookup.get(room_id)

    # Step 13: 降下可能判定
    def can_descend(self) -> bool:
        current_floor = self.get_current_floor()
        if not current_floor:
            return False
        if not current_floor.exit_to_next:
            return False
        if current_floor.boss_room and not current_floor.cleared:
            return False
        return True

    # Step 14: 上昇可能判定
    def can_ascend(self) -> bool:
        if self.current_depth <= 1:
            return False
        prev_floor_id = f"floor_{self.current_depth - 1}"
        prev_floor = self.floors.get(prev_floor_id)
        if not prev_floor or not prev_floor.exit_to_next:
            return False
        return True

    # Step 15: エレベーター使用可能判定
    def can_use_elevator(self) -> bool:
        current_floor = self.get_current_floor()
        if not current_floor or not current_floor.exit_to_next:
            return False
        return current_floor.exit_to_next.get("type") == "elevator"

    # Step 19: 共通遷移処理
    def _perform_transition(
        self,
        target_floor_id: str,
        transition_type: FloorTransitionType
    ) -> FloorTransitionResult:
        import time
        previous_floor_id = self.current_floor_id or ""
        previous_floor = self.floors.get(previous_floor_id)
        hazard_before = previous_floor.hazard_level if previous_floor else 0

        # 演出シーケンス構築
        if transition_type == FloorTransitionType.STAIRS_DOWN:
            sounds, events = self._build_stairs_down_sequence()
            hazard_change = 5
        elif transition_type == FloorTransitionType.STAIRS_UP:
            sounds, events = self._build_stairs_up_sequence()
            hazard_change = -10
        elif transition_type == FloorTransitionType.ELEVATOR:
            sounds, events = self._build_elevator_sequence("down" if self.current_depth < self.floors[target_floor_id].depth else "up")
            hazard_change = 0
        elif transition_type == FloorTransitionType.EMERGENCY_SHAFT:
            sounds, events = self._build_emergency_escape_sequence()
            hazard_change = -100
        else:
            sounds, events = [], []

        # 音声再生
        for sound in sounds:
            self.audio.play_sound(sound)

        # 演出イベントキューへ追加
        for event in events:
            self.presentation.event_queue.append(event)

        # フロア遷移実行
        self.current_floor_id = target_floor_id
        self.current_depth = self.floors[target_floor_id].depth
        new_floor = self.floors[target_floor_id]

        # 入口部屋を現在部屋に設定
        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()
        if new_floor.rooms:
            exploration.current_room_id = new_floor.rooms[0].room_id

        # Phase 1 Step 8: 初見フロアボーナス
        if exploration._is_first_floor(self.current_depth):
            exploration._visited_floors.add(self.current_depth)
            exploration.exploration_rank.max_depth_reached = max(
                exploration.exploration_rank.max_depth_reached, self.current_depth
            )
            # 初見フロアボーナス経験値
            floor_bonus_exp = self.current_depth * 100 + 1000
            gained_exp, ranked_up = exploration.add_exploration_exp(floor_bonus_exp)
            if ranked_up:
                exploration._play_rank_up_fanfare(exploration.exploration_rank.rank)
            # フロア到達メッセージ追加
            events.append(exploration.presentation.add_event(
                emote_file="emote_exclamation.png",
                audio_file="floor_transition_woosh.ogg",
                message=f"初見フロア到達！ 探索経験値 +{floor_bonus_exp}",
            ))

        # ハザード更新
        new_floor.hazard_level = max(0, min(100, new_floor.hazard_level + hazard_change))
        hazard_after = new_floor.hazard_level

        # 履歴記録
        record = FloorTransitionRecord(
            timestamp=time.time(),
            from_floor=previous_floor_id,
            to_floor=target_floor_id,
            transition_type=transition_type,
            hazard_before=hazard_before,
            hazard_after=hazard_after,
        )
        self.transition_history.append(record)

        direction_msg = "降りた" if transition_type in (FloorTransitionType.STAIRS_DOWN, FloorTransitionType.ELEVATOR) else "登った"
        return FloorTransitionResult(
            success=True,
            message=f"フロア {self.current_depth} へ{direction_msg}。",
            previous_floor_id=previous_floor_id,
            new_floor_id=target_floor_id,
            transition_type=transition_type,
            played_sounds=sounds,
            presentation_events=events,
            hazard_change=hazard_change,
        )

    # Step 20: 階段降下用演出シーケンス
    def _build_stairs_down_sequence(self) -> tuple[list[str], list[Any]]:
        from skill_eater_presentation_system import PresentationEvent
        sounds = ["stair_creak.ogg"] * 3 + ["floor_transition_woosh.ogg"]
        events = [
            PresentationEvent(
                emote_file="emote_arrow_down.png",
                audio_file="stair_creak.ogg",
                message="階段を降りる...",
                duration_ms=800,
            )
        ]
        return sounds, events

    # Step 21: 階段上昇用演出シーケンス
    def _build_stairs_up_sequence(self) -> tuple[list[str], list[Any]]:
        from skill_eater_presentation_system import PresentationEvent
        sounds = ["stair_creak.ogg"] * 3 + ["floor_transition_woosh.ogg"]
        events = [
            PresentationEvent(
                emote_file="emote_arrow_up.png",
                audio_file="stair_creak.ogg",
                message="階段を登る...",
                duration_ms=800,
            )
        ]
        return sounds, events

    # Step 22: エレベーター用演出シーケンス
    def _build_elevator_sequence(self, direction: str) -> tuple[list[str], list[Any]]:
        from skill_eater_presentation_system import PresentationEvent
        emote = "emote_arrow_down.png" if direction == "down" else "emote_arrow_up.png"
        msg = "エレベーターで下降中..." if direction == "down" else "エレベーターで上昇中..."
        sounds = ["elevator_hum.ogg", "floor_transition_woosh.ogg"]
        events = [
            PresentationEvent(
                emote_file=emote,
                audio_file="elevator_hum.ogg",
                message=msg,
                duration_ms=2000,
                vr_grid_effect=True,
            )
        ]
        return sounds, events

    # Step 23: 移動失敗時の演出
    def _build_failed_transition_sequence(self, reason: str) -> tuple[list[str], list[Any]]:
        from skill_eater_presentation_system import PresentationEvent
        sounds = ["buzzer.ogg"]
        events = [
            PresentationEvent(
                emote_file="emote_alert.png",
                audio_file="buzzer.ogg",
                message=reason,
                duration_ms=1000,
            )
        ]
        return sounds, events

    # Step 24: 緊急脱出用演出シーケンス
    def _build_emergency_escape_sequence(self) -> tuple[list[str], list[Any]]:
        from skill_eater_presentation_system import PresentationEvent
        sounds = ["warp.ogg", "floor_transition_woosh.ogg"]
        events = [
            PresentationEvent(
                emote_file="emote_exclamation.png",
                audio_file="warp.ogg",
                message="緊急脱出！地上へワープ！",
                duration_ms=1500,
                vr_grid_effect=True,
            )
        ]
        return sounds, events

    # Step 16: 階段降下
    def descend_stairs(self) -> FloorTransitionResult:
        if not self.can_descend():
            sounds, events = self._build_failed_transition_sequence("降下できません。ボスを倒すか、出口がありません。")
            for sound in sounds:
                self.audio.play_sound(sound)
            for event in events:
                self.presentation.event_queue.append(event)
            return FloorTransitionResult(
                success=False,
                message="降下できません。ボスを倒すか、出口がありません。",
                previous_floor_id=self.current_floor_id or "",
                new_floor_id=None,
                transition_type=FloorTransitionType.STAIRS_DOWN,
                played_sounds=sounds,
                presentation_events=events,
            )

        current_floor = self.get_current_floor()
        target_floor_id = current_floor.exit_to_next.get("target_floor", f"floor_{self.current_depth + 1}")

        # 次フロアが存在しない場合は生成
        self._ensure_next_floor_exists()

        return self._perform_transition(target_floor_id, FloorTransitionType.STAIRS_DOWN)

    # Step 17: 階段上昇
    def ascend_stairs(self) -> FloorTransitionResult:
        if not self.can_ascend():
            sounds, events = self._build_failed_transition_sequence("上昇できません。前のフロアに出口がありません。")
            for sound in sounds:
                self.audio.play_sound(sound)
            for event in events:
                self.presentation.event_queue.append(event)
            return FloorTransitionResult(
                success=False,
                message="上昇できません。前のフロアに出口がありません。",
                previous_floor_id=self.current_floor_id or "",
                new_floor_id=None,
                transition_type=FloorTransitionType.STAIRS_UP,
                played_sounds=sounds,
                presentation_events=events,
            )

        target_floor_id = f"floor_{self.current_depth - 1}"
        return self._perform_transition(target_floor_id, FloorTransitionType.STAIRS_UP)

    # Step 18: エレベーター移動
    def use_elevator(self, target_depth: int | None = None) -> FloorTransitionResult:
        if not self.can_use_elevator():
            sounds, events = self._build_failed_transition_sequence("エレベーターが使用できません。")
            for sound in sounds:
                self.audio.play_sound(sound)
            for event in events:
                self.presentation.event_queue.append(event)
            return FloorTransitionResult(
                success=False,
                message="エレベーターが使用できません。",
                previous_floor_id=self.current_floor_id or "",
                new_floor_id=None,
                transition_type=FloorTransitionType.ELEVATOR,
                played_sounds=sounds,
                presentation_events=events,
            )

        if target_depth is None:
            target_depth = self.current_depth + 1
        target_depth = max(1, min(99, target_depth))
        target_floor_id = f"floor_{target_depth}"

        self._ensure_next_floor_exists()
        direction = "down" if target_depth > self.current_depth else "up"
        return self._perform_transition(target_floor_id, FloorTransitionType.ELEVATOR)

    # Step 24: 緊急脱出
    def emergency_escape(self) -> FloorTransitionResult:
        previous_floor_id = self.current_floor_id or ""
        sounds, events = self._build_emergency_escape_sequence()
        for sound in sounds:
            self.audio.play_sound(sound)
        for event in events:
            self.presentation.event_queue.append(event)

        self.current_floor_id = "floor_1"
        self.current_depth = 1
        floor_1 = self.floors.get("floor_1")
        if floor_1:
            floor_1.hazard_level = 0
            from skill_eater_exploration_system import SkillEaterExplorationSystem
            exploration = SkillEaterExplorationSystem.get_instance()
            if floor_1.rooms:
                exploration.current_room_id = floor_1.rooms[0].room_id

        import time
        record = FloorTransitionRecord(
            timestamp=time.time(),
            from_floor=previous_floor_id,
            to_floor="floor_1",
            transition_type=FloorTransitionType.EMERGENCY_SHAFT,
            hazard_before=self.floors.get(previous_floor_id, DungeonFloor("", 0, DungeonTheme.INDUSTRIAL_RUINS)).hazard_level,
            hazard_after=0,
        )
        self.transition_history.append(record)

        return FloorTransitionResult(
            success=True,
            message="緊急脱出完了。地上（フロア1）へ戻りました。",
            previous_floor_id=previous_floor_id,
            new_floor_id="floor_1",
            transition_type=FloorTransitionType.EMERGENCY_SHAFT,
            played_sounds=sounds,
            presentation_events=events,
            hazard_change=-100,
        )

    # Step 25: フロアクリア判定
    def check_floor_clear(self) -> bool:
        current_floor = self.get_current_floor()
        if not current_floor:
            return False
        if current_floor.boss_room and not current_floor.cleared:
            return False
        return True

    # Step 26: フロアクリア処理
    def clear_current_floor(self) -> FloorClearResult:
        current_floor = self.get_current_floor()
        if not current_floor:
            return FloorClearResult(
                success=False,
                cleared_floor="",
                next_floor=None,
            )

        current_floor.cleared = True
        current_floor.hazard_level = max(0, current_floor.hazard_level - 50)

        next_floor = None
        if self.current_depth < 99:
            next_floor_id = f"floor_{self.current_depth + 1}"
            next_floor = next_floor_id

        # 報酬計算
        reward_multiplier = self.calculate_reward_multiplier(self.current_depth)
        base_shards = 10
        concept_shards = int(base_shards * reward_multiplier)
        rewards = [f"concept_shard_{concept_shards}", f"floor_clear_token_{self.current_depth}"]

        # Phase 1 Step 10: フロアクリア時ボーナス
        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()
        exploration.exploration_rank.floors_cleared += 1
        floor_clear_exp = self.current_depth * 200 + exploration.exploration_rank.floors_cleared * 100
        gained_exp, ranked_up = exploration.add_exploration_exp(floor_clear_exp)
        if ranked_up:
            exploration._play_rank_up_fanfare(exploration.exploration_rank.rank)
        # クリア演出追加
        exploration.presentation.add_event(
            emote_file="emote_star.png",
            audio_file="victory.ogg",
            message=f"フロアクリア！ 探索経験値 +{floor_clear_exp}",
        )

        return FloorClearResult(
            success=True,
            cleared_floor=current_floor.floor_id,
            next_floor=next_floor,
            rewards=rewards,
            hazard_purge_amount=50,
            concept_shards=concept_shards,
        )

    # Step 27: 次フロア自動生成
    def _ensure_next_floor_exists(self) -> str:
        next_depth = self.current_depth + 1
        next_floor_id = f"floor_{next_depth}"
        if next_floor_id not in self.floors and next_depth <= 99:
            theme = DungeonTheme.from_depth(next_depth)
            floor = self._generate_floor(next_floor_id, next_depth, theme)
            self.floors[next_floor_id] = floor
        return next_floor_id

    # Step 29: 敵ティア計算
    def calculate_enemy_tier(self, depth: int) -> int:
        return self.scaling_config.base_enemy_tier + int(depth * self.scaling_config.enemy_tier_per_depth)

    # Step 30: トラップ密度計算
    def calculate_trap_density(self, depth: int) -> float:
        return min(0.8, self.scaling_config.base_trap_density + depth * self.scaling_config.trap_density_per_depth)

    # Step 31: 報酬倍率計算
    def calculate_reward_multiplier(self, depth: int) -> float:
        return min(3.0, self.scaling_config.base_reward_multiplier + depth * self.scaling_config.reward_multiplier_per_depth)

    # Step 32: テーマ別敵プール選択
    def get_enemy_pool_for_depth(self, depth: int) -> dict:
        theme = DungeonTheme.from_depth(depth)
        theme_data = self.theme_registry.get(theme.value)
        if theme_data:
            return theme_data.enemy_pools
        return {"common": [], "elite": []}

    # Step 33: テーマ別ハザード選択
    def get_hazards_for_depth(self, depth: int) -> list[str]:
        theme = DungeonTheme.from_depth(depth)
        theme_data = self.theme_registry.get(theme.value)
        if theme_data:
            hazards = theme_data.environmental_hazards
            density = self.calculate_trap_density(depth)
            num_hazards = max(1, int(len(hazards) * density))
            return random.sample(hazards, min(num_hazards, len(hazards)))
        return []

    # Step 34: テーマ別特殊部屋選択
    def get_special_rooms_for_depth(self, depth: int) -> list[str]:
        theme = DungeonTheme.from_depth(depth)
        theme_data = self.theme_registry.get(theme.value)
        if theme_data:
            return theme_data.special_rooms
        return []

    # Step 35: ボス生成判定
    def should_spawn_boss(self, depth: int) -> bool:
        return depth % self.scaling_config.boss_spawn_depth_interval == 0

    # Step 36: ボス敵選択
    def select_boss_for_depth(self, depth: int) -> str:
        theme = DungeonTheme.from_depth(depth)
        theme_data = self.theme_registry.get(theme.value)
        if theme_data and theme_data.enemy_pools:
            elite = theme_data.enemy_pools.get("elite", [])
            if elite:
                return random.choice(elite)
        return "unknown_boss"

    # Step 37: フロア生成時のスケーリング適用
    def _apply_depth_scaling(self, floor: DungeonFloor) -> None:
        tier = self.calculate_enemy_tier(floor.depth)
        trap_density = self.calculate_trap_density(floor.depth)
        reward_mult = self.calculate_reward_multiplier(floor.depth)

        for room in floor.rooms:
            room.has_trap = random.random() < trap_density
            # 敵ティアに基づいて敵を設定（実際の敵データは別途管理）
            room.enemies = [f"tier_{tier}_enemy_{i}" for i in range(random.randint(1, 3))]

        if floor.boss_room:
            floor.boss_room.enemies = [self.select_boss_for_depth(floor.depth)]

    # Step 38: ハザードレベル更新
    def update_hazard_level(self, delta: int) -> int:
        current_floor = self.get_current_floor()
        if not current_floor:
            return 0
        current_floor.hazard_level = max(0, min(100, current_floor.hazard_level + delta))
        return current_floor.hazard_level

    # Step 39: ハザードデバフ取得
    def get_hazard_debuffs(self) -> list[str]:
        current_floor = self.get_current_floor()
        if not current_floor:
            return []
        debuffs = []
        level = current_floor.hazard_level
        if level >= 30:
            debuffs.append("Concept Leaking: MP Cost +20%")
        if level >= 60:
            debuffs.append("Gravity Distortion: Turn Time -30%")
        if level >= 90:
            debuffs.append("Total Reality Breakdown: Continuous HP Erosion")
        return debuffs

    # Step 40: マップ構造変化トリガー
    def check_map_mutation(self) -> str | None:
        current_floor = self.get_current_floor()
        if not current_floor:
            return None
        if current_floor.hazard_level >= 50 and current_floor.exit_to_next:
            current_floor.exit_to_next = None
            return "ALERT: Spatial collapse blocked the exit to next floor!"
        return None

    # Step 43: テーマ別遷移音声上書き機能
    def _get_transition_sounds(self, theme: DungeonTheme, transition_type: FloorTransitionType) -> dict[str, str]:
        theme_data = self.theme_registry.get(theme.value)
        if theme_data and theme_data.transition_sounds:
            return {
                "loop": theme_data.transition_sounds.get("elevator", "elevator_hum.ogg"),
                "step": theme_data.transition_sounds.get("stairs", "stair_creak.ogg"),
                "woosh": "floor_transition_woosh.ogg",
            }
        return {
            "loop": "elevator_hum.ogg",
            "step": "stair_creak.ogg",
            "woosh": "floor_transition_woosh.ogg",
        }

    # Step 44: 遷移時のテーマ別エモート選択
    def _get_transition_emotes(self, theme: DungeonTheme, direction: str) -> str:
        theme_data = self.theme_registry.get(theme.value)
        if theme_data and theme_data.transition_emotes:
            return theme_data.transition_emotes.get(direction, f"emote_arrow_{direction}.png")
        return f"emote_arrow_{direction}.png"

    # Step 46: 演出システムへの登録ヘルパー
    def _queue_transition_presentation(self, sounds: list[str], emote: str, message: str, duration_ms: int = 1000, vr_grid: bool = False) -> None:
        from skill_eater_presentation_system import PresentationEvent
        for sound in sounds:
            self.audio.play_sound(sound)
        event = PresentationEvent(
            emote_file=emote,
            audio_file=sounds[0] if sounds else None,
            message=message,
            duration_ms=duration_ms,
            vr_grid_effect=vr_grid,
        )
        self.presentation.event_queue.append(event)

    # Step 47: 遷移中の「移動中」表示用イベント
    def _create_traveling_event(self, duration_ms: int) -> Any:
        from skill_eater_presentation_system import PresentationEvent
        return PresentationEvent(
            emote_file=None,
            audio_file=None,
            message="次のフロアへ移動中...",
            duration_ms=duration_ms,
            vr_grid_effect=True,
        )

    # Step 48: 到着時の部屋進入演出
    def _create_room_entry_event(self, room: DungeonRoom) -> Any:
        from skill_eater_presentation_system import PresentationEvent
        current_floor = self.get_current_floor()
        theme = current_floor.theme if current_floor else DungeonTheme.INDUSTRIAL_RUINS
        emote = "emote_exclamation.png" if room == current_floor.boss_room else "emote_dots2.png"
        return PresentationEvent(
            emote_file=emote,
            audio_file="doorOpen_1.ogg",
            message=f"{room.name} に到達",
            duration_ms=1000,
        )

    # Step 49: ボス部屋前演出
    def _create_boss_approach_event(self) -> list[Any]:
        from skill_eater_presentation_system import PresentationEvent
        events = [
            PresentationEvent(
                emote_file="emote_alert.png",
                audio_file="warning.ogg",
                message="強大な気配を感じる...",
                duration_ms=1500,
            ),
            PresentationEvent(
                emote_file="emote_alert.png",
                audio_file="warning.ogg",
                message="ボス部屋が近い！",
                duration_ms=1000,
            ),
            PresentationEvent(
                emote_file="emote_exclamation.png",
                audio_file="alarm.ogg",
                message="覚悟しろ！",
                duration_ms=1000,
            ),
        ]
        for event in events:
            self.presentation.event_queue.append(event)
            if event.audio_file:
                self.audio.play_sound(event.audio_file)
        return events

    # Step 50: フロアクリア演出
    def _create_floor_clear_event(self, floor: DungeonFloor) -> list[Any]:
        from skill_eater_presentation_system import PresentationEvent
        events = [
            PresentationEvent(
                emote_file="emote_star.png",
                audio_file="victory.ogg",
                message=f"{floor.floor_id} クリア！",
                duration_ms=2000,
            ),
            PresentationEvent(
                emote_file="emote_heart.png",
                audio_file="fanfare.ogg",
                message="次の階層へ進めます。",
                duration_ms=1500,
            ),
        ]
        for event in events:
            self.presentation.event_queue.append(event)
            if event.audio_file:
                self.audio.play_sound(event.audio_file)
        return events

    # Step 51: ハザード上昇時演出
    def _create_hazard_rise_event(self, level: int) -> Any:
        from skill_eater_presentation_system import PresentationEvent
        event = PresentationEvent(
            emote_file="emote_alert.png",
            audio_file="heartbeat.ogg",
            message=f"概念侵食レベル {level}% - 現実が歪み始めた...",
            duration_ms=2000,
        )
        self.presentation.event_queue.append(event)
        if event.audio_file:
            self.audio.play_sound(event.audio_file)
        return event

    # Step 52: 音声・エモート欠損時のフォールバック（既存システムの仕様で自動対応）
    # SkillEaterAudioSystem.play_sound() はファイル不在でも False 返却のみで継続
    # is_mock_only=True モードでは全音声・演出スキップ

    # Step 53: ExplorationSystem 連携用メソッド
    def try_descend(self) -> Any:
        """探索システムからの降下試行（Step 56）"""
        from skill_eater_exploration_system import ExplorationResult
        result = self.descend_stairs()
        return ExplorationResult(
            action_type="MOVE_FLOOR" if result.success else "MOVE_ROOM",
            message=result.message,
            current_room_id=self.get_current_room().room_id if self.get_current_room() else "",
            played_sounds=result.played_sounds,
            presentation_events=result.presentation_events,
        )

    def try_ascend(self) -> Any:
        """探索システムからの上昇試行（Step 57）"""
        from skill_eater_exploration_system import ExplorationResult
        result = self.ascend_stairs()
        return ExplorationResult(
            action_type="MOVE_FLOOR" if result.success else "MOVE_ROOM",
            message=result.message,
            current_room_id=self.get_current_room().room_id if self.get_current_room() else "",
            played_sounds=result.played_sounds,
            presentation_events=result.presentation_events,
        )

    def try_elevator(self, target_depth: int | None = None) -> Any:
        """探索システムからのエレベーター試行（Step 58）"""
        from skill_eater_exploration_system import ExplorationResult
        result = self.use_elevator(target_depth)
        return ExplorationResult(
            action_type="MOVE_FLOOR" if result.success else "MOVE_ROOM",
            message=result.message,
            current_room_id=self.get_current_room().room_id if self.get_current_room() else "",
            played_sounds=result.played_sounds,
            presentation_events=result.presentation_events,
        )

    # Step 59: 現在フロア情報取得
    def get_floor_info(self) -> dict:
        current_floor = self.get_current_floor()
        if not current_floor:
            return {}
        return {
            "floor_id": current_floor.floor_id,
            "depth": current_floor.depth,
            "theme": current_floor.theme.value,
            "theme_name": current_floor.theme.value.replace('_', ' ').title(),
            "hazard_level": current_floor.hazard_level,
            "hazard_debuffs": self.get_hazard_debuffs(),
            "cleared": current_floor.cleared,
            "has_boss": current_floor.boss_room is not None,
            "boss_defeated": current_floor.cleared,
            "rooms_count": len(current_floor.rooms),
            "exit_type": current_floor.exit_to_next.get("type") if current_floor.exit_to_next else None,
        }

    # Step 60: UI連携用利用可能移動手段取得
    def get_available_transitions(self) -> list[FloorTransitionType]:
        available = []
        if self.can_descend():
            available.append(FloorTransitionType.STAIRS_DOWN)
        if self.can_ascend():
            available.append(FloorTransitionType.STAIRS_UP)
        if self.can_use_elevator():
            available.append(FloorTransitionType.ELEVATOR)
        available.append(FloorTransitionType.EMERGENCY_SHAFT)
        return available

    # Step 61: 状態シリアライズ
    def to_dict(self) -> dict[str, Any]:
        return {
            "current_floor_id": self.current_floor_id,
            "current_depth": self.current_depth,
            "floors": {fid: floor.to_dict() for fid, floor in self.floors.items()},
            "transition_history": [record.to_dict() for record in self.transition_history],
            "scaling_config": {
                "base_enemy_tier": self.scaling_config.base_enemy_tier,
                "enemy_tier_per_depth": self.scaling_config.enemy_tier_per_depth,
                "base_trap_density": self.scaling_config.base_trap_density,
                "trap_density_per_depth": self.scaling_config.trap_density_per_depth,
                "base_reward_multiplier": self.scaling_config.base_reward_multiplier,
                "reward_multiplier_per_depth": self.scaling_config.reward_multiplier_per_depth,
                "boss_spawn_depth_interval": self.scaling_config.boss_spawn_depth_interval,
            },
        }

    # Step 64: デシリアライズ
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillEaterDungeonFloorManager:
        manager = cls()
        manager.current_floor_id = data.get("current_floor_id")
        manager.current_depth = data.get("current_depth", 0)
        manager.transition_history = [
            FloorTransitionRecord(**record) for record in data.get("transition_history", [])
        ]

        scaling = data.get("scaling_config", {})
        manager.scaling_config = DepthScalingConfig(
            base_enemy_tier=scaling.get("base_enemy_tier", 1),
            enemy_tier_per_depth=scaling.get("enemy_tier_per_depth", 0.1),
            base_trap_density=scaling.get("base_trap_density", 0.1),
            trap_density_per_depth=scaling.get("trap_density_per_depth", 0.02),
            base_reward_multiplier=scaling.get("base_reward_multiplier", 1.0),
            reward_multiplier_per_depth=scaling.get("reward_multiplier_per_depth", 0.05),
            boss_spawn_depth_interval=scaling.get("boss_spawn_depth_interval", 10),
        )

        # フロアと部屋の再構築
        from skill_eater_exploration_system import DungeonRoom
        room_lookup = {}
        for fid, fdata in data.get("floors", {}).items():
            rooms = []
            for rid in fdata.get("rooms", []):
                room = DungeonRoom(
                    room_id=rid,
                    name=rid,
                    description="",
                )
                rooms.append(room)
                room_lookup[rid] = room

            boss_room = None
            if fdata.get("boss_room"):
                boss_room = room_lookup.get(fdata["boss_room"])

            floor = DungeonFloor.from_dict(fdata, room_lookup)
            manager.floors[fid] = floor

        manager._room_lookup = room_lookup
        return manager

    # Step 65: JSON保存
    def save_to_file(self, filepath: str) -> None:
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    # Step 66: JSON読み込み
    @classmethod
    def load_from_file(cls, filepath: str) -> SkillEaterDungeonFloorManager:
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
