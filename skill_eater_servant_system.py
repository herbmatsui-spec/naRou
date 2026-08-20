"""
skill_eater_servant_system.py
Aの世界（スキル喰い） Phase 4: 従属システム（使い捨てオートタレット化）
提案6: 従属者移植・治癒・自壊のEmote & Audio演出 (Steps 41〜43)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from skill_eater_system import (
    SkillEaterRegistry,
    SkillDef,
    CharacterState
)
from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem, PresentationEvent


@dataclass
class ServantCharacter:
    id: str
    original_name: str
    custom_name: str
    state: CharacterState
    duration_turns: int = 3  # 寿命（残り行動ターン数）
    assigned_role: str = "Turret"

    def get_skill_count(self) -> int:
        return len(self.state.skills)


@dataclass
class ServantActionResult:
    servant_id: str
    servant_name: str
    action_type: str  # 'ATTACK', 'SKILL', 'CRUMBLE', 'PASS'
    skill_used_id: Optional[str]
    skill_used_name: Optional[str]
    target_id: str
    damage: int = 0
    heal: int = 0
    log_message: str = ""
    is_crumbled: bool = False
    played_sounds: List[str] = field(default_factory=list)
    presentation_events: List[PresentationEvent] = field(default_factory=list)


class SkillEaterServantSystem:
    def __init__(
        self,
        registry: Optional[SkillEaterRegistry] = None,
        audio: Optional[SkillEaterAudioSystem] = None,
        presentation: Optional[SkillEaterPresentationSystem] = None
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        if audio and not presentation:
            self.presentation.audio_system = audio
        self.servant_party: Dict[str, ServantCharacter] = {}

    def capture_husk(self, husk_enemy: CharacterState, custom_name: Optional[str] = None) -> Optional[ServantCharacter]:
        """スキルを奪い尽くしてHusk状態になった敵を捕獲し、使い捨てタレットとして初期化"""
        if not husk_enemy.is_husk:
            return None

        c_name = custom_name or f"従属素体_{husk_enemy.name}"
        servant = ServantCharacter(
            id=f"servant_{husk_enemy.id}",
            original_name=husk_enemy.name,
            custom_name=c_name,
            state=husk_enemy,
            duration_turns=3,
            assigned_role="Turret"
        )
        self.servant_party[servant.id] = servant
        return servant

    def transplant_skill(
        self,
        player: CharacterState,
        servant: ServantCharacter,
        skill_id: str
    ) -> Tuple[bool, str]:
        """Step 41: スキル移植起動 (emote_heart + beltHandle1.ogg)"""
        if not player.has_skill(skill_id):
            return False, "プレイヤーが指定スキルを所持していません。"

        skill_def = self.registry.get_skill(skill_id)
        skill_name = skill_def.name if skill_def else skill_id

        # プレイヤーから消費し素体に注入
        player.remove_skill(skill_id)
        servant.state.add_skill(skill_id)
        servant.state.is_husk = False
        servant.duration_turns = 3

        # Step 41: 移植エモート
        self.presentation.add_event(
            emote_file="emote_heart.png",
            audio_file="beltHandle1.ogg",
            message=f"《{skill_name}》を {servant.custom_name} に注入起動！"
        )

        return True, f"《{skill_name}》を {servant.custom_name} に注入！ 自律オートタレットとして起動！（稼働限界: {servant.duration_turns}ターン）"

    def crumble_servant(self, servant_id: str) -> Optional[ServantCharacter]:
        """Step 43: 自壊・崩壊 (emote_faceSad + cloth3 + creak3)"""
        self.presentation.add_event(
            emote_file="emote_faceSad.png",
            audio_file="cloth3.ogg",
            message="従属者の魔力枯渇による崩壊"
        )
        self.audio.play_sound("creak3.ogg")
        return self.servant_party.pop(servant_id, None)

    def execute_servant_turn(
        self,
        servant: ServantCharacter,
        enemies: List[CharacterState],
        allies: List[CharacterState]
    ) -> ServantActionResult:
        sounds = []
        events = []
        skills = servant.state.get_skill_ids()

        # 1. 回復スキルの場合
        if "com_combat_002" in skills:
            wounded = [a for a in allies if a.hp < a.max_hp * 0.7]
            target = min(wounded, key=lambda a: a.hp) if wounded else (allies[0] if allies else servant.state)
            heal_val = int(servant.state.intelligence * 1.2 + 20)
            target.hp = min(target.max_hp, target.hp + heal_val)

            # Step 42: 回復エモート
            evt_heal = self.presentation.add_event(
                emote_file="emote_hearts.png",
                message=f"{servant.custom_name}の自動治癒（+{heal_val} HP）"
            )
            events.append(evt_heal)

            servant.duration_turns -= 1
            crumbled = servant.duration_turns <= 0
            if crumbled:
                self.crumble_servant(servant.id)
                sounds.extend(["cloth3.ogg", "creak3.ogg"])

            log_msg = f"{servant.custom_name}が自動治癒を発動！ {target.name}を {heal_val} 回復！ (残稼働: {max(0, servant.duration_turns)}T)"
            if crumbled:
                log_msg += f" ➔ エネルギー枯渇により {servant.custom_name} は塵となって崩壊した。"

            return ServantActionResult(
                servant_id=servant.id,
                servant_name=servant.custom_name,
                action_type="SKILL",
                skill_used_id="com_combat_002",
                skill_used_name="小ヒール",
                target_id=target.id,
                heal=heal_val,
                log_message=log_msg,
                is_crumbled=crumbled,
                played_sounds=sounds,
                presentation_events=events
            )

        # 2. 攻撃
        if enemies:
            target_enemy = min(enemies, key=lambda e: e.hp)
            dmg = max(1, servant.state.atk - (target_enemy.defense // 2))
            target_enemy.hp = max(0, target_enemy.hp - dmg)

            evt_atk = self.presentation.add_event(
                emote_file="emote_heartBroken.png",
                message=f"{servant.custom_name}の一斉掃射（{dmg} ダメージ）"
            )
            events.append(evt_atk)

            servant.duration_turns -= 1
            crumbled = servant.duration_turns <= 0
            if crumbled:
                self.crumble_servant(servant.id)
                sounds.extend(["cloth3.ogg", "creak3.ogg"])

            log_msg = f"{servant.custom_name}の自律一斉射撃！ {target_enemy.name}に {dmg} のダメージ！ (残稼働: {max(0, servant.duration_turns)}T)"
            if crumbled:
                log_msg += f" ➔ 魔力回路が焼き切れ、{servant.custom_name} は粉々に自壊した。"

            return ServantActionResult(
                servant_id=servant.id,
                servant_name=servant.custom_name,
                action_type="ATTACK",
                skill_used_id=None,
                skill_used_name=None,
                target_id=target_enemy.id,
                damage=dmg,
                log_message=log_msg,
                is_crumbled=crumbled,
                played_sounds=sounds,
                presentation_events=events
            )

        servant.duration_turns -= 1
        crumbled = servant.duration_turns <= 0
        if crumbled:
            self.crumble_servant(servant.id)
            sounds.extend(["cloth3.ogg", "creak3.ogg"])

        return ServantActionResult(
            servant_id=servant.id,
            servant_name=servant.custom_name,
            action_type="PASS",
            skill_used_id=None,
            skill_used_name=None,
            target_id="",
            log_message=f"{servant.custom_name}は待機している。(残稼働: {max(0, servant.duration_turns)}T)",
            is_crumbled=crumbled,
            played_sounds=sounds,
            presentation_events=events
        )
