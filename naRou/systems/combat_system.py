"""高度な戦闘システム - 属性・詠唱失敗・AoE・フレンドリーファイア・出血 (ステップ37〜45)。"""
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

from naRou import combat
from naRou.constants import Element

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from naRou.item_system import Item

from .combat_core import (
    STATUS_BLEEDING,
    STATUS_PARALYSIS,
    STATUS_POISON,
    AggroList,
    ResistanceSet,
    StatusEffect,
)


class CombatSystem:
    """高度な戦闘計算 - 属性・詠唱失敗・AoE・フレンドリーファイア・出血 (ステップ37〜45)"""

    # AoEパターン生成 (ステップ40)
    @staticmethod
    def aoe_radius(cx: int, cy: int, radius: int = 1) -> list[tuple[int, int]]:
        """円形範囲の座標リスト"""
        return combat.aoe_radius(cx, cy, radius)

    @staticmethod
    def aoe_beam(
        sx: int, sy: int, direction: tuple[int, int], length: int = 5
    ) -> list[tuple[int, int]]:
        """直線ビーム範囲"""
        dx, dy = direction
        return combat.aoe_beam(sx, sy, direction, length)

    @staticmethod
    def aoe_nova(cx: int, cy: int) -> list[tuple[int, int]]:
        """周囲全方位（8マス）"""
        return combat.aoe_nova(cx, cy)

    @staticmethod
    def publish_damage_event(
        event_bus,
        damage: int,
        x: int,
        y: int,
        is_crit: bool = False,
        is_kill: bool = False,
    ) -> None:
        """ダメージイベントを発行 (FXManagerが購読してエフェクトを生成)"""
        if event_bus:
            event_bus.publish(
                "damage_dealt",
                {
                    "damage": damage,
                    "x": x,
                    "y": y,
                    "is_crit": is_crit,
                    "is_kill": is_kill,
                },
            )

    @staticmethod
    def publish_kill_event(event_bus, x: int, y: int) -> None:
        """敵撃破イベントを発行"""
        if event_bus:
            event_bus.publish("entity_killed", {"x": x, "y": y})

    @staticmethod
    def publish_trap_event(event_bus, damage: int, x: int, y: int) -> None:
        """トラップ発動イベントを発行"""
        if event_bus:
            event_bus.publish("trap_triggered", {"damage": damage, "x": x, "y": y})

    @staticmethod
    def calc_element_damage(base_dmg: int, element: Element, resistance: int) -> int:
        """属性耐性を考慮したダメージ計算 (ステップ38)"""
        # resistance: 100=無効, 0=通常, -50=弱点(1.5倍)
        return combat.calc_element_damage(base_dmg, element, resistance)

    @staticmethod
    def calc_spell_success(caster: Entity, spell_id: str) -> tuple[bool, int | None]:
        """魔法詠唱成功率 (ステップ39) - 失敗時にマナ反動ダメージ"""
        skill_lv = caster.skills.get("magic_cast", None)
        skill_val = skill_lv.level if skill_lv else 1
        magic_attr = caster.attributes.magic if hasattr(caster, "attributes") else 10

        # 成功率計算: スキルLv * 8 + 知力 * 3 + 乱数
        success_rate = min(98, max(5, skill_val * 8 + magic_attr * 3 - 20))
        roll = random.randint(1, 100)

        if roll <= success_rate:
            return True, None
        else:
            # 失敗: マナ反動ダメージ
            backlash = random.randint(3, 10 + magic_attr)
            return False, backlash

    @staticmethod
    def calculate_melee_attack(
        attacker: Entity,
        defender: Entity,
        weapon=None,
        element: Element = Element.PHYSICAL,
    ) -> tuple[int, bool, str]:
        """近接攻撃 + 属性ダメージ + 出血付与 (ステップ37, 38, 45)"""
        hit_rate = 75 + attacker.attributes.dexterity - defender.attributes.dexterity
        if weapon:
            hit_rate += weapon.hit_bonus * 5
        hit_rate = max(10, min(95, hit_rate))

        if random.randint(1, 100) > hit_rate:
            return 0, False, f"{attacker.name}の攻撃は{defender.name}にかわされた。"

        crit_rate = 5 + int(attacker.attributes.perception / 5)
        is_crit = random.randint(1, 100) <= crit_rate

        dice_n = weapon.dice_num if weapon else 1
        dice_s = weapon.dice_side if weapon else 4
        bonus = weapon.dmg_bonus if weapon else 0
        roll_dmg = sum(random.randint(1, dice_s) for _ in range(dice_n)) + bonus
        roll_dmg += int(attacker.attributes.strength / 3)
        if is_crit:
            roll_dmg = int(roll_dmg * 1.5) + dice_s

        try:
            from naRou.event_bus import EVENT_BEFORE_DAMAGE, event_bus

            evt_data = {
                "attacker": attacker,
                "defender": defender,
                "damage": roll_dmg,
                "element": element,
                "is_crit": is_crit,
            }
            event_bus.publish(EVENT_BEFORE_DAMAGE, evt_data)
            roll_dmg = evt_data["damage"]
        except ImportError:
            pass

        # 属性耐性 & 弱点判定 (Steps 55, 56)
        elem_name = element.value if hasattr(element, "value") else str(element)
        is_weak = False
        if hasattr(defender, "is_weak_to") and defender.is_weak_to(elem_name):
            is_weak = True
            roll_dmg = int(roll_dmg * 1.5)

        res_val = 0
        if hasattr(defender, "get_elemental_resistance"):
            res_val = defender.get_elemental_resistance(elem_name)
        else:
            res = getattr(defender, "resistances", ResistanceSet())
            res_val = res.get(element) if hasattr(res, "get") else 0

        final_dmg = CombatSystem.calc_element_damage(roll_dmg, element, res_val)

        # 武器のエンチャント属性追加ダメージの加算 (Step 13, 55)
        extra_elem_logs = []
        if attacker and hasattr(attacker, "inventory") and attacker.inventory:
            for extra_elem, extra_pwr in attacker.inventory.get_weapon_element_damages():
                if hasattr(defender, "is_weak_to") and defender.is_weak_to(extra_elem):
                    extra_pwr = int(extra_pwr * 1.5)
                    extra_elem_logs.append(f"【{extra_elem}弱点!】")
                ext_res = defender.get_elemental_resistance(extra_elem) if hasattr(defender, "get_elemental_resistance") else 0
                calc_ext = max(1, int(extra_pwr * (1.0 - ext_res / 100.0)))
                final_dmg += calc_ext

                # 状態異常の付与抽選 (Step 57)
                if hasattr(defender, "add_status") and random.random() < 0.25:
                    if extra_elem == "fire":
                        defender.add_status("burn", duration=3, power=max(1, calc_ext // 2), source_name=attacker.name)
                        extra_elem_logs.append("🔥炎上付与!")
                    elif extra_elem == "ice":
                        defender.add_status("freeze", duration=2, power=1, source_name=attacker.name)
                        extra_elem_logs.append("❄️凍結付与!")
                    elif extra_elem == "lightning":
                        defender.add_status("paralyze", duration=2, power=1, source_name=attacker.name)
                        extra_elem_logs.append("⚡麻痺付与!")
                    elif extra_elem == "poison":
                        defender.add_status("poison", duration=4, power=max(1, calc_ext // 2), source_name=attacker.name)
                        extra_elem_logs.append("🧪毒付与!")

        final_dmg = max(
            1,
            final_dmg - random.randint(0, max(1, int(defender.attributes.endurance / 4))),
        )

        # 転生スケーリング適用 (Steps 53, 54)
        if not getattr(attacker, "is_player", False):
            # 敵の攻撃力にプレイヤーの転生スケーリングを適用
            reinc_count = getattr(defender, "reincarnation_count", 0)
            if reinc_count > 0:
                mult = min(5.0, 1.0 + reinc_count * 0.15)
                final_dmg = int(final_dmg * mult)

        # 難易度補正 (Step 33): プレイヤーが受けるダメージを難易度で補正
        if getattr(defender, "is_player", False):
            from naRou.core.difficulty import DifficultyManager

            final_dmg = max(1, int(DifficultyManager().player_damage_taken(final_dmg)))

        # 出血判定 (ステップ45): 大きなダメージ時に5%
        if final_dmg > 8 and random.random() < 0.05:
            if hasattr(defender, "add_status"):
                defender.add_status("bleeding", duration=5, power=2, source_name=attacker.name)
            elif hasattr(defender, "status_effects"):
                defender.status_effects = [
                    s for s in defender.status_effects if s.name != STATUS_BLEEDING
                ]
                defender.status_effects.append(StatusEffect(STATUS_BLEEDING, 500, power=2))

        crit_msg = "★会心の一撃！ " if is_crit else ""
        weak_msg = "【効果はばつぐんだ！】" if is_weak else ""
        extra_msg = " ".join(extra_elem_logs)
        msg = f"{attacker.name}は{defender.name}に{final_dmg}ダメージ！ {crit_msg}{weak_msg} {extra_msg}".strip()
        return final_dmg, is_crit, msg

    @staticmethod
    def apply_aoe(
        caster: Entity,
        coords: list[tuple[int, int]],
        base_dmg_range: tuple[int, int],
        element: Element,
        entities: list[Entity],
        karma_ref: Any = None,
    ) -> list[str]:
        """AoE範囲攻撃 - フレンドリーファイア含む (ステップ40, 41)"""
        logs = []
        for ex, ey in coords:
            for e in list(entities):
                if e.x == ex and e.y == ey and e.hp > 0:
                    base = random.randint(*base_dmg_range)
                    res = getattr(e, "resistances", ResistanceSet())
                    res_val = res.get(element) if hasattr(res, "get") else 0
                    dmg = CombatSystem.calc_element_damage(
                        base + caster.attributes.magic, element, res_val
                    )
                    e.hp -= dmg
                    logs.append(f"  -> {e.name}に{dmg}の{element.name}ダメージ！")
                    # フレンドリーファイア: ペットや市民を巻き込んだらカルマ低下
                    if e.is_pet if hasattr(e, "is_pet") else False:
                        if karma_ref is not None:
                            karma_ref["value"] -= 5
                        logs.append(f"    【悪行】{e.name}を巻き込んだ！ カルマ-5")
        return logs

    @staticmethod
    def process_status_effects(entity: Entity) -> tuple[list[str], bool]:
        """状態異常のTick処理 (ステップ16, 45, 58-61)"""
        logs = []
        is_bleeding = False

        # 1. ECS StatusEffectsComponent 処理 (Step 54, 58-61)
        if hasattr(entity, "get_component"):
            try:
                from naRou.ecs.components import StatusEffectsComponent
                sec = entity.get_component(StatusEffectsComponent)
                expired = []
                for eff_type, eff in list(sec.effects.items()):
                    eff.duration -= 1

                    if eff_type in ("poison", "毒"):
                        dmg = max(1, eff.power)
                        entity.hp -= dmg
                        logs.append(f"{entity.name}は毒で{dmg}ダメージを受けた！")
                    elif eff_type in ("burn", "炎上"):
                        dmg = max(1, eff.power * 2)
                        entity.hp -= dmg
                        logs.append(f"{entity.name}は炎上で{dmg}ダメージを受けた！")
                    elif eff_type in ("freeze", "凍結", "paralyze", "麻痺", "sleep", "睡眠"):
                        entity.energy = min(entity.energy, 0)
                        eff_label = "凍結" if "freeze" in eff_type else ("麻痺" if "paralyze" in eff_type else "睡眠")
                        logs.append(f"{entity.name}は{eff_label}で動けない！")
                    elif eff_type in ("bleeding", "出血"):
                        is_bleeding = True
                        dmg = max(1, eff.power)
                        entity.hp -= dmg
                        logs.append(f"{entity.name}は出血で{dmg}ダメージを受けた！")

                    if eff.duration <= 0:
                        expired.append(eff_type)
                        logs.append(f"{entity.name}の{eff_type}状態が治まった。")

                for exp_type in expired:
                    sec.remove_effect(exp_type)
            except Exception:
                pass

        # 2. 後方互換リスト型 status_effects 処理
        if hasattr(entity, "status_effects") and isinstance(entity.status_effects, list):
            remaining = []
            for eff in entity.status_effects:
                if not getattr(eff, "is_infinite", False):
                    eff.remaining_ticks -= 10

                if eff.name == STATUS_POISON:
                    dmg = max(1, eff.power)
                    entity.hp -= dmg
                    if random.random() < 0.1:
                        logs.append(f"{entity.name}は毒に蝕まれる！(-{dmg} HP)")
                elif eff.name == STATUS_BLEEDING:
                    is_bleeding = True
                    dmg = max(1, eff.power)
                    entity.hp -= dmg
                    if random.random() < 0.15:
                        logs.append(f"{entity.name}の傷口から血が流れ出す！(-{dmg} HP)")
                elif eff.name == STATUS_PARALYSIS:
                    entity.energy = min(entity.energy, 0)

                if eff.remaining_ticks > 0:
                    remaining.append(eff)
                else:
                    if eff.name == STATUS_BLEEDING:
                        logs.append(f"{entity.name}の出血が止まった。")

            entity.status_effects = remaining

        return logs, is_bleeding

    @staticmethod
    def cast_spell(caster: Entity, spell_name: str, target: Entity) -> tuple[int, str]:
        """詠唱失敗率つき魔法発動 (ステップ39)"""
        success, backlash = CombatSystem.calc_spell_success(caster, spell_name)
        if not success:
            caster.hp -= backlash
            return 0, f"詠唱に失敗した！ 魔力が暴走し{backlash}のダメージを受けた！"

        if spell_name == "magic_dart":
            mp_cost = 4
            if caster.mp < mp_cost:
                return 0, "MPが足りない！"
            caster.mp -= mp_cost
            dmg = random.randint(1, 6) + int(caster.attributes.magic / 2) + 5
            target.hp -= dmg
            return dmg, f"{caster.name}は魔法の矢を放ち{target.name}に{dmg}ダメージ！"
        elif spell_name == "minor_heal":
            mp_cost = 6
            if caster.mp < mp_cost:
                return 0, "MPが足りない！"
            caster.mp -= mp_cost
            heal = 25 + int(caster.attributes.will / 2)
            caster.hp = min(caster.max_hp, caster.hp + heal)
            return heal, f"{caster.name}の傷が癒えた！ (HP +{heal})"
        elif spell_name == "fireball":
            mp_cost = 10
            if caster.mp < mp_cost:
                return 0, "MPが足りない！"
            caster.mp -= mp_cost

    # === エクスクルーシブスキル処理 (Steps 62, 63) ===
    @staticmethod
    def is_exclusive_skill(skill_id: str) -> bool:
        """スキルIDがエクスクルーシブスキルか判定 (Step 62)"""
        try:
            from pathlib import Path

            import yaml

            p = Path("data/exclusive_skills.yaml")
            if not p.exists():
                return False
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return skill_id in data.get("exclusive_skills", {})
        except Exception:
            logger.exception("Unhandled exception")
            return False

    @staticmethod
    def get_exclusive_skill_data(skill_id: str) -> dict[str, Any] | None:
        """エクスクルーシブスキルの定義データを取得 (Step 62)"""
        try:
            from pathlib import Path

            import yaml

            p = Path("data/exclusive_skills.yaml")
            if not p.exists():
                return None
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("exclusive_skills", {}).get(skill_id)
        except Exception:
            logger.exception("Unhandled exception")
            import logging
            logging.getLogger(__name__).exception("Unhandled exception")
            return None

    @staticmethod
    def execute_exclusive_skill(caster: Entity, skill_id: str, target: Entity) -> tuple[int, str]:
        """エクスクルーシブスキル実行 (Step 63)"""
        data = CombatSystem.get_exclusive_skill_data(skill_id)
        if not data:
            return 0, "不明な専用スキル。"

        mp_cost = data.get("mp_cost", 10)
        if caster.mp < mp_cost:
            return 0, f"MPが足りない！ (必要MP: {mp_cost})"

        caster.mp -= mp_cost
        data.get("effects", {})
        name = data.get("name", skill_id)

        # ダメージ計算
        dmg = 0
        if skill_id == "shield_bash":
            dmg = int(caster.attributes.strength * 1.5) + random.randint(3, 8)
            target.hp -= dmg
            if not hasattr(target, "status_effects"):
                target.status_effects = []
            target.status_effects.append(StatusEffect(STATUS_PARALYSIS, 30, power=2))
            return (
                dmg,
                f"{caster.name}の【{name}】！ {target.name}に{dmg}ダメージとスタンを付与！",
            )

        elif skill_id == "iaijutsu":
            dmg = int(
                caster.attributes.dexterity * 2.5 + caster.attributes.strength * 1.2
            ) + random.randint(10, 20)
            target.hp -= dmg
            return (
                dmg,
                f"★{caster.name}の神速の【{name}】！ 刀閃が走り{target.name}に{dmg}の致命傷！",
            )

        elif skill_id == "meteor":
            dmg = int(caster.attributes.magic * 4.0) + random.randint(20, 50)
            target.hp -= dmg
            if not hasattr(target, "status_effects"):
                target.status_effects = []
            target.status_effects.append(StatusEffect(STATUS_BLEEDING, 500, power=5))
            return (
                dmg,
                f"🌌{caster.name}の【{name}】！ 天より隕石が降り注ぎ{target.name}に{dmg}の破滅的ダメージ！",
            )

        return 0, f"{caster.name}は【{name}】を放った！"
