"""
skill_eater_facility_actions.py
Aの世界（スキル喰い） アジト施設アクションシステム
Phase 5: 施設アクション・NPCインタラクション
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import (
    PresentationEvent,
    SkillEaterPresentationSystem,
)
from skill_eater_system import CharacterState, SkillEaterRegistry

if TYPE_CHECKING:
    from skill_eater_economy_system import BaseFacility, FactionState, SkillEaterEconomySystem

logger = logging.getLogger(__name__)


@dataclass
class MercenaryContract:
    merc_type: str
    name: str
    duration_turns: int
    effects: dict[str, Any]
    is_elite: bool = False


@dataclass
class FacilityAction:
    id: str
    name: str
    facility_id: str
    cost_junk: int = 0
    cost_aldo: int = 0
    cost_time_turns: int = 0
    required_skill: str | None = None
    base_success_rate: float = 0.50
    max_success_rate: float = 0.95
    audio_file: str = ""
    emote_file: str = ""
    description: str = ""
    success_audio: str | None = None
    failure_audio: str | None = None
    critical_audio: str | None = None


@dataclass
class FacilityActionResult:
    action_id: str
    facility_name: str
    success: bool
    is_critical: bool = False
    consumed_junk: int = 0
    consumed_aldo: int = 0
    consumed_time: int = 0
    rewards: dict[str, Any] = field(default_factory=dict)
    log_message: str = ""
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[PresentationEvent] = field(default_factory=list)


class FacilityActionRegistry:
    _instance: FacilityActionRegistry | None = None

    def __init__(self):
        self._actions: dict[str, FacilityAction] = {}
        self._register_all_actions()

    @classmethod
    def get_instance(cls) -> FacilityActionRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def _register_all_actions(self):
        self._register_workshop_actions()
        self._register_lab_actions()
        self._register_medbay_actions()
        self._register_command_actions()
        self._register_bar_actions()

    def _register_workshop_actions(self):
        self._actions["craft_implant"] = FacilityAction(
            id="craft_implant",
            name="インプラント製作",
            facility_id="workshop",
            cost_junk=50,
            cost_aldo=500,
            cost_time_turns=1,
            required_skill="rar_utility_005",
            base_success_rate=0.40,
            audio_file="metalPot1.ogg",
            emote_file="emote_stars.png",
            description="スキルスロット拡張用インプラントを製作する",
            success_audio="metalPot3.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["repair_gear"] = FacilityAction(
            id="repair_gear",
            name="装備修理",
            facility_id="workshop",
            cost_junk=30,
            cost_aldo=200,
            cost_time_turns=1,
            required_skill=None,
            base_success_rate=0.70,
            audio_file="chop.ogg",
            emote_file="emote_heart.png",
            description="損傷した装備を修理し性能を回復する",
            success_audio="metalPot1.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["install_cybernetic"] = FacilityAction(
            id="install_cybernetic",
            name="義体インストール",
            facility_id="workshop",
            cost_junk=100,
            cost_aldo=2000,
            cost_time_turns=2,
            required_skill="rar_utility_005",
            base_success_rate=0.30,
            audio_file="metalPot2.ogg",
            emote_file="emote_exclamation.png",
            description="高度な義体パーツを身体に埋め込み能力を永続強化",
            success_audio="metalPot3.ogg",
            failure_audio="creak3.ogg",
            critical_audio="handleSmallLeather2.ogg",
        )

    def _register_lab_actions(self):
        self._actions["analyze_skill_crystal"] = FacilityAction(
            id="analyze_skill_crystal",
            name="スキル結晶解析",
            facility_id="lab",
            cost_junk=20,
            cost_aldo=1000,
            cost_time_turns=1,
            required_skill="com_magic_001",
            base_success_rate=0.60,
            audio_file="metalClick.ogg",
            emote_file="emote_idea.png",
            description="未知のスキル結晶を解析し、スキル定義を解放する",
            success_audio="metalLatch.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["reverse_engineer_tech"] = FacilityAction(
            id="reverse_engineer_tech",
            name="敵装備リバースエンジニアリング",
            facility_id="lab",
            cost_junk=80,
            cost_aldo=1500,
            cost_time_turns=2,
            required_skill="rar_utility_005",
            base_success_rate=0.35,
            audio_file="metalClick.ogg",
            emote_file="emote_dots3.png",
            description="敵の装備・技術を解析し、新規合成レシピを獲得する",
            success_audio="metalPot3.ogg",
            failure_audio="creak2.ogg",
        )

        self._actions["develop_countermeasure"] = FacilityAction(
            id="develop_countermeasure",
            name="対策開発",
            facility_id="lab",
            cost_junk=50,
            cost_aldo=3000,
            cost_time_turns=3,
            required_skill="uni_midas_001",
            base_success_rate=0.25,
            audio_file="metalPot2.ogg",
            emote_file="emote_stars.png",
            description="特定ボス/敵タイプへの対抗手段(メタ特効)を開発する",
            success_audio="metalPot3.ogg",
            failure_audio="creak2.ogg",
        )

    def _register_medbay_actions(self):
        self._actions["treat_toxicity"] = FacilityAction(
            id="treat_toxicity",
            name="毒性治療",
            facility_id="medbay",
            cost_junk=10,
            cost_aldo=500,
            cost_time_turns=1,
            required_skill=None,
            base_success_rate=0.80,
            audio_file="metalClick.ogg",
            emote_file="emote_hearts.png",
            description="スキル精神侵食度(毒性)を軽減する治療を行う",
            success_audio="handleSmallLeather2.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["augment_servant"] = FacilityAction(
            id="augment_servant",
            name="従属者強化手術",
            facility_id="medbay",
            cost_junk=60,
            cost_aldo=1000,
            cost_time_turns=2,
            required_skill="rar_utility_005",
            base_success_rate=0.45,
            audio_file="beltHandle1.ogg",
            emote_file="emote_heart.png",
            description="捕獲した従属者(サーヴァント)を手術で強化する",
            success_audio="metalPot1.ogg",
            failure_audio="creak3.ogg",
        )

        self._actions["memory_wipe"] = FacilityAction(
            id="memory_wipe",
            name="記憶消去・リセット",
            facility_id="medbay",
            cost_junk=0,
            cost_aldo=5000,
            cost_time_turns=3,
            required_skill="con_fire_001",
            base_success_rate=0.20,
            audio_file="doorClose_3.ogg",
            emote_file="emote_cross.png",
            description="スキル記憶を完全消去し、クリーンな状態で再出発する(危険)",
            success_audio="doorOpen_2.ogg",
            failure_audio="doorClose_1.ogg",
            critical_audio="bookClose.ogg",
        )

    def _register_command_actions(self):
        self._actions["dispatch_squad"] = FacilityAction(
            id="dispatch_squad",
            name="部隊派遣",
            facility_id="command",
            cost_junk=30,
            cost_aldo=1000,
            cost_time_turns=2,
            required_skill=None,
            base_success_rate=0.55,
            audio_file="doorOpen_1.ogg",
            emote_file="emote_exclamations.png",
            description="抵抗軍部隊を派遣し、資源回収や偵察を行わせる",
            success_audio="doorClose_2.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["plan_raid"] = FacilityAction(
            id="plan_raid",
            name="襲撃計画立案",
            facility_id="command",
            cost_junk=50,
            cost_aldo=2000,
            cost_time_turns=3,
            required_skill="rar_combat_012",
            base_success_rate=0.40,
            audio_file="bookFlip3.ogg",
            emote_file="emote_idea.png",
            description="ミダス施設やボス拠点への襲撃作戦を練り、成功率を高める",
            success_audio="metalLatch.ogg",
            failure_audio="creak2.ogg",
        )

        self._actions["negotiate_truce"] = FacilityAction(
            id="negotiate_truce",
            name="休戦交渉",
            facility_id="command",
            cost_junk=0,
            cost_aldo=10000,
            cost_time_turns=1,
            required_skill=None,
            base_success_rate=0.30,
            audio_file="handleCoins.ogg",
            emote_file="emote_hearts.png",
            description="敵対派閥と休戦協定を結び、一時的に敵対関係を解除する",
            success_audio="doorOpen_2.ogg",
            failure_audio="doorClose_1.ogg",
        )

    def _register_bar_actions(self):
        self._actions["gather_intel"] = FacilityAction(
            id="gather_intel",
            name="情報収集",
            facility_id="bar",
            cost_junk=0,
            cost_aldo=500,
            cost_time_turns=1,
            required_skill=None,
            base_success_rate=0.65,
            audio_file="handleCoins.ogg",
            emote_file="emote_idea.png",
            description="酒場の噂話から貴重な情報を聞き出す",
            success_audio="bookOpen.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["hire_mercenary"] = FacilityAction(
            id="hire_mercenary",
            name="傭兵雇用",
            facility_id="bar",
            cost_junk=0,
            cost_aldo=3000,
            cost_time_turns=1,
            required_skill=None,
            base_success_rate=0.70,
            audio_file="handleCoins.ogg",
            emote_file="emote_cash.png",
            description="傭兵を雇い、次の探索/戦闘に同行させる",
            success_audio="beltHandle1.ogg",
            failure_audio="creak1.ogg",
        )

        self._actions["launder_aldo"] = FacilityAction(
            id="launder_aldo",
            name="アルド洗浄(マネロン)",
            facility_id="bar",
            cost_junk=0,
            cost_aldo=0,
            cost_time_turns=2,
            required_skill="rar_utility_005",
            base_success_rate=0.50,
            audio_file="handleCoins2.ogg",
            emote_file="emote_cash.png",
            description="違法入手のアルド(熱い金)を洗浄し、安全な資金に変える",
            success_audio="metalClick.ogg",
            failure_audio="doorClose_1.ogg",
        )

    def get_action(self, action_id: str) -> FacilityAction | None:
        return self._actions.get(action_id)

    def get_actions_by_facility(self, facility_id: str) -> list[FacilityAction]:
        return [a for a in self._actions.values() if a.facility_id == facility_id]

    def get_all_actions(self) -> list[FacilityAction]:
        return list(self._actions.values())


def calculate_success_rate(facility: BaseFacility, player: CharacterState, action: FacilityAction) -> float:
    rate = action.base_success_rate + facility.level * 0.15
    if action.required_skill and player.has_skill(action.required_skill):
        slot = player.skills[action.required_skill]
        rate += slot.level * 0.05
    return min(rate, action.max_success_rate)


def can_afford_action(player: CharacterState, economy: SkillEaterEconomySystem, action: FacilityAction) -> tuple[bool, str]:
    if player.junk < action.cost_junk:
        return False, "ジャンクが不足しています"
    if economy.aldo_currency < action.cost_aldo:
        return False, "アルドが不足しています"
    cooldown = player.facility_action_cooldowns.get(action.id, 0)
    if cooldown > 0:
        return False, f"クールダウン中です (残り {cooldown} ターン)"
    return True, ""


# ============================================================
# Workshop Actions Execution Logic
# ============================================================

def execute_craft_implant(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 10, 11: インプラント製作実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        memory_gain = 4 if is_critical else 2
        player.max_memory_capacity = min(20, player.max_memory_capacity + memory_gain)

        rewards = {"memory_capacity_gain": memory_gain}
        if is_critical:
            rewards["rare_implant"] = True

        log_msg = f"【インプラント製作成功】メモリ容量 +{memory_gain} (最大: {player.max_memory_capacity})"
        if is_critical:
            log_msg += " レアインプラントを獲得！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        if is_critical and action.critical_audio:
            audio.play_sound(action.critical_audio)
            sounds.append(action.critical_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【製作失敗】材料が不純でインプラントの製作に失敗した..."

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_repair_gear(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 13, 14: 装備修理実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        atk_buff = 6 if is_critical else 3
        def_buff = 10 if is_critical else 5
        duration = 5 if is_critical else 3

        player.status_effects.append(f"RepairBuff_ATK_{atk_buff}_{duration}")
        player.status_effects.append(f"RepairBuff_DEF_{def_buff}_{duration}")

        rewards = {"atk_buff": atk_buff, "def_buff": def_buff, "duration": duration}
        log_msg = f"【装備修理完了】攻撃力+{atk_buff} 防御力+{def_buff} ({duration}ターン持続)"
        if is_critical:
            log_msg += " 完璧な修理で効果が上昇！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【修理失敗】修理途中で部品が外れてしまった..."

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_install_cybernetic(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 16, 17: 義体インストール実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        stat_choices = [
            ("atk", 5, "攻撃力"),
            ("defense", 5, "防御力"),
            ("speed", 3, "速度"),
            ("intelligence", 3, "知力"),
        ]
        if is_critical:
            chosen = random.sample(stat_choices, 2)
        else:
            chosen = [random.choice(stat_choices)]

        rewards = {"stats": []}
        log_parts = []
        for stat, value, name in chosen:
            setattr(player, stat, getattr(player, stat) + value)
            rewards["stats"].append({"stat": stat, "value": value})
            log_parts.append(f"{name}+{value}")

        if is_critical:
            player.status_effects.append("Cybernetic")
            rewards["cybernetic_trait"] = True

        log_msg = f"【義体インストール成功】{'、'.join(log_parts)} が永続上昇！"
        if is_critical:
            log_msg += " 複数箇所同時施術に成功！特性《義体適応》獲得！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        if is_critical and action.critical_audio:
            audio.play_sound(action.critical_audio)
            sounds.append(action.critical_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        player.hp = max(1, player.hp - 20)
        player.status_effects.append("SurgeryTrauma")
        log_msg = "【手術失敗】拒絶反応が発生！大ダメージを受け『手術外傷』状態に..."

        evt = presentation.add_event(
            emote_file="emote_faceSad.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)
        audio.play_sound("cloth3.ogg")
        sounds.append("cloth3.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


# ============================================================
# Lab Actions Execution Logic
# ============================================================

def execute_analyze_skill_crystal(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 22, 23: スキル結晶解析実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    if not player.unidentified_crystals:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="解析対象の未鑑定スキル結晶を持っていません。",
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        crystal_id = player.unidentified_crystals.pop(0)
        registry = SkillEaterRegistry.get_instance()
        skill_def = registry.get_skill(crystal_id)

        if skill_def:
            skill_def.is_encrypted = False

        rewards = {"decrypted_skill": crystal_id}
        log_msg = f"【解析成功】《{crystal_id}》の暗号化が解除され、スキル定義が判明！"
        if is_critical:
            if skill_def:
                rewards["market_value"] = skill_def.market_value
                rewards["tier"] = skill_def.tier.value
            log_msg += f" さらに市場価値({skill_def.market_value if skill_def else '不明'})とTier({skill_def.tier.value if skill_def else '不明'})も判明！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("bookOpen.ogg")
        sounds.append("bookOpen.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【解析失敗】結晶の共振が読み取れない..."

        evt = presentation.add_event(
            emote_file="emote_question.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_reverse_engineer_tech(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 25, 26: リバースエンジニアリング実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        from skill_eater_synthesis_system import SkillEaterSynthesisSystem
        synthesis = SkillEaterSynthesisSystem(registry=SkillEaterRegistry.get_instance())

        all_possible_recipes = [
            ("com_combat_001", "com_magic_001", "rar_infrared_vision"),
            ("rar_combat_012", "uni_midas_001", "rar_gold_body"),
            ("com_magic_001", "com_labor_002", "rar_infrared_vision"),
            ("com_combat_002", "com_labor_001", "rar_utility_005"),
        ]

        new_recipes = []
        for id_a, id_b, result in all_possible_recipes:
            key1 = (id_a, id_b)
            key2 = (id_b, id_a)
            if key1 not in synthesis._static_recipes and key2 not in synthesis._static_recipes:
                new_recipes.append((id_a, id_b, result))

        if new_recipes:
            recipe_count = 2 if is_critical else 1
            gained = []
            for _ in range(min(recipe_count, len(new_recipes))):
                id_a, id_b, result = random.choice(new_recipes)
                synthesis.register_static_recipe(id_a, id_b, result)
                gained.append(f"{id_a}+{id_b}={result}")
                new_recipes.remove((id_a, id_b, result))

            rewards = {"new_recipes": gained}
            log_msg = f"【リバースエンジニアリング成功】新規合成レシピを獲得: {', '.join(gained)}"
            if is_critical:
                log_msg += " 違法フラグなしのレアレシピも含まれている！"
        else:
            rewards = {}
            log_msg = "【解析完了】新たなレシピは発見できなかったが、技術データを蓄積した。"

        evt = presentation.add_event(
            emote_file="emote_stars.png",
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("bookFlip1.ogg")
        sounds.append("bookFlip1.ogg")
        audio.play_sound("bookFlip2.ogg")
        sounds.append("bookFlip2.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【解析失敗】技術が難解すぎて解読不能..."

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_develop_countermeasure(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    boss_id: str = "midas_ceo",
) -> FacilityActionResult:
    """Step 28, 29: 対策開発実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        if not hasattr(economy, "developed_countermeasures"):
            economy.developed_countermeasures = {}

        economy.developed_countermeasures[boss_id] = True

        rewards = {"countermeasure": boss_id, "permanent": is_critical}
        log_msg = f"【対策開発成功】{boss_id}へのメタ特効を開発！次回遭遇時に有利に！"
        if is_critical:
            from skill_eater_meta_quest_system import GlobalRuleEngine
            rule_engine = GlobalRuleEngine.get_instance()
            rule_engine.is_boss_instant_kill_enabled = False
            log_msg += " ボスの即死ギミックを恒久的に無効化！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("metalPot2.ogg")
        sounds.append("metalPot2.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【開発失敗】対策データの構築に失敗..."

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


# ============================================================
# Medbay Actions Execution Logic
# ============================================================

def execute_treat_toxicity(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 34, 35: 毒性治療実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        old_toxicity = player.addiction_buildup
        reduction = 0 if is_critical else 30
        player.addiction_buildup = max(0, player.addiction_buildup - reduction)

        if "Addicted" in player.status_effects:
            player.status_effects.remove("Addicted")

        if is_critical:
            player.status_effects.append("MentalStability_5")

        rewards = {"toxicity_reduction": old_toxicity - player.addiction_buildup, "mental_stability": is_critical}
        log_msg = f"【毒性治療成功】精神侵食度 {old_toxicity} → {player.addiction_buildup}"
        if is_critical:
            log_msg += " 完全回復！『精神安定』バフ獲得(5ターン侵食無効)！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        player.addiction_buildup = max(0, player.addiction_buildup - 10)
        log_msg = "【治療不完全】治療薬が合わなかった... 微減にとどまる"

        evt = presentation.add_event(
            emote_file="emote_swirl.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_augment_servant(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    servant_system,
    servant_id: str,
) -> FacilityActionResult:
    """Step 37, 38: 従属者強化手術実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    if not servant_system or not hasattr(servant_system, 'servant_party'):
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="従属者システムが初期化されていません。",
        )

    servant = servant_system.servant_party.get(servant_id)
    if not servant:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="指定された従属者が見つかりません。",
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        atk_gain = 20 if is_critical else 10
        hp_gain = 100 if is_critical else 50
        duration_gain = 5 if is_critical else 2

        servant.state.atk += atk_gain
        servant.state.max_hp += hp_gain
        servant.state.hp += hp_gain
        servant.duration_turns += duration_gain

        com_skills = ["com_combat_001", "com_combat_002", "com_magic_001", "com_labor_001", "com_labor_002"]
        new_skill = random.choice([s for s in com_skills if not servant.state.has_skill(s)])
        servant.state.add_skill(new_skill)

        registry = SkillEaterRegistry.get_instance()
        skill_def = registry.get_skill(new_skill)
        skill_name = skill_def.name if skill_def else new_skill

        rewards = {"atk_gain": atk_gain, "hp_gain": hp_gain, "duration_gain": duration_gain, "new_skill": new_skill}
        log_msg = f"【強化手術成功】{servant.custom_name}: 攻撃+{atk_gain} HP+{hp_gain} 稼働+{duration_gain}ターン 新スキル《{skill_name}》習得！"
        if is_critical:
            log_msg += " エリート強化！外観も変化した。"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        servant.state.hp = max(1, servant.state.hp - 30)
        log_msg = f"【手術失敗】拒絶反応で{servant.custom_name}が損傷(HP-30)..."

        evt = presentation.add_event(
            emote_file="emote_faceSad.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)
        audio.play_sound("creak3.ogg")
        sounds.append("creak3.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_memory_wipe(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 40, 41: 記憶消去・リセット実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        old_skills = list(player.skills.keys())
        old_archived = list(player.archived_skills.keys())

        player.skills.clear()
        player.archived_skills.clear()
        player.addiction_buildup = 0
        player.max_memory_capacity += 5
        player.is_husk = False
        player.status_effects = [s for s in player.status_effects if s not in ["Addicted", "SkillLossShock"]]

        rewards = {
            "cleared_skills": old_skills,
            "cleared_archived": old_archived,
            "memory_capacity_gain": 5,
            "tabula_rasa": True,
        }
        if is_critical:
            player.analysis_level += 2
            player.add_skill("Blank_Slate")
            rewards["analysis_gain"] = 2
            rewards["blank_slate"] = True

        log_msg = f"【記憶消去完了】全{len(old_skills)}スキル・{len(old_archived)}アーカイブスキルを消去。メモリ容量+5、侵食度0にリセット。実績《Tabula Rasa》獲得！"
        if is_critical:
            log_msg += " クリティカル成功！解析Lv+2、特殊スキル《白紙の状態》獲得(次回捕食成功率+50%)！"

        evt = presentation.add_event(
            emote_file="emote_heart.png",
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("bookClose.ogg")
        sounds.append("bookClose.ogg")

        if is_critical and action.critical_audio:
            audio.play_sound(action.critical_audio)
            sounds.append(action.critical_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        player.hp = 1
        player.status_effects.extend(["Amnesia", "Broken"])
        log_msg = "【記憶消去暴走】プロセスが制御不能に！自我が崩壊しかけ、瀕死&『記憶喪失』『完全崩壊』状態に..."

        evt = presentation.add_event(
            emote_file="emote_faceSad.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)
        audio.play_sound("creak3.ogg")
        sounds.append("creak3.ogg")
        audio.play_sound("cloth3.ogg")
        sounds.append("cloth3.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


# ============================================================
# Command Room Actions Execution Logic
# ============================================================

def execute_dispatch_squad(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    mission_type: str = "scavenge",
) -> FacilityActionResult:
    """Step 46, 47: 部隊派遣実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        rewards = {}
        log_parts = []

        if mission_type == "scavenge":
            junk_gain = random.randint(50, 100) * (2 if is_critical else 1)
            aldo_gain = random.randint(200, 500) * (2 if is_critical else 1)
            player.junk += junk_gain
            economy.aldo_currency += aldo_gain
            rewards = {"junk": junk_gain, "aldo": aldo_gain}
            log_parts.append(f"ジャンク+{junk_gain} アルド+{aldo_gain}")
            if is_critical:
                rewards["special_item"] = "MissionReport"
                log_parts.append("特殊アイテム《作戦記録》獲得！")

        elif mission_type == "recon":
            rewards = {"recon_data": True}
            log_parts.append("次ダンジョンの敵構成・弱点情報を入手！")
            if is_critical:
                rewards["full_map"] = True
                log_parts.append("完全マップデータも入手！")

        elif mission_type == "sabotage":
            economy.factions["midas"].influence_points = max(0, economy.factions["midas"].influence_points - 200 * (2 if is_critical else 1))
            economy.heat_level = max(0, economy.heat_level - 10 * (2 if is_critical else 1))
            rewards = {"midas_influence_loss": 200 * (2 if is_critical else 1), "heat_reduction": 10 * (2 if is_critical else 1)}
            log_parts.append(f"ミダス影響力-{rewards['midas_influence_loss']} 警戒度-{rewards['heat_reduction']}")

        log_msg = f"【部隊派遣成功:{mission_type}】" + "、".join(log_parts)
        if is_critical:
            log_msg += " 大成功！報酬2倍！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("doorOpen_1.ogg")
        sounds.append("doorOpen_1.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【派遣失敗】部隊が帰還せず... 損失を出した。"

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_plan_raid(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    target_id: str = "midas_branch",
) -> FacilityActionResult:
    """Step 49, 50: 襲撃計画立案実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        if not hasattr(economy, "raid_plans"):
            economy.raid_plans = {}

        economy.raid_plans[target_id] = True

        rewards = {"raid_plan": target_id, "permanent": is_critical}
        log_msg = f"【襲撃計画立案成功】{target_id}への作戦を立案！次回戦闘で捕食成功率+20%、先制権獲得！"
        if is_critical:
            from skill_eater_meta_quest_system import GlobalRuleEngine
            rule_engine = GlobalRuleEngine.get_instance()
            rule_engine.is_boss_instant_kill_enabled = False
            rewards["instant_kill_disabled"] = True
            log_msg += " ボスの即死ギミックを恒久的に無効化！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("bookFlip3.ogg")
        sounds.append("bookFlip3.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        economy.heat_level += 20
        log_msg = "【計画露見】情報が漏洩し、計画が露見した！警戒度上昇。"

        evt = presentation.add_event(
            emote_file="emote_alert.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_negotiate_truce(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    faction_id: str = "midas",
) -> FacilityActionResult:
    """Step 52, 53: 休戦交渉実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    faction = economy.factions.get(faction_id)
    if not faction:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="指定された派閥が存在しません。",
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        was_hostile = faction.is_hostile
        faction.is_hostile = False
        old_rep = faction.reputation
        faction.reputation = min(100, faction.reputation + 30)
        economy.heat_level = 0

        rewards = {"faction": faction_id, "reputation_gain": faction.reputation - old_rep, "permanent": is_critical}
        if is_critical:
            rewards["permanent_neutral"] = True

        log_msg = f"【休戦交渉成功】{faction.name}と休戦協定締結！敵対解除、好感度{old_rep}→{faction.reputation}、警戒度0 (10ターン持続)"
        if is_critical:
            log_msg += " 永続的中立化達成！特殊クエスト解放！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("handleCoins.ogg")
        sounds.append("handleCoins.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        faction.reputation = max(-100, faction.reputation - 20)
        log_msg = f"【交渉決裂】{faction.name}は激怒している！好感度低下、警戒度上昇。"

        evt = presentation.add_event(
            emote_file="emote_anger.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)
        audio.play_sound("creak2.ogg")
        sounds.append("creak2.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


# ============================================================
# Bar Actions Execution Logic
# ============================================================

def execute_gather_intel(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 58, 59: 情報収集実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    intel_categories = [
        ("boss_weakness", "《黄金錬成》の弱点は【氷属性】との噂..."),
        ("hidden_recipe", "地下倉庫に未鑑定スキル結晶が眠っているらしい..."),
        ("faction_movement", "ミダスの増援部隊が北方面へ移動中との情報..."),
        ("secret_vault", "旧市街区画B-7に隠し金庫があるという話..."),
    ]

    if is_success:
        category, hint = random.choice(intel_categories)
        rewards = {"intel_category": category}
        log_msg = f"【情報収集成功】{hint}"

        if is_critical:
            if category == "boss_weakness":
                rewards["confirmed_weakness"] = "Ice"
                log_msg = "【確定情報】《黄金錬成》の弱点は【氷属性】で確定！"
            elif category == "hidden_recipe":
                rewards["confirmed_recipe"] = "proc_syn_rare_001"
                log_msg = "【確定情報】隠しレシピID: proc_syn_rare_001 (場所: 地下倉庫)"
            elif category == "secret_vault":
                rewards["vault_location"] = "B-7"
                log_msg = "【確定情報】隠し金庫座標: 旧市街区画B-7 で確定！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("bookFlip1.ogg")
        sounds.append("bookFlip1.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        log_msg = "【情報収集失敗】有力な情報は得られなかった..."

        evt = presentation.add_event(
            emote_file="emote_dots3.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_hire_mercenary(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
) -> FacilityActionResult:
    """Step 61, 62: 傭兵雇用実行"""
    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    economy.aldo_currency -= action.cost_aldo
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    mercenary_types = [
        ("vanguard", "前衛傭兵", {"taunt": True, "damage_reduction": 0.5}, "敵の標的を引き受け、味方の被ダメージ軽減"),
        ("sniper", "狙撃傭兵", {"auto_attack": True, "damage_multiplier": 1.5}, "ターン開始時ランダム敵に攻撃"),
        ("medic", "医療傭兵", {"heal_per_turn": 30}, "ターン終了時味方全体回復"),
        ("hacker", "解析傭兵", {"analysis_bonus": 3, "auto_hack": True}, "解析Lv+3相当、暗号化自動ハック"),
    ]

    if is_success:
        merc_type, name, effects, desc = random.choice(mercenary_types)
        duration = 5 if is_critical else 3

        contract = MercenaryContract(
            merc_type=merc_type,
            name=name,
            duration_turns=duration,
            effects=effects,
            is_elite=is_critical,
        )

        if not hasattr(player, "active_mercenaries"):
            player.active_mercenaries = []
        player.active_mercenaries.append(contract)

        rewards = {"mercenary": contract}
        log_msg = f"【傭兵雇用成功】《{name}》と契約！{desc} ({duration}ターン同行)"
        if is_critical:
            log_msg += " エリート傭兵！効果2倍、特殊スキル使用可能！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        economy.aldo_currency -= action.cost_aldo
        log_msg = "【雇用失敗】信用ならない傭兵だった。金だけ持ち逃げされた..."

        evt = presentation.add_event(
            emote_file="emote_cross.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=action.cost_aldo,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


def execute_launder_aldo(
    player: CharacterState,
    economy: SkillEaterEconomySystem,
    facility: BaseFacility,
    action: FacilityAction,
    audio: SkillEaterAudioSystem,
    presentation: SkillEaterPresentationSystem,
    amount: int = 0,
) -> FacilityActionResult:
    """Step 64, 65: アルド洗浄実行"""
    max_launderable = economy.heat_level * 100
    if amount <= 0 or amount > max_launderable:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=f"洗浄可能額: 1〜{max_launderable} アルド (警戒度×100)。指定額が無効です。",
        )

    can_afford, msg = can_afford_action(player, economy, action)
    if not can_afford:
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message=msg,
        )

    player.junk -= action.cost_junk
    player.facility_action_cooldowns[action.id] = action.cost_time_turns

    rate = calculate_success_rate(facility, player, action)
    is_success = random.random() < rate
    is_critical = is_success and random.random() < 0.05 and rate > 0.90

    sounds = [action.audio_file]
    events = []

    if is_success:
        fee_rate = 0.10 if is_critical else 0.20
        cleaned = int(amount * (1 - fee_rate))
        economy.heat_level = max(0, economy.heat_level - (amount // 100))
        economy.aldo_currency += cleaned

        if is_critical:
            economy.factions["broker"].reputation = min(100, economy.factions["broker"].reputation + 10)

        rewards = {"cleaned_aldo": cleaned, "fee_paid": amount - cleaned, "heat_reduction": amount // 100}
        log_msg = f"【マネロン成功】{amount}アルド洗浄→手数料{int(fee_rate*100)}%差引{cleaned}アルド獲得。警戒度-{amount//100}"
        if is_critical:
            log_msg += " ブローカー好感度+10！"

        evt = presentation.add_event(
            emote_file=action.emote_file,
            audio_file=action.success_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.success_audio)
        audio.play_sound("handleCoins2.ogg")
        sounds.append("handleCoins2.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=True,
            is_critical=is_critical,
            consumed_junk=action.cost_junk,
            consumed_aldo=0,
            consumed_time=action.cost_time_turns,
            rewards=rewards,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )
    else:
        economy.heat_level += 20
        log_msg = "【洗浄失敗】洗浄ルートがマークされていた！アルド没収、警戒度+20！"

        evt = presentation.add_event(
            emote_file="emote_alert.png",
            audio_file=action.failure_audio,
            message=log_msg,
        )
        events.append(evt)
        sounds.append(action.failure_audio)
        audio.play_sound("doorClose_1.ogg")
        sounds.append("doorClose_1.ogg")
        audio.play_sound("metalLatch.ogg")
        sounds.append("metalLatch.ogg")

        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            consumed_junk=action.cost_junk,
            consumed_aldo=amount,
            consumed_time=action.cost_time_turns,
            log_message=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )


# ============================================================
# Helper Functions
# ============================================================

def get_available_servants(servant_system) -> list:
    return list(servant_system.servant_party.values())


def get_hostile_factions(economy: SkillEaterEconomySystem) -> list[FactionState]:
    return [f for f in economy.factions.values() if f.is_hostile]


def apply_raid_bonus(economy: SkillEaterEconomySystem, target_id: str):
    if hasattr(economy, "raid_plans") and economy.raid_plans.get(target_id):
        return True
    return False


# ============================================================
# Facade System - Main Entry Point
# ============================================================

class SkillEaterFacilitySystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        economy: SkillEaterEconomySystem | None = None,
        servant_system = None,
        synthesis_system = None,
        combat_system = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.economy = economy or SkillEaterEconomySystem(self.registry)
        self.servant_system = servant_system
        self.synthesis_system = synthesis_system
        self.combat_system = combat_system
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()

        if audio and not presentation:
            self.presentation.audio_system = audio

        self.action_registry = FacilityActionRegistry.get_instance()

    def execute_action(
        self,
        facility_id: str,
        action_id: str,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        facility = self.economy.base_facilities.get(facility_id)
        if not facility:
            return FacilityActionResult(
                action_id=action_id,
                facility_name="Unknown",
                success=False,
                log_message=f"施設 {facility_id} が存在しません。",
            )

        action = self.action_registry.get_action(action_id)
        if not action:
            return FacilityActionResult(
                action_id=action_id,
                facility_name=facility.name,
                success=False,
                log_message=f"アクション {action_id} が存在しません。",
            )

        if action.facility_id != facility_id:
            return FacilityActionResult(
                action_id=action_id,
                facility_name=facility.name,
                success=False,
                log_message=f"このアクションは {facility.name} では実行できません。",
            )

        return self._dispatch_action(facility, action, player, **kwargs)

    def _dispatch_action(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if facility.id == "workshop":
            return self._execute_workshop(facility, action, player, **kwargs)
        elif facility.id == "lab":
            return self._execute_lab(facility, action, player, **kwargs)
        elif facility.id == "medbay":
            return self._execute_medbay(facility, action, player, **kwargs)
        elif facility.id == "command":
            return self._execute_command(facility, action, player, **kwargs)
        elif facility.id == "bar":
            return self._execute_bar(facility, action, player, **kwargs)
        else:
            return FacilityActionResult(
                action_id=action.id,
                facility_name=facility.name,
                success=False,
                log_message=f"未対応の施設: {facility.id}",
            )

    def _execute_workshop(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if action.id == "craft_implant":
            return execute_craft_implant(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "repair_gear":
            return execute_repair_gear(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "install_cybernetic":
            return execute_install_cybernetic(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="未実装のアクションです。",
        )

    def _execute_lab(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if action.id == "analyze_skill_crystal":
            return execute_analyze_skill_crystal(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "reverse_engineer_tech":
            return execute_reverse_engineer_tech(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "develop_countermeasure":
            boss_id = kwargs.get("boss_id", "midas_ceo")
            return execute_develop_countermeasure(
                player, self.economy, facility, action, self.audio, self.presentation, boss_id
            )
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="未実装のアクションです。",
        )

    def _execute_medbay(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if action.id == "treat_toxicity":
            return execute_treat_toxicity(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "augment_servant":
            servant_id = kwargs.get("servant_id")
            if not servant_id:
                return FacilityActionResult(
                    action_id=action.id,
                    facility_name=facility.name,
                    success=False,
                    log_message="従属者IDが指定されていません。",
                )
            return execute_augment_servant(
                player, self.economy, facility, action, self.audio, self.presentation,
                self.servant_system, servant_id
            )
        elif action.id == "memory_wipe":
            return execute_memory_wipe(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="未実装のアクションです。",
        )

    def _execute_command(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if action.id == "dispatch_squad":
            mission_type = kwargs.get("mission_type", "scavenge")
            return execute_dispatch_squad(
                player, self.economy, facility, action, self.audio, self.presentation, mission_type
            )
        elif action.id == "plan_raid":
            target_id = kwargs.get("target_id", "midas_branch")
            return execute_plan_raid(
                player, self.economy, facility, action, self.audio, self.presentation, target_id
            )
        elif action.id == "negotiate_truce":
            faction_id = kwargs.get("faction_id", "midas")
            return execute_negotiate_truce(
                player, self.economy, facility, action, self.audio, self.presentation, faction_id
            )
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="未実装のアクションです。",
        )

    def _execute_bar(
        self,
        facility: BaseFacility,
        action: FacilityAction,
        player: CharacterState,
        **kwargs
    ) -> FacilityActionResult:
        if action.id == "gather_intel":
            return execute_gather_intel(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "hire_mercenary":
            return execute_hire_mercenary(
                player, self.economy, facility, action, self.audio, self.presentation
            )
        elif action.id == "launder_aldo":
            amount = kwargs.get("amount", 0)
            return execute_launder_aldo(
                player, self.economy, facility, action, self.audio, self.presentation, amount
            )
        return FacilityActionResult(
            action_id=action.id,
            facility_name=facility.name,
            success=False,
            log_message="未実装のアクションです。",
        )

    def get_available_actions(self, facility_id: str) -> list[FacilityAction]:
        facility = self.economy.base_facilities.get(facility_id)
        if not facility:
            return []
        return self.action_registry.get_actions_by_facility(facility_id)

    def get_facility(self, facility_id: str) -> BaseFacility | None:
        return self.economy.base_facilities.get(facility_id)

    def decrease_cooldowns(self, player: CharacterState):
        for action_id in list(player.facility_action_cooldowns.keys()):
            player.facility_action_cooldowns[action_id] -= 1
            if player.facility_action_cooldowns[action_id] <= 0:
                del player.facility_action_cooldowns[action_id]
