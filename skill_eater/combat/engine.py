"""
skill_eater_combat_system.py
Aの世界（スキル喰い）の戦闘エンジン＆《喰らい（Devour）》システム
提案2 & 3: 戦闘・喰らい・解析・ハックのEmote & Audio演出 (Steps 9〜24, 45〜47, 57〜59)
Phase 1 Tactical Combat Manager (Phase1CombatManager)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import PresentationEvent, SkillEaterPresentationSystem
from skill_eater_system import (
    CharacterState,
    SkillEaterRegistry,
    SkillEffect,
    SkillTier,
)

# 属性シナジー＆消化不良の定義
SYNERGY_COMBOS: dict[tuple[str, str], tuple[str, int]] = {
    ("Fire", "Wind"): ("【連鎖熱爆発】爆風が業火を巻き込み全体大ダメージ！", 40),
    ("Water", "Ice"): ("【絶対零度凍結】冷気が凝縮し対象を行動不能に追い込む！", 30),
    ("Defense", "Sword"): ("【剛剣両断】守りを力に変え防御貫通の一撃！", 35),
}

INDIGESTION_COMBOS: dict[tuple[str, str], tuple[str, int]] = {
    ("Fire", "Water"): (
        "【消化不良：水蒸気爆破】胃袋の中で反発反応！主人公が自傷ダメージを受けた！",
        25,
    ),
    ("Ice", "Fire"): ("【熱狂ショック】急激な温度変化により拒絶反応！", 20),
}

# 効果式（`formula`）のトークン。数値・`*` `+` `-` だけを受け、eval を使わない。
_FORMULA_TOKENS = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?|[*+\-]")

# 効果式の能力名が指す CharacterState のフィールド。
# `engine/engine.py` の橋渡しが strength→atk / endurance→defense / perception→intelligence で
# 写すのと同じ写し方に揃える。`dex`（器用）に相当する能力は CharacterState に無いため speed を充てる。
_FORMULA_STAT_FIELDS: dict[str, str] = {
    "str": "atk",
    "strength": "atk",
    "atk": "atk",
    "attack": "atk",
    "def": "defense",
    "defense": "defense",
    "defence": "defense",
    "endurance": "defense",
    "int": "intelligence",
    "intelligence": "intelligence",
    "perception": "intelligence",
    "magic": "intelligence",
    "dex": "speed",
    "dexterity": "speed",
    "agility": "speed",
    "speed": "speed",
    "hp": "hp",
    "mp": "mp",
    "max_hp": "max_hp",
    "max_mp": "max_mp",
}

# 即座に実体へ当てられる効果。恒久補正（DamageMod / ResistanceMod / AggroMod など）や、
# 経済・小計・召喚など別システムに依存する効果だけは含めない。
# 含めないものは「実行経路が無い」として拒否またはスキップとして必ず明示する。
EXECUTABLE_EFFECT_TYPES: frozenset[str] = frozenset(
    {"Damage", "Heal", "ApplyStatus", "StatMod"}
)

# 効果の `target` の解釈。World A の戦闘は単独なので `Ally`（味方全体）は唱えた本人に寄せる。
_EFFECT_TARGET_KINDS: dict[str, str] = {
    "self": "self",
    "ally": "self",
    "enemy": "enemy",
    "enemyaoe": "enemy_aoe",
}


def _formula_value(
    formula: str | None, subject: CharacterState, base: float = 0.0
) -> float | None:
    """`"int * 1.8 + 30"` 形式の効果式を `subject` の能力で評価する。

    対応する書式は `<能力> * <係数> [± <定数>]`、`<能力> ± <定数>`、そして先頭が演算子の
    `<係数>` / `±<定数>`（StatMod のように「対象の現在値を*''」に使う形）。
    未知の能力名や空の式は «None» を返し、「実行できない」判定に回す。
    """
    if not formula:
        return None
    tokens = _FORMULA_TOKENS.findall(str(formula))
    if not tokens:
        return None

    acc = float(base)
    pending = "+"  # 先頭に立つ能力名は base への加算として扱う
    for token in tokens:
        if token in {"*", "+", "-"}:
            pending = token
            continue
        try:
            operand = float(token)
        except ValueError:
            field = _FORMULA_STAT_FIELDS.get(token.lower())
            if field is None:
                return None
            operand = float(getattr(subject, field, 0))
        if pending == "*":
            acc *= operand
        elif pending == "+":
            acc += operand
        else:
            acc -= operand
        pending = "+"
    return acc


def _stat_mod_field(effect: SkillEffect) -> str | None:
    """`StatMod` の `stat` が指す CharacterState のフィールド。

    `max_carry_weight` のように CharacterState に無い能力は «None»（実行不可）。
    """
    stat = str(effect.params.get("stat") or "").strip().lower()
    return _FORMULA_STAT_FIELDS.get(stat)


def _resolve_effect_targets(
    effect: SkillEffect, caster: CharacterState, targets: Sequence[CharacterState]
) -> list[CharacterState]:
    """効果の `target` を実際の `CharacterState` へ解決する（空なら実行不可）。"""
    kind = _EFFECT_TARGET_KINDS.get(str(effect.target or "Self").strip().lower())
    if kind == "self":
        return [caster]
    if kind == "enemy":
        return list(targets[:1])
    if kind == "enemy_aoe":
        return list(targets)
    return []


def _clamp_field(character: CharacterState, field: str, value: float) -> int:
    """能力値の変更を World A の既存慣習の範囲へ丸める（HP/MP は上限内、能力値は 1  以上）。"""
    value = int(value)
    if field == "hp":
        return max(0, min(value, character.max_hp))
    if field == "mp":
        return max(0, min(value, character.max_mp))
    if field in {"max_hp", "max_mp"}:
        return max(0, value)
    return max(1, value)


def _character_state_of(entity: Any) -> CharacterState:
    """実体（`ecs.entity.Entity`）を World A の戦闘状態へ写す。

    `engine/engine.py` の `_character_state_from_entity` と同じ写し方だが、同ファイルは
    他作業者の編集対象であり、この戦闘システム側はエンジンに依存せずに自前で持つ。
    """
    attributes = entity.attributes
    return CharacterState(
        id=str(getattr(entity, "id", entity.name)),
        name=entity.name,
        hp=entity.hp,
        max_hp=entity.max_hp,
        mp=entity.mp,
        max_mp=entity.max_mp,
        atk=attributes.strength,
        defense=attributes.endurance,
        intelligence=attributes.perception,
        speed=entity.speed,
        analysis_level=getattr(entity, "analysis_level", 1),
        status_effects=list(getattr(entity, "status_effects", None) or []),
    )


@dataclass
class _CastTally:
    """1 回の詠唱で出た結果。`BattleActionResult` へ移すまで貯めておく。"""

    damage: int = 0
    heal: int = 0
    statuses: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    sounds: list[str] = field(default_factory=list)
    events: list[PresentationEvent] = field(default_factory=list)


@dataclass
class AnalyzedSkillInfo:
    skill_id: str
    name: str
    tier: str
    type: str
    tags: list[str]
    market_value: int | None
    is_weakness_revealed: bool
    flavor_text: str | None = None
    is_encrypted: bool = False


@dataclass
class AnalysisResult:
    target_id: str
    target_name: str
    target_hp_ratio: float
    analysis_level: int
    revealed_skills: list[AnalyzedSkillInfo]
    weaknesses: list[str]
    devour_success_rate: float
    hologram_visual_mode: str
    system_log: str
    synergy_hint: str | None = None
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[PresentationEvent] = field(default_factory=list)


@dataclass
class BattleActionResult:
    action_type: str  # 'ATTACK', 'SKILL', 'DEVOUR', 'ANALYZE', 'HACK', 'DISCARD'
    actor_name: str
    target_name: str
    success: bool
    damage_dealt: int = 0
    heal_amount: int = 0
    stolen_skill_id: str | None = None
    stolen_skill_name: str | None = None
    status_applied: list[str] = field(default_factory=list)
    log_messages: list[str] = field(default_factory=list)
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[PresentationEvent] = field(default_factory=list)  # Step 9: 演出リスト


class SkillEaterCombatSystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        # プレイヤーの永続呪術帳。kernel に登録されたこのインスタンスがラン中 1 個なので、
        # ここに置いた CharacterState はそのまま「跨ぎ越える呪術帳」になる。
        self._spellbook: CharacterState | None = None

    def calculate_devour_rate(self, analyzer: CharacterState, target: CharacterState) -> float:
        base_rate = 0.60
        analysis_bonus = analyzer.analysis_level * 0.05
        hp_loss_ratio = 1.0 - (target.hp / max(1, target.max_hp))
        hp_bonus = hp_loss_ratio * 0.50

        total_rate = base_rate + analysis_bonus + hp_bonus

        if "Paralyzed" in target.status_effects or "Sleep" in target.status_effects:
            total_rate += 0.20

        return max(0.05, min(1.0, round(total_rate, 2)))

    def analyze_target(self, analyzer: CharacterState, target: CharacterState) -> AnalysisResult:
        """Step 17〜19: 解析実行時のEmote & Audio演出 (dots3/metalClick, idea/metalLatch, question)"""
        lv = analyzer.analysis_level
        revealed_skills: list[AnalyzedSkillInfo] = []
        weaknesses: list[str] = []
        sounds: list[str] = []
        events: list[PresentationEvent] = []

        # Step 17: 解析スキャン中
        evt_scan = self.presentation.add_event(
            emote_file="emote_dots3.png",
            audio_file="metalClick.ogg",
            message="対象の構造を解析中...",
        )
        sounds.append("metalClick.ogg")
        events.append(evt_scan)

        if lv < 3:
            visual_mode = "BASIC"
        elif lv < 7:
            visual_mode = "DEEP"
        else:
            visual_mode = "EXPLOIT"
            # Step 18: 完全解析完了
            evt_exp = self.presentation.add_event(
                emote_file="emote_idea.png",
                audio_file="metalLatch.ogg",
                message="弱点および構造の完全解析に成功！",
            )
            sounds.append("metalLatch.ogg")
            events.append(evt_exp)

        synergy_hint = None
        last_elem = analyzer.last_devoured_element

        for skill_id in target.get_skill_ids():
            skill_def = self.registry.get_skill(skill_id)
            if not skill_def:
                continue

            if skill_def.is_encrypted and not target.encryption_broken:
                # Step 19: 暗号化スキル検出
                evt_enc = self.presentation.add_event(
                    emote_file="emote_question.png",
                    message="暗号化されたプロテクトスキルを検出",
                )
                events.append(evt_enc)
                revealed_skills.append(
                    AnalyzedSkillInfo(
                        skill_id=skill_def.id,
                        name="【暗号化プロテクト中】",
                        tier="???",
                        type="???",
                        tags=["[ENCRYPTED]"],
                        market_value=None,
                        is_weakness_revealed=False,
                        flavor_text="暗号化された高位スキル。ハッキング（execute_hack）で開示可能。",
                        is_encrypted=True,
                    )
                )
                continue

            can_see_full = False
            if (
                lv >= 7
                or lv >= 3
                and skill_def.tier in [SkillTier.COMMON, SkillTier.RARE]
                or lv < 3
                and skill_def.tier == SkillTier.COMMON
            ):
                can_see_full = True

            market_val = skill_def.market_value if can_see_full else None
            flavor = skill_def.flavor_text if can_see_full else "???"

            if "Fire" in skill_def.tags and "Ice" not in weaknesses:
                weaknesses.append("Water/Ice")
            if "Defense" in skill_def.tags and "ArmorPierce" not in weaknesses:
                weaknesses.append("Magic/ArmorPierce")

            if last_elem and not synergy_hint:
                for tag in skill_def.tags:
                    if (last_elem, tag) in SYNERGY_COMBOS:
                        synergy_hint = (
                            f"★シナジー予測: 前回【{last_elem}】× 今回【{tag}】➔ 大爆発チャンス！"
                        )
                        break
                    elif (last_elem, tag) in INDIGESTION_COMBOS:
                        synergy_hint = (
                            f"▲消化不良警告: 前回【{last_elem}】× 今回【{tag}】➔ 自傷リスク！"
                        )
                        break

            revealed_skills.append(
                AnalyzedSkillInfo(
                    skill_id=skill_def.id,
                    name=skill_def.name if (can_see_full or lv >= 2) else "???",
                    tier=skill_def.tier.value if (can_see_full or lv >= 2) else "???",
                    type=skill_def.type.value if can_see_full else "???",
                    tags=skill_def.tags if can_see_full else [],
                    market_value=market_val,
                    is_weakness_revealed=can_see_full,
                    flavor_text=flavor,
                    is_encrypted=False,
                )
            )

        devour_rate = self.calculate_devour_rate(analyzer, target)
        hp_ratio = round(target.hp / max(1, target.max_hp), 2)

        log_msg = f"[SCAN] 対象 '{target.name}' の構造解析完了。(解析Lv.{lv}, 検出: {len(revealed_skills)}個, 喰らい成功率: {int(devour_rate * 100)}%)"

        return AnalysisResult(
            target_id=target.id,
            target_name=target.name,
            target_hp_ratio=hp_ratio,
            analysis_level=lv,
            revealed_skills=revealed_skills,
            weaknesses=weaknesses if lv >= 3 else ["??? (解析Lv3で解放)"],
            devour_success_rate=devour_rate,
            hologram_visual_mode=visual_mode,
            system_log=log_msg,
            synergy_hint=synergy_hint,
            played_sounds=sounds,
            presentation_events=events,
        )

    # Steps 17〜21: 解析ハッキングコマンド＆暗号解除オブザーバー
    def execute_analysis_hack(
        self, analyzer: CharacterState, target: CharacterState
    ) -> AnalysisResult:
        """Step 17〜19: 敵の暗号化・偽装・解除条件をハッキングスキャン"""
        lv = analyzer.analysis_level
        revealed_skills: list[AnalyzedSkillInfo] = []
        weaknesses: list[str] = []
        sounds: list[str] = []
        events: list[PresentationEvent] = []

        evt_scan = self.presentation.add_event(
            emote_file="emote_dots3.png",
            audio_file="metalClick.ogg",
            message="【解析ハック】対象のセキュリティ・アイスをスキャン中...",
        )
        sounds.append("metalClick.ogg")
        events.append(evt_scan)

        unlocked_count = 0
        for skill_id, slot in list(target.skills.items()):
            # Step 23: 偽装（ミミック）解除判定
            if slot.is_disguised and (lv >= 3 or random.random() < 0.6):
                slot.is_disguised = False
                if slot.real_skill_id:
                    real_def = self.registry.get_skill(slot.real_skill_id)
                    real_name = real_def.name if real_def else slot.real_skill_id
                    events.append(
                        self.presentation.add_event(
                            emote_file="emote_idea.png",
                            message=f"【偽装看破！】隠された真のスキル《{real_name}》を暴いた！",
                        )
                    )

            s_def = self.registry.get_skill(
                slot.real_skill_id if not slot.is_disguised and slot.real_skill_id else skill_id
            )
            if not s_def:
                continue

            cond_hints = []
            if slot.unlock_conditions:
                for c in slot.unlock_conditions:
                    c_type = c.get("type", "element")
                    if c_type == "element":
                        cond_hints.append(f"属性【{c.get('element')}】攻撃")
                    elif c_type == "critical":
                        cond_hints.append("クリティカル直撃")
                    elif c_type == "status":
                        cond_hints.append(f"状態異常【{c.get('status')}】")

            hint_str = " / ".join(cond_hints) if cond_hints else "直接ハックまたは高威力攻撃"

            revealed_skills.append(
                AnalyzedSkillInfo(
                    skill_id=s_def.id,
                    name=s_def.name,
                    tier=s_def.tier.value,
                    type=s_def.type.value,
                    tags=s_def.tags,
                    market_value=s_def.market_value,
                    is_weakness_revealed=True,
                    flavor_text=f"[解除条件: {hint_str}] {s_def.flavor_text}",
                    is_encrypted=slot.is_encrypted,
                )
            )

        devour_rate = self.calculate_devour_rate(analyzer, target)
        hp_ratio = round(target.hp / max(1, target.max_hp), 2)
        log_msg = f"[HACK SCAN] 対象 '{target.name}' の暗号化解析完了。（解析Lv.{lv}, スキル数: {len(revealed_skills)}, 喰らい成功率: {int(devour_rate * 100)}%）"

        return AnalysisResult(
            target_id=target.id,
            target_name=target.name,
            target_hp_ratio=hp_ratio,
            analysis_level=lv,
            revealed_skills=revealed_skills,
            weaknesses=(
                ["暗号プロテクト検出"]
                if any(s.is_encrypted for s in target.skills.values())
                else ["プロテクトなし"]
            ),
            devour_success_rate=devour_rate,
            hologram_visual_mode="EXPLOIT" if lv >= 5 else "DEEP",
            system_log=log_msg,
            played_sounds=sounds,
            presentation_events=events,
        )

    def check_and_unlock_conditions(
        self,
        attacker: CharacterState,
        defender: CharacterState,
        action_element: str | None = None,
        is_critical: bool = False,
        status_applied: str | None = None,
    ) -> list[str]:
        """Step 20, 21: 戦闘中の攻撃属性やクリティカル等で条件を満たしたか判定し暗号を解除"""
        unlocked_logs = []
        for s_id, slot in defender.skills.items():
            if not slot.is_encrypted:
                continue

            matched = False
            for cond in slot.unlock_conditions:
                c_type = cond.get("type")
                if (
                    c_type == "element"
                    and action_element
                    and cond.get("element", "").lower() == action_element.lower()
                ):
                    matched = True
                elif c_type == "critical" and is_critical:
                    matched = True
                elif (
                    c_type == "status"
                    and status_applied
                    and cond.get("status", "").lower() == status_applied.lower()
                ):
                    matched = True

            if matched:
                slot.is_encrypted = False
                s_def = self.registry.get_skill(s_id)
                s_name = s_def.name if s_def else s_id
                unlocked_logs.append(
                    f"【プロテクト解除！】{defender.name}の《{s_name}》の暗号化障壁が破壊された！"
                )
                self.presentation.add_event(
                    emote_file="emote_idea.png",
                    audio_file="metalLatch.ogg",
                    message=f"《{s_name}》プロテクト解除！",
                )

        return unlocked_logs

    # Step 57〜59: ハッキング実行コマンド（Emote & Audio演出）
    def execute_hack(
        self,
        analyzer: CharacterState,
        target: CharacterState,
        force_success: bool | None = None,
    ) -> BattleActionResult:
        sounds = []
        events = []
        # Step 57: タイピング・クラッキング音
        evt1 = self.presentation.add_event(
            emote_file="emote_dots3.png",
            audio_file="metalClick.ogg",
            message="プロテクト防壁へ侵入中...",
        )
        sounds.extend(["metalClick.ogg", "metalClick.ogg"])
        events.append(evt1)

        hack_chance = min(0.95, 0.40 + (analyzer.intelligence * 0.02))
        is_success = (
            force_success if force_success is not None else (random.random() <= hack_chance)
        )

        if is_success:
            target.encryption_broken = True
            # Step 58: ハック成功
            evt_ok = self.presentation.add_event(
                emote_file="emote_idea.png",
                audio_file="metalLatch.ogg",
                message="防壁突破！ 真のデータを開示！",
            )
            sounds.extend(["metalLatch.ogg", "bookOpen.ogg"])
            events.append(evt_ok)

            return BattleActionResult(
                action_type="HACK",
                actor_name=analyzer.name,
                target_name=target.name,
                success=True,
                log_messages=[
                    f"【ハック成功！】{analyzer.name}は{target.name}の防壁を突破！ 真のデータ構造を開示しました！"
                ],
                played_sounds=sounds,
                presentation_events=events,
            )
        else:
            analyzer.intelligence = max(1, analyzer.intelligence - 3)
            # Step 59: ハック失敗・知力ダウン
            evt_fail = self.presentation.add_event(
                emote_file="emote_swirl.png",
                audio_file="creak2.ogg",
                message="逆探知カウンター！",
            )
            sounds.append("creak2.ogg")
            events.append(evt_fail)

            return BattleActionResult(
                action_type="HACK",
                actor_name=analyzer.name,
                target_name=target.name,
                success=False,
                log_messages=[
                    f"【ハック失敗…】逆探知カウンターを受け、{analyzer.name}の知力が一時的に低下した！"
                ],
                played_sounds=sounds,
                presentation_events=events,
            )

    # Steps 7〜11: オーバークロック脳焼きダメージ＆UIグリッチ演出
    def apply_overclock_damage(
        self, character: CharacterState
    ) -> tuple[int, list[str], list[PresentationEvent]]:
        character.calculate_memory_usage()
        if character.overclock_level <= 0:
            return 0, [], []

        damage_pct = min(character.overclock_level * 0.5, 50.0)
        actual_damage = max(1, int(character.max_hp * (damage_pct / 100.0)))
        character.hp = max(0, character.hp - actual_damage)

        glitch_intensity = min(character.overclock_level / 100.0, 1.0)
        logs = [
            f"【脳焼き警告】メモリ超過（{character.overclock_level}%）により大脳皮質に負荷！ {actual_damage} の自傷ダメージ！"
        ]

        evt_glitch = self.presentation.add_event(
            emote_file="emote_swirl.png",
            audio_file="creak3.ogg",
            message=f"【UIグリッチ】脳負荷過大 (超過率 {character.overclock_level}%)",
        )
        events = [evt_glitch]

        if character.overclock_level >= 150:
            fry_dmg, fry_msg, fry_evts = self.trigger_fatal_brain_fry(character)
            logs.append(fry_msg)
            events.extend(fry_evts)

        return actual_damage, logs, events

    def trigger_fatal_brain_fry(
        self, character: CharacterState
    ) -> tuple[int, str, list[PresentationEvent]]:
        """Step 11: 150%以上で致命的脳過熱"""
        character.hp = 0
        evt_fatal = self.presentation.add_event(
            emote_file="emote_cross.png",
            audio_file="metalPot1.ogg",
            message="【致命的脳過熱】脳内回路が完全に焼き切れ、意識を喪失した！",
        )
        return (
            character.max_hp,
            "【致命的過熱】メモリ許容量150%超過により脳回路が完全破壊されました！",
            [evt_fatal],
        )

    # Step 45: スキル任意破棄コマンド（Emote: emote_drop.png）
    def discard_skill(
        self, character: CharacterState, skill_id: str
    ) -> tuple[bool, str, list[str], list[PresentationEvent]]:
        if not character.has_skill(skill_id):
            return False, "所持していないスキルです。", [], []

        s_def = self.registry.get_skill(skill_id)
        s_name = s_def.name if s_def else skill_id

        character.remove_skill(skill_id)
        character.addiction_buildup = max(0, character.addiction_buildup - 20)
        character.calculate_memory_usage()

        evt = self.presentation.add_event(
            emote_file="emote_drop.png",
            audio_file="dropLeather.ogg",
            message=f"《{s_name}》を脳内メモリから消去",
        )

        return (
            True,
            f"《{s_name}》を脳内メモリから消去しました。（空きメモリ増加、精神侵食度 -20 ➔ {character.addiction_buildup}）",
            ["dropLeather.ogg"],
            [evt],
        )

    # Step 23, 24: 喰らいシナジー＆消化不良の判定（Emote: emote_exclamations / emote_swirl）
    def evaluate_devour_combo(
        self,
        predator: CharacterState,
        prey: CharacterState,
        devoured_element: str | None,
    ) -> tuple[int, int, list[str], list[str], list[PresentationEvent]]:
        bonus_dmg = 0
        indigestion_dmg = 0
        logs = []
        sounds = []
        events = []

        last_elem = predator.last_devoured_element
        if last_elem and devoured_element:
            pair = (last_elem, devoured_element)
            if pair in SYNERGY_COMBOS:
                desc, dmg = SYNERGY_COMBOS[pair]
                bonus_dmg = dmg
                prey.hp = max(0, prey.hp - bonus_dmg)
                logs.append(f"{desc} （{prey.name}に追加 {bonus_dmg} ダメージ！）")
                # Step 23: シナジー爆発
                evt_syn = self.presentation.add_event(
                    emote_file="emote_exclamations.png",
                    audio_file="metalPot1.ogg",
                    message="属性連鎖シナジー爆発！",
                )
                sounds.append("metalPot1.ogg")
                events.append(evt_syn)
            elif pair in INDIGESTION_COMBOS:
                desc, dmg = INDIGESTION_COMBOS[pair]
                indigestion_dmg = dmg
                predator.hp = max(1, predator.hp - indigestion_dmg)
                logs.append(f"{desc} （{predator.name}は {indigestion_dmg} の自傷ダメージ！）")
                # Step 24: 消化不良
                evt_indig = self.presentation.add_event(
                    emote_file="emote_swirl.png",
                    audio_file="creak3.ogg",
                    message="胃袋での反発反応（消化不良）！",
                )
                sounds.append("creak3.ogg")
                events.append(evt_indig)

        predator.last_devoured_element = devoured_element
        return bonus_dmg, indigestion_dmg, logs, sounds, events

    # Step 11〜15: 基本通常攻撃（Emote: heartBroken, cross, drop）
    def execute_basic_attack(
        self, attacker: CharacterState, defender: CharacterState
    ) -> BattleActionResult:
        sounds = []
        events = []
        raw_damage = max(1, attacker.atk - (defender.defense // 2))

        if defender.has_skill("rar_combat_012") or defender.defense >= 30:
            raw_damage = max(1, int(raw_damage * 0.7))
            self.audio.play_sound("chop.ogg")
            sounds.append("chop.ogg")
        else:
            slice_se = random.choice(["knifeSlice.ogg", "knifeSlice2.ogg"])
            self.audio.play_sound(slice_se)
            sounds.append(slice_se)

        defender.hp = max(0, defender.hp - raw_damage)
        logs = [f"{attacker.name}の通常攻撃！ {defender.name}に {raw_damage} のダメージ！"]

        # Step 11: 被弾エモート
        evt_hit = self.presentation.add_event(
            emote_file="emote_heartBroken.png",
            message=f"{defender.name}に {raw_damage} ダメージ！",
        )
        events.append(evt_hit)

        if defender.hp == 0:
            logs.append(f"{defender.name}は倒れた！")
            # Step 13: 撃破エモート
            evt_dead = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="dropLeather.ogg",
                message=f"{defender.name}は戦闘不能になった",
            )
            sounds.append("dropLeather.ogg")
            events.append(evt_dead)

        return BattleActionResult(
            action_type="ATTACK",
            actor_name=attacker.name,
            target_name=defender.name,
            success=True,
            damage_dealt=raw_damage,
            log_messages=logs,
            played_sounds=sounds,
            presentation_events=events,
        )

    # --- 詠唱（喰らいで得た技を使う） ---
    def player_spellbook(self, entity: Any) -> CharacterState:
        """プレイヤーの永続呪術帳。ラン中 1 個だけ持ち続ける `CharacterState`。

        `Engine.execute_devour()` は奪取した id を `player.skills`（ECS 側の所有辞書）へ書く。
        そちらは所有者の入れ物で詠唱の経路を持たないため、初回参照時に id を
        `CharacterState.skills`（World A が実際に唱える場所）へ載せ替え、以降は同じ
        インスタンスを返し続ける。HP / MP / 能力値は毎回 Entity から取り直す。
        """
        spellbook = self._spellbook
        if spellbook is None:
            attributes = entity.attributes
            spellbook = CharacterState(
                id="player",
                name=entity.name,
                hp=entity.hp,
                max_hp=entity.max_hp,
                mp=entity.mp,
                max_mp=entity.max_mp,
                atk=attributes.strength,
                defense=attributes.endurance,
                intelligence=attributes.perception,
                speed=entity.speed,
            )
            self._spellbook = spellbook

        attributes = entity.attributes
        spellbook.name = entity.name
        spellbook.hp = entity.hp
        spellbook.max_hp = entity.max_hp
        spellbook.mp = entity.mp
        spellbook.max_mp = entity.max_mp
        spellbook.atk = attributes.strength
        spellbook.defense = attributes.endurance
        spellbook.intelligence = attributes.perception
        spellbook.speed = entity.speed
        spellbook.analysis_level = getattr(entity, "analysis_level", 1)

        for owned_id in getattr(entity, "skills", None) or {}:
            skill_id = str(owned_id)
            if skill_id in spellbook.skills:
                continue
            if self.registry.get_skill(skill_id) is None:
                # 主人公既定の格闘・短剣など World A カタログに無い id は唱えられない。
                # `Engine._register_devoured_skill` も同じ理由でこのような id を記録しない。
                # 載せれば記憶容量を消費するだけなので、呪術帳には入れない。
                continue
            # 記憶容量の可否は execute_devour 側が判断済み。ここでは使用メモリ(MB)を
            # 反映させ、overclock_level として process_turn_end の脳焼きに載せる。
            spellbook.add_skill(skill_id, ignore_capacity=True)
        return spellbook

    def cast_skill(
        self,
        caster: CharacterState,
        skill_id: str,
        targets: Sequence[CharacterState] = (),
    ) -> BattleActionResult:
        """`caster` が `skill_id` を唱える。魔力とクールダウンを払い、効果を実体へ当てる。

        唱えられない場合は魔力もクールダウンも消費しない。効果のうち実行経路が無いものは
        黙って捨てず、「何が Didn't run」をログに必ず残す。
        """
        target_list = list(targets)
        target_name = target_list[0].name if target_list else caster.name
        s_def = self.registry.get_skill(skill_id)

        if s_def is None:
            return self._cast_refusal(
                caster, target_name, f"《{skill_id}》の定義が無く唱えられない。"
            )

        skill_name = s_def.name

        if not caster.has_skill(skill_id):
            return self._cast_refusal(
                caster, target_name, f"《{skill_name}》は呪術帳に載っていない。"
            )

        slot = caster.skills[skill_id]

        if slot.is_encrypted:
            return self._cast_refusal(
                caster,
                target_name,
                f"《{skill_name}》は暗号化ステップで解読されていない。",
                emote="emote_question.png",
                audio="metalClick.ogg",
            )

        if slot.current_cooldown > 0:
            return self._cast_refusal(
                caster,
                target_name,
                f"《{skill_name}》はクールダウン中（残り {slot.current_cooldown} ターン）。",
            )

        if not any(self._can_apply(e, caster, target_list) for e in s_def.effects):
            unsupported = ", ".join(dict.fromkeys(e.effect_type for e in s_def.effects))
            return self._cast_refusal(
                caster,
                target_name,
                f"《{skill_name}》を唱える実行経路が無い（未対応の効果: {unsupported or '(効果宣言なし)'}）。",
                emote="emote_question.png",
            )

        if caster.mp < s_def.mp_cost:
            return self._cast_refusal(
                caster,
                target_name,
                f"《{skill_name}》を唱える魔力が足りない（必要 {s_def.mp_cost} / 所持 {caster.mp}）。",
            )

        caster.mp -= s_def.mp_cost
        slot.current_cooldown = s_def.cooldown

        tally = _CastTally()
        self.audio.play_sound("cast.ogg")
        tally.sounds.append("cast.ogg")
        tally.events.append(
            self.presentation.add_event(
                emote_file="emote_alert.png",
                audio_file="metalLatch.ogg",
                message=f"《{skill_name}》を唱える！",
            )
        )
        tally.logs.append(
            f"{caster.name}は《{skill_name}》を唱えた！"
            f"（魔力 -{s_def.mp_cost} / クールダウン {s_def.cooldown}）"
        )

        skipped: list[str] = []
        for effect in s_def.effects:
            if not self._apply_effect(effect, caster, target_list, tally):
                skipped.append(effect.effect_type)

        if skipped:
            tally.logs.append(
                "※未実行の効果（実行経路が無い）: " + ", ".join(dict.fromkeys(skipped))
            )

        if tally.damage:
            tally.events.append(
                self.presentation.add_event(
                    emote_file="emote_heartBroken.png",
                    message=f"{target_name}に {tally.damage} ダメージ！",
                )
            )
        if tally.heal:
            tally.events.append(
                self.presentation.add_event(
                    emote_file="emote_idea.png",
                    message=f"{caster.name}の体力が {tally.heal} 回復した！",
                )
            )
        if tally.statuses:
            tally.sounds.append("metalLatch.ogg")

        return BattleActionResult(
            action_type="SKILL",
            actor_name=caster.name,
            target_name=target_name,
            success=True,
            damage_dealt=tally.damage,
            heal_amount=tally.heal,
            status_applied=tally.statuses,
            log_messages=tally.logs,
            played_sounds=tally.sounds,
            presentation_events=tally.events,
        )

    def cast_devoured_skill(
        self, entity: Any, skill_id: str, target_entity: Any | None = None
    ) -> BattleActionResult:
        """プレイヤーの実体に《喰らい》した技を1回歌わせ、結果を実体へ書き戻す。

        World A の戦闘状態は実体の写しに過ぎないので、HP / MP / 状態異常はここでもどす。
        「唱えるにはどれほど近くにいるか」等の入力層の判断はこの関数の外側にある。
        """
        spellbook = self.player_spellbook(entity)
        target_states = (
            [_character_state_of(target_entity)] if target_entity is not None else []
        )

        result = self.cast_skill(spellbook, skill_id, target_states)

        entity.hp = spellbook.hp
        entity.mp = spellbook.mp
        if spellbook.status_effects:
            entity.status_effects = list(spellbook.status_effects)

        if target_states:
            target_state = target_states[0]
            target_entity.hp = target_state.hp
            target_entity.mp = target_state.mp
            if target_state.status_effects:
                target_entity.status_effects = list(target_state.status_effects)

        return result

    def _cast_refusal(
        self,
        caster: CharacterState,
        target_name: str,
        message: str,
        emote: str = "emote_swirl.png",
        audio: str = "creak1.ogg",
    ) -> BattleActionResult:
        """唱えられなかった旨を演出とログにして返す（魔力・クールダウンは消費しない）。"""
        self.audio.play_sound(audio)
        event = self.presentation.add_event(
            emote_file=emote, audio_file=audio, message=message
        )
        return BattleActionResult(
            action_type="SKILL",
            actor_name=caster.name,
            target_name=target_name,
            success=False,
            log_messages=[message],
            played_sounds=[audio],
            presentation_events=[event],
        )

    def _can_apply(
        self, effect: SkillEffect, caster: CharacterState, targets: Sequence[CharacterState]
    ) -> bool:
        """その場で効果当てられるかを、実体に触れずに判定する。"""
        if effect.effect_type not in EXECUTABLE_EFFECT_TYPES:
            return False
        if not _resolve_effect_targets(effect, caster, targets):
            return False
        if effect.effect_type in {"Damage", "Heal"}:
            return _formula_value(effect.params.get("formula"), caster) is not None
        if effect.effect_type == "ApplyStatus":
            return bool(str(effect.params.get("status") or "").strip())
        if _stat_mod_field(effect) is None:
            return False
        return bool(str(effect.params.get("formula") or "").strip())

    def _apply_effect(
        self,
        effect: SkillEffect,
        caster: CharacterState,
        targets: Sequence[CharacterState],
        tally: _CastTally,
    ) -> bool:
        """1 件の効果を実体へ当てる。実行できなかった場合は False。"""
        resolved = _resolve_effect_targets(effect, caster, targets)
        if not resolved:
            return False

        kind = effect.effect_type
        params = effect.params
        names = "、".join(t.name for t in resolved)

        if kind in {"Damage", "Heal"}:
            amount = _formula_value(params.get("formula"), caster)
            if amount is None or amount <= 0:
                return False
            element = str(params.get("element") or "")
            if kind == "Damage":
                dealt = 0
                for target in resolved:
                    damage = min(int(amount), target.hp)
                    target.hp = max(0, target.hp - int(amount))
                    dealt += damage
                tally.damage += dealt
                tally.logs.append(
                    f"{names}に {int(amount)} のダメージ！（{element}）"
                    if element
                    else f"{names}に {int(amount)} のダメージ！"
                )
                return True
            restored = 0
            for target in resolved:
                recovered = min(int(amount), max(0, target.max_hp - target.hp))
                target.hp += recovered
                restored += recovered
            tally.heal += restored
            tally.logs.append(f"{names}の体力が {restored} 回復した。")
            return True

        if kind == "ApplyStatus":
            status = str(params.get("status") or "").strip()
            if not status:
                return False
            chance = params.get("chance")
            if chance is not None and random.random() * 100.0 >= float(chance):
                tally.logs.append(f"《{status}》は確率 {int(float(chance))}% に当たらなかった。")
                return True
            for target in resolved:
                if status not in target.status_effects:
                    target.status_effects.append(status)
            tally.statuses.append(status)
            tally.logs.append(f"{names}に状態異常【{status}】が付いた！")
            return True

        if kind == "StatMod":
            field = _stat_mod_field(effect)
            if field is None:
                return False
            stat = str(params.get("stat"))
            for target in resolved:
                before = getattr(target, field)
                after = _clamp_field(target, field, _formula_value(
                    params.get("formula"), target, float(before)
                ) or float(before))
                setattr(target, field, after)
                tally.logs.append(f"{target.name}の{stat}が {before} → {after} に変わった。")
            return True

        return False

    # Step 20〜22: 喰らいコマンド（Emote: alert, star, cross）
    def execute_devour(
        self,
        predator: CharacterState,
        prey: CharacterState,
        target_skill_id: str | None = None,
        force_success: bool | None = None,
    ) -> BattleActionResult:
        logs = []
        sounds = []
        events = []
        available_skills = prey.get_skill_ids()

        if not available_skills or prey.is_husk:
            evt_empty = self.presentation.add_event(
                emote_file="emote_swirl.png", message="喰らうものがない！"
            )
            events.append(evt_empty)
            return BattleActionResult(
                action_type="DEVOUR",
                actor_name=predator.name,
                target_name=prey.name,
                success=False,
                log_messages=[
                    f"{prey.name}は既にスキルを持たない空っぽ（Husk）だ！ 喰らうものがない！"
                ],
                played_sounds=[],
                presentation_events=events,
            )

        if not target_skill_id or target_skill_id not in available_skills:
            target_skill_id = random.choice(available_skills)

        skill_def = self.registry.get_skill(target_skill_id)
        skill_name = skill_def.name if skill_def else target_skill_id
        target_slot = prey.skills.get(target_skill_id)

        # Step 22: 暗号化＆トラップチェック
        is_encrypted = False
        is_trap = False
        trap_penalty = "Virus"
        if target_slot is not None:
            is_encrypted = target_slot.is_encrypted
            is_trap = target_slot.is_trap
            trap_penalty = target_slot.trap_penalty or (
                skill_def.trap_penalty if skill_def else "Virus"
            )
        elif skill_def:
            is_encrypted = skill_def.is_encrypted
            is_trap = skill_def.is_trap
            trap_penalty = skill_def.trap_penalty

        if is_encrypted and not prey.encryption_broken:
            if is_trap:
                # トラップ発動！
                trap_dmg = max(5, int(predator.max_hp * 0.25))
                predator.hp = max(1, predator.hp - trap_dmg)
                if trap_penalty not in predator.status_effects:
                    predator.status_effects.append(trap_penalty)
                evt_trap = self.presentation.add_event(
                    emote_file="emote_cross.png",
                    audio_file="metalPot1.ogg",
                    message=f"【トラップ発動！】ウイルス感染＆{trap_dmg}ダメージ！",
                )
                sounds.append("metalPot1.ogg")
                events.append(evt_trap)
                return BattleActionResult(
                    action_type="DEVOUR",
                    actor_name=predator.name,
                    target_name=prey.name,
                    success=False,
                    damage_dealt=0,
                    log_messages=[
                        f"【トラップスキル感知！】《{skill_name}》は悪意ある偽装トラップだった！ {predator.name}は {trap_dmg} ダメージを受け、[{trap_penalty}]に感染した！"
                    ],
                    played_sounds=sounds,
                    presentation_events=events,
                )
            else:
                # 暗号化による拒絶
                evt_enc = self.presentation.add_event(
                    emote_file="emote_question.png",
                    audio_file="metalClick.ogg",
                    message="プロテクトにより捕食拒絶！",
                )
                sounds.append("metalClick.ogg")
                events.append(evt_enc)
                return BattleActionResult(
                    action_type="DEVOUR",
                    actor_name=predator.name,
                    target_name=prey.name,
                    success=False,
                    log_messages=[
                        f"【暗号化プロテクト！】《{skill_name}》は暗号化されているため喰らえません！ 先にハッキングか弱点攻撃でプロテクトを解除してください！"
                    ],
                    played_sounds=sounds,
                    presentation_events=events,
                )

        # Step 44: メモリ空き容量チェック
        cost = skill_def.memory_usage if skill_def else 1
        if predator.current_memory_usage + cost > predator.max_memory_capacity:
            evt_full = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="脳内メモリ不足！",
            )
            events.append(evt_full)
            return BattleActionResult(
                action_type="DEVOUR",
                actor_name=predator.name,
                target_name=prey.name,
                success=False,
                log_messages=[
                    f"【脳内メモリ容量不足！】《{skill_name}》（必要: {cost}）を記憶する空きがありません！（現在: {predator.current_memory_usage}/{predator.max_memory_capacity}） スキルを破棄してください！"
                ],
                played_sounds=["metalClick.ogg"],
                presentation_events=events,
            )

        # Step 20: 強奪モーション
        evt_start = self.presentation.add_event(
            emote_file="emote_alert.png",
            audio_file="clothBelt.ogg",
            message=f"《喰らい》発動！ 対象:《{skill_name}》",
        )
        sounds.append("clothBelt.ogg")
        events.append(evt_start)

        rate = self.calculate_devour_rate(predator, prey)
        logs.append(
            f"{predator.name}は禁忌の力《喰らい》を発動！ 対象スキル:《{skill_name}》（成功率: {int(rate * 100)}%）"
        )

        is_success = force_success if force_success is not None else (random.random() <= rate)

        if is_success:
            prey.remove_skill(target_skill_id)
            stat_loss = max(2, int(prey.defense * 0.3))
            prey.defense = max(1, prey.defense - stat_loss)
            prey.atk = max(1, prey.atk - stat_loss)
            prey.status_effects.append("SkillLossShock")

            predator.add_skill(target_skill_id, level=1)

            # Step 21: 捕食定着成功
            evt_ok = self.presentation.add_event(
                emote_file="emote_star.png",
                audio_file="handleSmallLeather2.ogg",
                message=f"《{skill_name}》の捕食・定着に成功！",
            )
            sounds.append("handleSmallLeather2.ogg")
            events.append(evt_ok)

            logs.append(f"【捕食成功！】{prey.name}から《{skill_name}》を完全に喰らい尽くした！")
            logs.append(
                f"{predator.name}は新たなスキル《{skill_name}》を獲得！（メモリ使用量: {predator.current_memory_usage}/{predator.max_memory_capacity}）"
            )

            primary_elem = None
            if skill_def and skill_def.tags:
                for t in ["Fire", "Water", "Ice", "Wind", "Defense", "Sword"]:
                    if t in skill_def.tags:
                        primary_elem = t
                        break

            bonus_dmg, _indig_dmg, combo_logs, combo_sounds, combo_events = (
                self.evaluate_devour_combo(predator, prey, primary_elem)
            )
            logs.extend(combo_logs)
            sounds.extend(combo_sounds)
            events.extend(combo_events)

            if prey.is_husk:
                logs.append(f"※{prey.name}の全スキルが消滅し、『空っぽ（Husk）』となった。")

            return BattleActionResult(
                action_type="DEVOUR",
                actor_name=predator.name,
                target_name=prey.name,
                success=True,
                damage_dealt=bonus_dmg,
                stolen_skill_id=target_skill_id,
                stolen_skill_name=skill_name,
                status_applied=["SkillLossShock"],
                log_messages=logs,
                played_sounds=sounds,
                presentation_events=events,
            )
        else:
            backlash_damage = max(5, int(predator.hp * 0.15))
            predator.hp = max(1, predator.hp - backlash_damage)
            prey.status_effects.append("Enraged")
            prey.atk = int(prey.atk * 1.3)

            # Step 22 & Step 15: 捕食失敗・敵激怒
            evt_fail = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="creak1.ogg",
                message="スキルの拒絶反応（反動ダメージ）！",
            )
            evt_enrage = self.presentation.add_event(
                emote_file="emote_faceAngry.png",
                audio_file="cloth4.ogg",
                message=f"{prey.name}が激怒状態になった！",
            )
            sounds.extend(["creak1.ogg", "cloth4.ogg"])
            events.extend([evt_fail, evt_enrage])

            logs.append(
                f"【捕食失敗……！】スキルの拒絶反応により暴走が発生！ {predator.name}は {backlash_damage} の反動ダメージを受けた！"
            )
            logs.append(f"{prey.name}は激怒状態となり、攻撃力が上昇した！")

            return BattleActionResult(
                action_type="DEVOUR",
                actor_name=predator.name,
                target_name=prey.name,
                success=False,
                damage_dealt=backlash_damage,
                status_applied=["Enraged"],
                log_messages=logs,
                played_sounds=sounds,
                presentation_events=events,
            )

    # Step 46, 47 & Steps 7〜11: 精神侵食警告とオーバークロック脳焼き処理チェーン
    def process_turn_end(self, character: CharacterState) -> dict[str, Any]:
        logs = []
        sounds = []
        events = []

        # 0. スキルのクールダウンを1ターン進める
        #    ここが World A のターン終了の入口なので、唱えた技の再使用可能性はここで戻る。
        for slot in character.skills.values():
            if slot.current_cooldown > 0:
                slot.current_cooldown -= 1

        # 1. オーバークロック脳焼きダメージ
        dmg, oc_logs, oc_evts = self.apply_overclock_damage(character)
        logs.extend(oc_logs)
        events.extend(oc_evts)

        # 2. 高位スキルの精神侵食度チェック
        for s_id in character.get_skill_ids():
            s_def = self.registry.get_skill(s_id)
            if s_def:
                if s_def.tier == SkillTier.UNIQUE:
                    character.addiction_buildup = min(100, character.addiction_buildup + 5)
                elif s_def.tier == SkillTier.CONCEPT:
                    character.addiction_buildup = min(100, character.addiction_buildup + 10)

        if character.addiction_buildup >= 100:
            if "Addicted" not in character.status_effects:
                character.status_effects.append("Addicted")
            # Step 47: 発狂（狂気エモート）
            evt_addict = self.presentation.add_event(
                emote_file="emote_laugh.png",
                audio_file="doorClose_3.ogg",
                message="精神崩壊！ スキル中毒状態に陥った！",
            )
            sounds.append("doorClose_3.ogg")
            events.append(evt_addict)
            logs.append(
                f"【精神崩壊警報！】{character.name}の脳が強力なスキルに侵食され『スキル中毒（Addicted）』に陥った！"
            )
        elif character.addiction_buildup >= 80:
            # Step 46: 侵食警告
            evt_warn = self.presentation.add_event(
                emote_file="emote_swirl.png",
                audio_file="creak1.ogg",
                message="精神侵食度が限界寸前！",
            )
            sounds.append("creak1.ogg")
            events.append(evt_warn)
            logs.append(
                f"※警告：{character.name}の精神侵食度が限界寸前（{character.addiction_buildup}/100）です。"
            )

        return {
            "overclock_level": character.overclock_level,
            "overclock_damage": dmg,
            "current_hp": character.hp,
            "logs": logs,
            "sounds": sounds,
            "events": events,
            "is_alive": character.hp > 0,
        }


# -------------------------------------------------------------
# Phase 1 Environmental Combat System
# -------------------------------------------------------------


@dataclass
class EnvironmentalObject:
    """Interactable environmental hazard that can be triggered via Analysis."""

    obj_id: str
    name: str
    hazard_type: str  # 'COLLAPSING_SCAFFOLD', 'MAGIC_PIPE', 'STEAM_VENT'
    trigger_cost_mp: int = 5
    damage: int = 150
    inflicts_stun: bool = True
    is_triggered: bool = False
    weak_spot_description: str = ""


@dataclass
class TacticalEnemy:
    """Enemy with structural flaw weak points revealable by Analysis."""

    enemy_id: str
    name: str
    hp: int
    max_hp: int
    atk: int
    structural_flaw: str  # e.g., 'CORE_OVERHEAT_VENT', 'ARMOR_JOINT_GAP'
    weakness_revealed: bool = False
    is_stunned: bool = False
    dropped_scraps: List[str] = field(default_factory=list)


class Phase1CombatManager:
    """Manages Phase 1 tactical combat, environment triggers, and weak point analysis."""

    def __init__(self) -> None:
        self.is_initialized: bool = True
        self.environment_objects: List[EnvironmentalObject] = []
        self.current_enemies: List[TacticalEnemy] = []

    def analyze_environmental_hazards(self) -> List[Dict[str, Any]]:
        """Uses Analysis to highlight interactable environmental traps."""
        results = []
        for obj in self.environment_objects:
            if not obj.is_triggered:
                results.append(
                    {
                        "obj_id": obj.obj_id,
                        "name": obj.name,
                        "hazard_type": obj.hazard_type,
                        "trigger_cost_mp": obj.trigger_cost_mp,
                        "damage": obj.damage,
                        "weak_spot": obj.weak_spot_description,
                        "highlight_color": "CYAN_PULSE",
                    }
                )
        return results

    def analyze_enemy_weakness(self, enemy_id: str) -> Dict[str, Any]:
        """Analyzes specific enemy to reveal structural flaws and targetable hitbox."""
        for enemy in self.current_enemies:
            if enemy.enemy_id == enemy_id:
                enemy.weakness_revealed = True
                return {
                    "success": True,
                    "enemy_id": enemy_id,
                    "structural_flaw": enemy.structural_flaw,
                    "hitbox_unlocked": True,
                    "multiplier": 3.0,
                    "description": f"《解析完了》弱点部位【{enemy.structural_flaw}】を捕捉！クリティカル率100%",
                }
        return {"success": False, "error": "ENEMY_NOT_FOUND"}

    def attack_weak_point(self, enemy_id: str, base_atk: int = 10) -> Dict[str, Any]:
        """Attacks the analyzed weak point, dealing 3x critical damage and triggering stagger."""
        for enemy in self.current_enemies:
            if enemy.enemy_id == enemy_id:
                if not enemy.weakness_revealed:
                    # Weak normal damage
                    enemy.hp -= base_atk
                    return {
                        "success": True,
                        "critical": False,
                        "damage": base_atk,
                        "enemy_hp": max(0, enemy.hp),
                    }
                dmg = int(base_atk * 3.0) + 20
                enemy.hp -= dmg
                enemy.is_stunned = True
                return {
                    "success": True,
                    "critical": True,
                    "damage": dmg,
                    "enemy_hp": max(0, enemy.hp),
                    "enemy_stunned": True,
                    "message": f"弱点直撃！致命的な{dmg}ダメージを与え、敵をスタンさせた！",
                }
        return {"success": False, "error": "ENEMY_NOT_FOUND"}

    def trigger_environmental_hazard(self, obj_id: str) -> Dict[str, Any]:
        """Triggers an environmental hazard dealing area damage and stunning all active enemies."""
        for obj in self.environment_objects:
            if obj.obj_id == obj_id:
                if obj.is_triggered:
                    return {"success": False, "error": "ALREADY_TRIGGERED"}
                obj.is_triggered = True
                total_affected = 0
                for enemy in self.current_enemies:
                    if enemy.hp > 0:
                        enemy.hp -= obj.damage
                        if obj.inflicts_stun:
                            enemy.is_stunned = True
                        total_affected += 1
                return {
                    "success": True,
                    "hazard_name": obj.name,
                    "damage_dealt": obj.damage,
                    "enemies_affected": total_affected,
                    "message": f"【環境トラップ発動】『{obj.name}』が崩壊！周囲の敵全員に{obj.damage}ダメージ＆スタン！",
                }
        return {"success": False, "error": "OBJECT_NOT_FOUND"}

    def setup_slum_tutorial_encounter(self) -> Dict[str, Any]:
        """Sets up the initial Slum tutorial fight showcasing Environmental Kills."""
        self.environment_objects = [
            EnvironmentalObject(
                obj_id="SCAFFOLD_01",
                name="腐食した足場",
                hazard_type="COLLAPSING_SCAFFOLD",
                damage=120,
                weak_spot_description="支柱の接合ボルト（《解析》で看破）",
            )
        ]
        self.current_enemies = [
            TacticalEnemy(
                enemy_id="SLUM_RAT_01",
                name="変異スラムラット",
                hp=100,
                max_hp=100,
                atk=15,
                structural_flaw="露出した首筋の生体コア",
                dropped_scraps=["SCRAP_BEAST_FANG", "SCRAP_AGILITY_FRAGMENT"],
            )
        ]
        return {
            "encounter": "SLUM_FIRST_FIGHT",
            "enemies_count": len(self.current_enemies),
            "hazards_count": len(self.environment_objects),
            "hint": "正面攻撃は危険！《解析》で足場のボルトかラットの首筋を狙え！",
        }
