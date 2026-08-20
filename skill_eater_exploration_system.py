"""
skill_eater_exploration_system.py
Aの世界（スキル喰い） 探索・移動・環境音システム
提案7: ダンジョン探索・足音・扉・トラップのEmote & Audio演出 (Steps 49〜56)
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from skill_eater_system import CharacterState
from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem, PresentationEvent


@dataclass
class DungeonRoom:
    room_id: str
    name: str
    description: str
    has_treasure: bool = False
    has_trap: bool = False
    enemies: List[CharacterState] = field(default_factory=list)


@dataclass
class ExplorationResult:
    action_type: str  # 'STEP', 'MOVE_ROOM', 'OPEN_DOOR', 'LOOT_CHEST', 'ESCAPE', 'TRAP'
    message: str
    current_room_id: str
    played_sounds: List[str] = field(default_factory=list)
    presentation_events: List[PresentationEvent] = field(default_factory=list)  # Step 49: 演出リスト


class SkillEaterExplorationSystem:
    def __init__(
        self,
        audio: Optional[SkillEaterAudioSystem] = None,
        presentation: Optional[SkillEaterPresentationSystem] = None
    ):
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.dungeon_rooms: Dict[str, DungeonRoom] = {
            "slum_alley": DungeonRoom("slum_alley", "スラムの裏路地", "薄暗く湿った路地。遠くでサイレンが鳴り響く。"),
            "underground_market": DungeonRoom("underground_market", "地下闇市場通り", "違法スキルの密売人たちが行き交う。"),
            "midas_tower_entrance": DungeonRoom("midas_tower_entrance", "ミダスタワー正面玄関", "巨大な黄金の扉がそびえ立つ。"),
            "vault_chamber": DungeonRoom("vault_chamber", "バベルの金庫室", "秘匿された至高のスキルが眠る金庫。", has_treasure=True)
        }
        self.current_room_id: str = "slum_alley"

    def step_forward(self) -> ExplorationResult:
        """Step 50: 1歩前進 (エモートなし + ランダム足音 footstep00〜09)"""
        idx = random.randint(0, 9)
        sound_name = f"footstep0{idx}.ogg"
        evt = self.presentation.add_event(
            emote_file=None,
            audio_file=sound_name,
            message="一歩前進"
        )

        return ExplorationResult(
            action_type="STEP",
            message="一歩、足を踏み出した。",
            current_room_id=self.current_room_id,
            played_sounds=[sound_name],
            presentation_events=[evt]
        )

    def move_to_room(self, target_room_id: str) -> ExplorationResult:
        """Step 51, 55: 部屋移動シーケンス (emote_dots2/exclamation + 連続足音3回 + doorOpen)"""
        if target_room_id not in self.dungeon_rooms:
            return ExplorationResult(
                action_type="MOVE_ROOM",
                message="行き先が存在しません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[]
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
            message=f"{target_room_id} へ移動"
        )
        sounds.append("doorOpen_1.ogg")
        events.append(evt_enter)

        self.current_room_id = target_room_id
        room = self.dungeon_rooms[target_room_id]

        return ExplorationResult(
            action_type="MOVE_ROOM",
            message=f"【エリア進入】{room.name} に到達した。（{room.description}）",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=events
        )

    def open_treasure_chest(self) -> ExplorationResult:
        """Step 52: 宝箱・コンテナ開封 (emote_star + metalLatch + doorOpen_1)"""
        sounds = ["metalLatch.ogg", "doorOpen_1.ogg"]
        evt = self.presentation.add_event(
            emote_file="emote_star.png",
            audio_file="metalLatch.ogg",
            message="宝箱の鍵を解錠！"
        )
        self.audio.play_sound("doorOpen_1.ogg")

        return ExplorationResult(
            action_type="LOOT_CHEST",
            message="【宝箱開封】錠前を外し、コンテナを開けた！",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt]
        )

    def escape_combat(self) -> ExplorationResult:
        """Step 53: 戦闘逃走 (emote_drops + footstep + cloth1)"""
        sounds = ["footstep01.ogg", "footstep02.ogg", "cloth1.ogg"]
        evt = self.presentation.add_event(
            emote_file="emote_drops.png",
            audio_file="cloth1.ogg",
            message="冷や汗を流しながら逃走！"
        )
        self.audio.play_sound("footstep01.ogg")
        self.audio.play_sound("footstep02.ogg")

        return ExplorationResult(
            action_type="ESCAPE",
            message="背を向け、一目散に路地裏へ逃亡した！",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt]
        )

    def trigger_trap_door(self) -> ExplorationResult:
        """Step 54: 退路遮断トラップ (emote_alert + doorClose_2)"""
        evt = self.presentation.add_event(
            emote_file="emote_alert.png",
            audio_file="doorClose_2.ogg",
            message="退路遮断トラップ作動！"
        )
        return ExplorationResult(
            action_type="TRAP",
            message="【トラップ発動！】背後の鉄扉が激しい音を立てて閉まり、退路が遮断された！",
            current_room_id=self.current_room_id,
            played_sounds=["doorClose_2.ogg"],
            presentation_events=[evt]
        )
