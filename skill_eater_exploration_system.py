"""
skill_eater_exploration_system.py
Aの世界（スキル喰い） 探索・移動・環境音システム
提案7: ダンジョン探索・足音・扉・トラップのEmote & Audio演出 (Steps 49〜56)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import PresentationEvent, SkillEaterPresentationSystem
from skill_eater_system import CharacterState

if TYPE_CHECKING:
    from skill_eater_procedural_dungeon import SkillEaterProceduralDungeon


@dataclass
class DungeonRoom:
    room_id: str
    name: str
    description: str
    has_treasure: bool = False
    has_trap: bool = False
    enemies: list[CharacterState] = field(default_factory=list)


@dataclass
class ExplorationRank:
    """探索ランクデータ (Phase 1 Step 1)"""

    rank: int = 1
    total_exp: int = 0
    max_depth_reached: int = 0
    rooms_visited: int = 0
    first_visit_bonuses: int = 0
    secret_rooms_found: int = 0
    floors_cleared: int = 0

    EXP_PER_RANK: int = 1000

    @classmethod
    def calculate_rank_from_exp(cls, total_exp: int) -> int:
        return max(1, total_exp // cls.EXP_PER_RANK + 1)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "total_exp": self.total_exp,
            "max_depth_reached": self.max_depth_reached,
            "rooms_visited": self.rooms_visited,
            "first_visit_bonuses": self.first_visit_bonuses,
            "secret_rooms_found": self.secret_rooms_found,
            "floors_cleared": self.floors_cleared,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExplorationRank":
        return cls(
            rank=data.get("rank", 1),
            total_exp=data.get("total_exp", 0),
            max_depth_reached=data.get("max_depth_reached", 0),
            rooms_visited=data.get("rooms_visited", 0),
            first_visit_bonuses=data.get("first_visit_bonuses", 0),
            secret_rooms_found=data.get("secret_rooms_found", 0),
            floors_cleared=data.get("floors_cleared", 0),
        )


@dataclass
class ExplorationResult:
    action_type: str  # 'STEP', 'MOVE_ROOM', 'OPEN_DOOR', 'LOOT_CHEST', 'ESCAPE', 'TRAP'
    message: str
    current_room_id: str
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[PresentationEvent] = field(
        default_factory=list
    )  # Step 49: 演出リスト


class SkillEaterExplorationSystem:
    _instance: SkillEaterExplorationSystem | None = None

    def __init__(
        self,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.dungeon_rooms: dict[str, DungeonRoom] = {
            "slum_alley": DungeonRoom(
                "slum_alley",
                "スラムの裏路地",
                "薄暗く湿った路地。遠くでサイレンが鳴り響く。",
            ),
            "underground_market": DungeonRoom(
                "underground_market",
                "地下闇市場通り",
                "違法スキルの密売人たちが行き交う。",
            ),
            "midas_tower_entrance": DungeonRoom(
                "midas_tower_entrance",
                "ミダスタワー正面玄関",
                "巨大な黄金の扉がそびえ立つ。",
            ),
            "vault_chamber": DungeonRoom(
                "vault_chamber",
                "バベルの金庫室",
                "秘匿された至高のスキルが眠る金庫。",
                has_treasure=True,
            ),
        }
        self.current_room_id: str = "slum_alley"
        self._procedural_dungeon: SkillEaterProceduralDungeon | None = None
        self._use_procedural: bool = False

        # Phase 1 Step 2: 探索ランキング・初見判定用セット
        self.exploration_rank: ExplorationRank = ExplorationRank()
        self._visited_rooms: set[str] = set()
        self._visited_floors: set[int] = set()
        self._visited_secret_rooms: set[str] = set()

    @classmethod
    def get_instance(cls) -> SkillEaterExplorationSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def set_procedural_dungeon(self, dungeon: SkillEaterProceduralDungeon) -> None:
        self._procedural_dungeon = dungeon
        self._use_procedural = True

    def migrate_legacy_rooms(self) -> None:
        if not self._procedural_dungeon:
            return
        for room_id, room in self.dungeon_rooms.items():
            if room_id not in self._procedural_dungeon.floors.get("floor_1", {}).rooms:
                pass
        self.dungeon_rooms = {}
        self._use_procedural = True

    def step_forward(self) -> ExplorationResult:
        """Step 50: 1歩前進 (エモートなし + ランダム足音 footstep00〜09)"""
        idx = random.randint(0, 9)
        sound_name = f"footstep0{idx}.ogg"
        evt = self.presentation.add_event(
            emote_file=None, audio_file=sound_name, message="一歩前進"
        )

        return ExplorationResult(
            action_type="STEP",
            message="一歩、足を踏み出した。",
            current_room_id=self.current_room_id,
            played_sounds=[sound_name],
            presentation_events=[evt],
        )

    def move_to_room(self, target_room_id: str) -> ExplorationResult:
        """Step 51, 55: 部屋移動シーケンス (emote_dots2/exclamation + 連続足音3回 + doorOpen) + Phase 1 Step 7: 経験値付与"""
        if self._use_procedural and self._procedural_dungeon:
            result = self._procedural_dungeon.move_to_room_procedural(target_room_id)
            # Sync current_room_id with procedural dungeon
            self.current_room_id = self._procedural_dungeon.current_room_id
            return result

        if target_room_id not in self.dungeon_rooms:
            return ExplorationResult(
                action_type="MOVE_ROOM",
                message="行き先が存在しません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        sounds = []
        events = []

        # 連続足音3回
        for _ in range(3):
            s = f"footstep0{random.randint(0, 9)}.ogg"
            self.audio.play_sound(s)
            sounds.append(s)

        emote = "emote_exclamation.png" if target_room_id == "vault_chamber" else "emote_dots2.png"
        evt_enter = self.presentation.add_event(
            emote_file=emote,
            audio_file="doorOpen_1.ogg",
            message=f"{target_room_id} へ移動",
        )
        sounds.append("doorOpen_1.ogg")
        events.append(evt_enter)

        # Phase 1 Step 7: 初見判定と経験値付与
        is_first_visit = self._is_first_visit(target_room_id)
        is_first_floor = False  # フロア移動は別メソッドで処理
        room = self.dungeon_rooms[target_room_id]
        is_secret = self._is_secret_room(room)

        if is_first_visit:
            self._visited_rooms.add(target_room_id)
            self.exploration_rank.rooms_visited += 1
            self.exploration_rank.first_visit_bonuses += 1

        if is_secret and target_room_id not in self._visited_secret_rooms:
            self._visited_secret_rooms.add(target_room_id)
            self.exploration_rank.secret_rooms_found += 1

        # 経験値計算・付与（部屋数=1とする）
        current_depth = 1
        if self._procedural_dungeon:
            current_depth = self._procedural_dungeon.current_depth
        exp = self._calculate_exploration_exp(
            current_depth, 1, is_first_visit, is_first_floor, is_secret
        )
        gained_exp, ranked_up = self.add_exploration_exp(exp)
        if ranked_up:
            self._play_rank_up_fanfare(self.exploration_rank.rank)

        self.current_room_id = target_room_id

        # Phase 2 Step 19: 部屋移動時のアセンションノードチェック
        self._check_and_unlock_ascension_nodes()

        return ExplorationResult(
            action_type="MOVE_ROOM",
            message=f"【エリア進入】{room.name} に到達した。（{room.description}）",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=events,
        )

    def open_treasure_chest(self) -> ExplorationResult:
        """Step 52: 宝箱・コンテナ開封 (emote_star + metalLatch + doorOpen_1)"""
        if self._use_procedural and self._procedural_dungeon:
            floor = self._procedural_dungeon.get_current_floor()
            if floor:
                node = floor.rooms.get(self.current_room_id)
                if node and node.room.has_treasure:
                    node.room.has_treasure = False
                    self._procedural_dungeon.log_treasure_found(
                        self._procedural_dungeon.current_floor_id,
                        self.current_room_id,
                        ["ランダムアイテム"],
                    )

        sounds = ["metalLatch.ogg", "doorOpen_1.ogg"]
        evt = self.presentation.add_event(
            emote_file="emote_star.png",
            audio_file="metalLatch.ogg",
            message="宝箱の鍵を解錠！",
        )
        self.audio.play_sound("doorOpen_1.ogg")

        return ExplorationResult(
            action_type="LOOT_CHEST",
            message="【宝箱開封】錠前を外し、コンテナを開けた！",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt],
        )

    def escape_combat(self) -> ExplorationResult:
        """Step 53: 戦闘逃走 (emote_drops + footstep + cloth1)"""
        sounds = ["footstep01.ogg", "footstep02.ogg", "cloth1.ogg"]
        evt = self.presentation.add_event(
            emote_file="emote_drops.png",
            audio_file="cloth1.ogg",
            message="冷や汗を流しながら逃走！",
        )
        self.audio.play_sound("footstep01.ogg")
        self.audio.play_sound("footstep02.ogg")

        return ExplorationResult(
            action_type="ESCAPE",
            message="背を向け、一目散に路地裏へ逃亡した！",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt],
        )

    def trigger_trap_door(self) -> ExplorationResult:
        """Step 54: 退路遮断トラップ (emote_alert + doorClose_2)"""
        evt = self.presentation.add_event(
            emote_file="emote_alert.png",
            audio_file="doorClose_2.ogg",
            message="退路遮断トラップ作動！",
        )
        return ExplorationResult(
            action_type="TRAP",
            message="【トラップ発動！】背後の鉄扉が激しい音を立てて閉まり、退路が遮断された！",
            current_room_id=self.current_room_id,
            played_sounds=["doorClose_2.ogg"],
            presentation_events=[evt],
        )

    def get_current_room(self) -> DungeonRoom | None:
        if self._use_procedural and self._procedural_dungeon:
            node = self._procedural_dungeon.get_current_room()
            if node:
                return node.room
        return self.dungeon_rooms.get(self.current_room_id)

    def get_connected_rooms(self) -> list[str]:
        if self._use_procedural and self._procedural_dungeon:
            return [n.node_id for n in self._procedural_dungeon.get_connected_rooms()]
        return list(self.dungeon_rooms.keys())

    def descend_stairs(self) -> ExplorationResult:
        if self._use_procedural and self._procedural_dungeon:
            return self._procedural_dungeon.descend_stairs()
        return ExplorationResult(
            action_type="DESCEND",
            message="プロシージャルモードでのみ利用可能です。",
            current_room_id=self.current_room_id,
            played_sounds=[],
            presentation_events=[],
        )

    def ascend_stairs(self) -> ExplorationResult:
        if self._use_procedural and self._procedural_dungeon:
            return self._procedural_dungeon.ascend_stairs()
        return ExplorationResult(
            action_type="ASCEND",
            message="プロシージャルモードでのみ利用可能です。",
            current_room_id=self.current_room_id,
            played_sounds=[],
            presentation_events=[],
        )

    def get_minimap_data(self) -> dict:
        if self._use_procedural and self._procedural_dungeon:
            return self._procedural_dungeon.get_minimap_data()
        return {}

    @property
    def exploration_progress(self) -> float:
        if self._use_procedural and self._procedural_dungeon:
            return self._procedural_dungeon.exploration_progress
        return 0.0

    # Phase 1 Step 3: 初見判定ロジック
    def _is_first_visit(self, room_id: str) -> bool:
        return room_id not in self._visited_rooms

    def _is_first_floor(self, floor_depth: int) -> bool:
        return floor_depth not in self._visited_floors

    def _is_secret_room(self, room: DungeonRoom) -> bool:
        name = room.name
        return (
            "秘密" in name or "隠し" in name or "secret" in name.lower() or "hidden" in name.lower()
        )

    # Phase 1 Step 4: 探索経験値計算式
    def _calculate_exploration_exp(
        self,
        depth: int,
        room_count: int,
        is_first_visit: bool,
        is_first_floor: bool,
        is_secret: bool,
    ) -> int:
        base = depth * room_count * 10
        first_visit_bonus = 500 if is_first_visit else 0
        first_floor_bonus = 1000 if is_first_floor else 0
        secret_bonus = 2000 if is_secret else 0
        return base + first_visit_bonus + first_floor_bonus + secret_bonus

    # Phase 1 Step 5: 経験値付与・ランクアップ処理
    def add_exploration_exp(self, exp: int) -> tuple[int, bool]:
        old_rank = self.exploration_rank.rank
        self.exploration_rank.total_exp += exp
        new_rank = ExplorationRank.calculate_rank_from_exp(self.exploration_rank.total_exp)
        self.exploration_rank.rank = new_rank
        ranked_up = new_rank > old_rank
        return exp, ranked_up

    # Phase 1 Step 6: ランクアップ演出・音声連動
    def _play_rank_up_fanfare(self, new_rank: int) -> None:
        self.presentation.add_event(
            emote_file="emote_crown.png",
            audio_file="rank_up_fanfare.ogg",
            message=f"探索ランク {new_rank} に昇格！",
        )
        self.audio.play_sound("rank_up_fanfare.ogg")

    # Phase 1 Step 9: 秘密部屋発見ボーナス
    def discover_secret_room(self, room_id: str) -> ExplorationResult:
        room = self.dungeon_rooms.get(room_id)
        if not room:
            return ExplorationResult(
                action_type="SECRET_DISCOVER",
                message="部屋が見つかりません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        is_secret = self._is_secret_room(room)
        if not is_secret:
            return ExplorationResult(
                action_type="SECRET_DISCOVER",
                message="ここは秘密部屋ではありません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        if room_id in self._visited_secret_rooms:
            return ExplorationResult(
                action_type="SECRET_DISCOVER",
                message="既に発見済みの秘密部屋です。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        self._visited_secret_rooms.add(room_id)
        self.exploration_rank.secret_rooms_found += 1

        # 経験値付与（秘密ボーナス含む）
        current_depth = 1
        if self._procedural_dungeon:
            current_depth = self._procedural_dungeon.current_depth
        exp = self._calculate_exploration_exp(current_depth, 1, True, False, True)
        gained_exp, ranked_up = self.add_exploration_exp(exp)
        if ranked_up:
            self._play_rank_up_fanfare(self.exploration_rank.rank)

        # 演出
        evt = self.presentation.add_event(
            emote_file="emote_crystal.png",
            audio_file="crystal_resonance.ogg",
            message="秘密部屋を発見！",
        )
        self.audio.play_sound("crystal_resonance.ogg")

        return ExplorationResult(
            action_type="SECRET_DISCOVER",
            message=f"【秘密部屋発見】{room.name} を見つけた！ 探索経験値 +{exp}",
            current_room_id=room_id,
            played_sounds=["crystal_resonance.ogg"],
            presentation_events=[evt],
        )

    # Phase 1 Step 11: 探索ランクUI表示用データ取得
    def get_exploration_rank_info(self) -> dict:
        rank = self.exploration_rank
        next_rank_exp = rank.rank * ExplorationRank.EXP_PER_RANK
        return {
            "rank": rank.rank,
            "total_exp": rank.total_exp,
            "next_rank_exp": next_rank_exp,
            "exp_to_next": max(0, next_rank_exp - rank.total_exp),
            "max_depth": rank.max_depth_reached,
            "rooms_visited": rank.rooms_visited,
            "secrets_found": rank.secret_rooms_found,
            "floors_cleared": rank.floors_cleared,
        }

    # Phase 1 Step 12: セーブ/ロード対応
    def to_dict(self) -> dict:
        return {
            "exploration_rank": self.exploration_rank.to_dict(),
            "visited_rooms": list(self._visited_rooms),
            "visited_floors": list(self._visited_floors),
            "visited_secret_rooms": list(self._visited_secret_rooms),
            "current_room_id": self.current_room_id,
        }

    # Phase 2 Step 18/19/20/21: アセンションボード連動ノードチェック
    def _check_and_unlock_ascension_nodes(self) -> None:
        """探索連動アセンションノードの条件チェックと解放"""
        try:
            from skill_eater_ascension_board import AscensionBoard
            from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager

            ascension_board = (
                AscensionBoard.get_instance() if hasattr(AscensionBoard, "get_instance") else None
            )
            dungeon_manager = (
                SkillEaterDungeonFloorManager.get_instance()
                if hasattr(SkillEaterDungeonFloorManager, "get_instance")
                else None
            )

            if ascension_board:
                ascension_board.check_and_unlock_exploration_nodes(
                    self.exploration_rank, dungeon_manager
                )
        except Exception:
            # 循環インポートや未初期化時はスキップ
            pass

    @classmethod
    def from_dict(cls, data: dict, audio=None, presentation=None) -> "SkillEaterExplorationSystem":
        instance = cls(audio=audio, presentation=presentation)
        instance.exploration_rank = ExplorationRank.from_dict(data.get("exploration_rank", {}))
        instance._visited_rooms = set(data.get("visited_rooms", []))
        instance._visited_floors = set(data.get("visited_floors", []))
        instance._visited_secret_rooms = set(data.get("visited_secret_rooms", []))
        instance.current_room_id = data.get("current_room_id", "slum_alley")
        return instance
