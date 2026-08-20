"""
skill_eater_combat_system.py
Aの世界（スキル喰い）の戦闘エンジン＆《喰らい（Devour）》システム
提案2 & 3: 戦闘・喰らい・解析・ハックのEmote & Audio演出 (Steps 9〜24, 45〜47, 57〜59)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import (
    PresentationEvent,
    SkillEaterPresentationSystem,
)
from skill_eater_system import CharacterState, SkillEaterRegistry, SkillTier

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
    presentation_events: list[PresentationEvent] = field(
        default_factory=list
    )  # Step 9: 演出リスト


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

    def calculate_devour_rate(
        self, analyzer: CharacterState, target: CharacterState
    ) -> float:
        base_rate = 0.60
        analysis_bonus = analyzer.analysis_level * 0.05
        hp_loss_ratio = 1.0 - (target.hp / max(1, target.max_hp))
        hp_bonus = hp_loss_ratio * 0.50

        total_rate = base_rate + analysis_bonus + hp_bonus

        if "Paralyzed" in target.status_effects or "Sleep" in target.status_effects:
            total_rate += 0.20

        return max(0.05, min(0.95, round(total_rate, 2)))

    def analyze_target(
        self, analyzer: CharacterState, target: CharacterState
    ) -> AnalysisResult:
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
                        synergy_hint = f"★シナジー予測: 前回【{last_elem}】× 今回【{tag}】➔ 大爆発チャンス！"
                        break
                    elif (last_elem, tag) in INDIGESTION_COMBOS:
                        synergy_hint = f"▲消化不良警告: 前回【{last_elem}】× 今回【{tag}】➔ 自傷リスク！"
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

    # Step 57〜59: ハッキング実行コマンド（Emote & Audio演出）
    def execute_hack(
        self, analyzer: CharacterState, target: CharacterState
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
        is_success = random.random() <= hack_chance

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
                logs.append(
                    f"{desc} （{predator.name}は {indigestion_dmg} の自傷ダメージ！）"
                )
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
        logs = [
            f"{attacker.name}の通常攻撃！ {defender.name}に {raw_damage} のダメージ！"
        ]

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

        is_success = (
            force_success if force_success is not None else (random.random() <= rate)
        )

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

            logs.append(
                f"【捕食成功！】{prey.name}から《{skill_name}》を完全に喰らい尽くした！"
            )
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
                logs.append(
                    f"※{prey.name}の全スキルが消滅し、『空っぽ（Husk）』となった。"
                )

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
            backlash_damage = max(5, int(predator.max_hp * 0.15))
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

    # Step 46, 47: 精神侵食警告と発狂（Emote: swirl / laugh）
    def process_turn_end(
        self, character: CharacterState
    ) -> tuple[list[str], list[str], list[PresentationEvent]]:
        logs = []
        sounds = []
        events = []
        for s_id in character.get_skill_ids():
            s_def = self.registry.get_skill(s_id)
            if s_def:
                if s_def.tier == SkillTier.UNIQUE:
                    character.addiction_buildup = min(
                        100, character.addiction_buildup + 5
                    )
                elif s_def.tier == SkillTier.CONCEPT:
                    character.addiction_buildup = min(
                        100, character.addiction_buildup + 10
                    )

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

        return logs, sounds, events
