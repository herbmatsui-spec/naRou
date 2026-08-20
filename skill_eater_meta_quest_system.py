"""
skill_eater_meta_quest_system.py
Aの世界（スキル喰い）
Phase 6 (クエスト＆改善案5: 複数解法メタ特効)
Phase 7 (改善案6: コスト消費型法則書き換え) + 演出 (Steps 60, 61: emote_exclamations/stars + bookFlip3, metalPot3)
Phase 8 (改善案7: 世界の初期値変動＆輪廻転生) + 演出 (Steps 62, 63: emote_cross/heart + doorClose_3, bookClose, doorOpen_2)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import (
    SkillEaterPresentationSystem,
)
from skill_eater_system import CharacterState, SkillEaterRegistry, SkillTier

# ----------------------------------------------------
# Phase 7 & 改善案6: コスト消費型法則書き換えエンジン (Rule Override System)
# ----------------------------------------------------


class GlobalRuleEngine:
    _instance: Optional["GlobalRuleEngine"] = None

    def __init__(
        self,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        if audio and not presentation:
            self.presentation.audio_system = audio
        self.root_access_granted: bool = False
        self.damage_multiplier: float = 1.0
        self.devour_success_rate_override: float | None = None
        self.is_boss_instant_kill_enabled: bool = True
        self.alchemy_gold_multiplier: float = 1.0
        self.override_count: int = 0

    @classmethod
    def get_instance(cls) -> "GlobalRuleEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset_rules(self):
        self.root_access_granted = False
        self.damage_multiplier = 1.0
        self.devour_success_rate_override = None
        self.is_boss_instant_kill_enabled = True
        self.alchemy_gold_multiplier = 1.0
        self.override_count = 0

    # Step 60, 61: 法則書き換え時の重厚なEmote & Audio演出 (emote_exclamations/stars + bookFlip3 + metalPot3)
    def override_rule(
        self,
        rule_name: str,
        value: Any,
        cost_type: str = "MAX_HP",
        player: CharacterState | None = None,
        available_karma: int = 0,
    ) -> tuple[bool, str, int]:
        if not self.root_access_granted:
            return False, "権限エラー: ROOT権限（マスタースキル）がありません。", 0

        if not hasattr(self, rule_name):
            return False, f"未定義のシステム変数: {rule_name}", 0

        # Step 60: 禁忌の法則書き換え開始
        self.presentation.add_event(
            emote_file="emote_exclamations.png",
            audio_file="bookFlip3.ogg",
            message="【ROOT権限行使】世界の法則構造を展開中...",
        )

        self.override_count += 1
        base_hp_cost = 20 * (2 ** (self.override_count - 1))
        base_karma_cost = 5000 * (2 ** (self.override_count - 1))

        if cost_type == "MAX_HP":
            if not player:
                return False, "プレイヤー実体が必要です。", 0
            if player.max_hp <= base_hp_cost:
                self.override_count -= 1
                return (
                    False,
                    f"生命力不足！ 改変の代償（最大HP -{base_hp_cost}）に耐えられません（現在最大HP: {player.max_hp}）。",
                    0,
                )

            player.max_hp -= base_hp_cost
            player.hp = min(player.hp, player.max_hp)
            setattr(self, rule_name, value)

            # Step 61: 世界改変の確定演出
            self.presentation.add_event(
                emote_file="emote_stars.png",
                audio_file="metalPot3.ogg",
                message=f"世界法則 '{rule_name}' が '{value}' に永久上書きされました！",
            )
            self.audio.play_sound("doorClose_4.ogg")

            return (
                True,
                f"[SYSTEM ROOT] 世界法則 '{rule_name}' を '{value}' に改変！（代償：最大HP -{base_hp_cost} ➔ 残最大HP: {player.max_hp}）",
                0,
            )

        elif cost_type == "KARMA":
            if available_karma < base_karma_cost:
                self.override_count -= 1
                return (
                    False,
                    f"カルマ/資金不足！ 改変には {base_karma_cost} アルド/カルマ が必要です。（所持: {available_karma}）",
                    0,
                )

            setattr(self, rule_name, value)

            # Step 61: 確定演出
            self.presentation.add_event(
                emote_file="emote_stars.png",
                audio_file="metalPot3.ogg",
                message=f"世界法則 '{rule_name}' が '{value}' に永久上書きされました！",
            )
            self.audio.play_sound("doorClose_4.ogg")

            return (
                True,
                f"[SYSTEM ROOT] 世界法則 '{rule_name}' を '{value}' に改変！（消費カルマ: {base_karma_cost}）",
                base_karma_cost,
            )

        return False, "無効なコストタイプです。", 0


# ----------------------------------------------------
# Phase 6 & 改善案5: 複数解法メタ特効システム
# ----------------------------------------------------


@dataclass
class QuestDefinition:
    quest_id: str
    title: str
    phase: int
    description: str
    required_skills: list[str] = field(default_factory=list)
    is_completed: bool = False


class SkillEaterQuestSystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.rule_engine = GlobalRuleEngine.get_instance()
        self.current_phase: int = 1
        self.quests: dict[str, QuestDefinition] = {}
        self._init_quests()

    def _init_quests(self):
        self.quests["q1_0"] = QuestDefinition(
            "q1_0", "適性検査と解雇通知", 1, "スラム街へ逃亡する"
        )
        self.quests["q1_1"] = QuestDefinition(
            "q1_1", "最底辺の生存戦略", 1, "ハンターから《初級剣術》を喰らう"
        )
        self.quests["q2_8"] = QuestDefinition(
            "q2_8",
            "敵対的買収（テイクオーバー）",
            2,
            "ドン・ミダスを打倒し《黄金錬成》を喰らう",
        )
        self.quests["q3_5"] = QuestDefinition(
            "q3_5",
            "バベルの金庫室",
            3,
            "世界銀行頭取を打倒し《マスタースキル》を喰らう",
        )

    def check_boss_meta_counter(
        self, player: CharacterState, boss_id: str
    ) -> tuple[bool, str]:
        if boss_id == "midas_ceo":
            if player.has_skill("rar_gold_body") or player.has_skill(
                "rar_infrared_vision"
            ):
                self.rule_engine.is_boss_instant_kill_enabled = False
                self.presentation.add_event(
                    emote_file="emote_idea.png",
                    audio_file="metalLatch.ogg",
                    message="【メタ特効】合成スキルの周波数共鳴により即死術式中和！",
                )
                return (
                    True,
                    "【メタ攻略成功：スキル共鳴】合成スキルの周波数が《黄金錬成》の即死術式を完全中和しました！",
                )

            if player.defense >= 80:
                self.rule_engine.is_boss_instant_kill_enabled = False
                self.presentation.add_event(
                    emote_file="emote_star.png",
                    audio_file="chop.ogg",
                    message="【メタ特効】圧倒的防御力で金化光線を粉砕！",
                )
                return (
                    True,
                    "【メタ攻略成功：圧倒的肉体】鍛え抜かれた防御力が《黄金錬成》の金化光線を力技で弾き返しました！",
                )

            for s_id in player.get_skill_ids():
                s_def = self.registry.get_skill(s_id)
                if s_def and s_def.tier == SkillTier.COMMON:
                    player.remove_skill(s_id)
                    self.rule_engine.is_boss_instant_kill_enabled = False
                    self.presentation.add_event(
                        emote_file="emote_drop.png",
                        audio_file="dropLeather.ogg",
                        message=f"【身代わり破壊】《{s_def.name}》が身代わりに粉砕！",
                    )
                    return (
                        True,
                        f"【メタ攻略成功：身代わり破壊】《{s_def.name}》が身代わりとなって粉砕され、即死を回避しました！",
                    )

        return False, "メタ対抗策なし。ボスの即死ギミックが有効です。"


# ----------------------------------------------------
# Phase 8 & 改善案7: 世界の初期値変動＆輪廻転生システム
# ----------------------------------------------------


@dataclass
class ReincarnationMetaState:
    loop_count: int = 1
    total_karma_points: int = 0
    unlocked_secrets: list[str] = field(default_factory=list)
    inherited_skill_ids: list[str] = field(default_factory=list)
    devoured_element_counts: dict[str, int] = field(default_factory=dict)
    dominant_element_last_life: str | None = None


class SkillEaterReincarnationSystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.meta_state = ReincarnationMetaState()

    def record_devoured_element(self, element: str | None):
        if element:
            cnt = self.meta_state.devoured_element_counts.get(element, 0)
            self.meta_state.devoured_element_counts[element] = cnt + 1

    def apply_world_modifier(self) -> str:
        dominant = self.meta_state.dominant_element_last_life
        if not dominant:
            return "通常の世界線が展開されています。"

        for s_def in self.registry.get_all_skills():
            if dominant in s_def.tags:
                s_def.market_value = max(100, int(s_def.market_value * 0.5))
            elif (
                dominant == "Fire"
                and "Water" in s_def.tags
                or dominant == "Water"
                and "Fire" in s_def.tags
            ):
                s_def.market_value = int(s_def.market_value * 2.0)

        msg = f"【世界変異観測】前世で【{dominant}】属性スキルが乱獲されたため、この世界では{dominant}スキルの価値が暴落し、対抗属性が高騰しています！"
        return msg

    def process_reincarnation(
        self, player: CharacterState, selected_carryover_skill_ids: list[str]
    ) -> tuple[CharacterState, str]:
        """
        Step 62, 63: 輪廻転生時のEmote & Audio演出 (cross/doorClose_3 ➔ heart/doorOpen_2)
        """
        # Step 62: 世界崩壊・リセット
        self.presentation.add_event(
            emote_file="emote_cross.png",
            audio_file="doorClose_3.ogg",
            message="世界線が崩壊し、記憶がカルマへと昇華...",
        )
        self.audio.play_sound("bookClose.ogg")

        karma_gain = 0
        for s_id in player.get_skill_ids():
            s_def = self.registry.get_skill(s_id)
            if s_def and s_def.market_value > 0:
                karma_gain += s_def.market_value // 100

        self.meta_state.loop_count += 1
        self.meta_state.total_karma_points += karma_gain

        if self.meta_state.devoured_element_counts:
            dominant = max(
                self.meta_state.devoured_element_counts,
                key=self.meta_state.devoured_element_counts.get,
            )
            self.meta_state.dominant_element_last_life = dominant
            self.meta_state.devoured_element_counts.clear()

        world_msg = self.apply_world_modifier()

        new_player = CharacterState(
            id=f"player_loop_{self.meta_state.loop_count}",
            name=f"主人公（第{self.meta_state.loop_count}周目）",
            hp=100 + (self.meta_state.loop_count * 20),
            max_hp=100 + (self.meta_state.loop_count * 20),
            mp=50 + (self.meta_state.loop_count * 10),
            max_mp=50 + (self.meta_state.loop_count * 10),
            atk=10 + self.meta_state.loop_count * 2,
            defense=5 + self.meta_state.loop_count * 2,
            intelligence=15 + self.meta_state.loop_count * 2,
            speed=10,
            analysis_level=1 + (self.meta_state.loop_count // 2),
            max_memory_capacity=10 + self.meta_state.loop_count * 2,
        )

        for c_id in selected_carryover_skill_ids[:3]:
            if player.has_skill(c_id):
                new_player.add_skill(c_id)

        if (
            self.meta_state.loop_count >= 2
            and "first_eater_vault" not in self.meta_state.unlocked_secrets
        ):
            self.meta_state.unlocked_secrets.append("first_eater_vault")

        # Step 63: 新世界開幕
        self.presentation.add_event(
            emote_file="emote_heart.png",
            audio_file="doorOpen_2.ogg",
            message=f"第{self.meta_state.loop_count}周目の世界線へ転生！",
        )
        self.audio.play_sound("footstep00.ogg")

        msg = (
            f"【輪廻転生完了】第{self.meta_state.loop_count}周目へ突入！ "
            f"獲得カルマ: {karma_gain}P, 継承スキル数: {len(new_player.skills)}個\n{world_msg}"
        )
        return new_player, msg
