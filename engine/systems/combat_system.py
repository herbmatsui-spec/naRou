"""
Combat System - Handles combat-related logic extracted from Engine.
Consolidated: damage calculation, AoE, spell success, status effects (moved from naRou.systems.CombatSystem).
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

from constants import (
    ENERGY_THRESHOLD,
    MAP_HEIGHT,
    MAP_WIDTH,
    STATUS_BLEEDING,
    STATUS_PARALYSIS,
    STATUS_POISON,
    Element,
    GameState,
)
from ecs.entity import Attributes, Entity
from run_summary import CAUSE_COMBAT, CAUSE_HUNGER, CAUSE_SELF, CAUSE_UNKNOWN
from sound_manager import SoundManager
from ui_fx_systems import FloatingText, Particle

if TYPE_CHECKING:
    from naRou.systems import ResistanceSet

    from event_bus import EventBus
    from game import Engine

logger = logging.getLogger(__name__)


class CombatSystem:
    """Handles combat events, kill rewards, and combat progression.
    Also provides all damage calculation methods (formerly in naRou.systems.CombatSystem).
    """

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def handle_kill(self, entity) -> None:
        """Process entity kill: rewards, quests, achievements, reputation."""
        engine = self.engine

        # Main quest progress
        if hasattr(engine, "main_quest_system"):
            logs = engine.main_quest_system.update_progress(engine.player, "kill", entity.name, 1, engine)
            for log in logs:
                engine.message_log.add(log, level="SUCCESS")

        # Procedural quests
        engine._progress_generated_quests("kill", entity.name, 1)

        # Log and effects
        engine.log(f"★{entity.name}を撃破！", (255, 215, 0), level="SUCCESS")
        SoundManager.play_se("kill")
        if hasattr(engine, "screen_shake"):
            engine.screen_shake.trigger(intensity=1.2, duration=3)

        # 撃破の瞬間を静止させるヒットストップ (打撃感統合: 既存FXに追加)
        fx_manager = getattr(engine, "fx_manager", None)
        if fx_manager is not None and hasattr(fx_manager, "trigger_hit_stop"):
            fx_manager.trigger_hit_stop(duration=6)

        # Explosion particles
        for _ in range(3):
            engine.particles.append(
                Particle(
                    "💥",
                    entity.x,
                    entity.y,
                    (255, 180, 50),
                    life=3,
                    vx=random.uniform(-0.4, 0.4),
                    vy=random.uniform(-0.4, 0.4),
                )
            )

        # Combat rewards
        from managers.combat_manager import CombatManager
        CombatManager().handle_kill_rewards(engine, entity)

        # SkillEaterSecretAccess - key item drops
        self._handle_secret_drops(entity)

        # Title system: kill counts
        if engine.player and hasattr(engine.player, "kill_counts"):
            key = entity.name.lower().replace(" ", "_")
            engine.player.kill_counts[key] = engine.player.kill_counts.get(key, 0) + 1

            m_type = getattr(entity, "char", "monster")
            if "goblin" in key or "ゴブリン" in entity.name:
                m_type = "goblin"
            elif "slime" in key or "ぷち" in entity.name:
                m_type = "slime"
            engine.player.monster_killed_types[m_type] = (
                engine.player.monster_killed_types.get(m_type, 0) + 1
            )

            # Title check
            from title_system import MANAGER
            granted = MANAGER.check_all_titles(engine.player)

            # Achievement check
            if hasattr(engine, "achievement_manager"):
                engine.achievement_manager.check_all_achievements(engine.player, engine)

        # Skill points
        from managers.skill_reward_manager import SkillRewardManager
        SkillRewardManager().grant_kill_skill_points(engine, entity)

        # Pet bond
        from managers.pet_bond_manager import PetBondManager
        PetBondManager().update_combat_bond(engine, entity)

        # Guild quests
        if engine.player and getattr(engine.player, "guild_id", None):
            mon_name = entity.name.lower()
            if "ゴブリン" in mon_name or "goblin" in mon_name:
                done = engine.guild_quest_manager.update_quest_progress(
                    engine.player, "slay_goblins", amount=20
                )
                engine.log("【ギルドクエスト】ゴブリン討伐進捗を記録！", (100, 255, 200))
                if done:
                    ok, qmsg, _ = engine.guild_quest_manager.complete_quest(
                        engine.player, "slay_goblins"
                    )
                    if ok:
                        engine.log(qmsg, (255, 215, 0))
            elif "ぷち" in mon_name or "slime" in mon_name:
                done = engine.guild_quest_manager.update_quest_progress(
                    engine.player, "slay_slimes", amount=34
                )
                engine.log("【ギルドクエスト】ぷち駆除進捗を記録！", (100, 255, 200))
                if done:
                    ok, qmsg, _ = engine.guild_quest_manager.complete_quest(
                        engine.player, "slay_slimes"
                    )
                    if ok:
                        engine.log(qmsg, (255, 215, 0))

        # Faction reputation
        from managers.faction_manager import FactionManager
        FactionManager().update_kill_reputation(engine, entity)

        # Memory fragments
        if random.random() < 0.08 and hasattr(engine, "meta_progression_manager"):
            from meta_progression_system import MemoryFragmentGenerator
            frag = MemoryFragmentGenerator.generate(
                engine.player,
                trigger_type="boss_kill",
                context={"enemy_name": entity.name, "dungeon_level": engine.dungeon_level},
            )
            engine.meta_progression_manager.add_memory_fragment(engine.player, frag, engine)

    def _handle_secret_drops(self, entity) -> None:
        """Handle secret area key item drops."""
        try:
            from secret_area_system import SECRET_REGISTRY
            SECRET_REGISTRY.load_from_yaml()

            drop_chance = 0.05
            if getattr(entity, "is_boss", False) or getattr(entity, "unique_boss", False):
                drop_chance = 0.3
            elif "unique" in entity.name.lower() or "ボス" in entity.name:
                drop_chance = 0.2

            if random.random() < drop_chance:
                dungeon_level = getattr(self.engine, "dungeon_level", 1)
                keycard_level = min(5, max(1, (dungeon_level // 5) + 1))

                available_keys = []
                for key in SECRET_REGISTRY.get_all_key_items():
                    if key.key_type == "keycard" and key.level <= keycard_level:
                        available_keys.append(key.id)
                    elif key.key_type == "biometric" and key.level <= (keycard_level // 2 + 1):
                        available_keys.append(key.id)
                    elif key.key_type == "decryption" and key.level <= (keycard_level // 2 + 1):
                        available_keys.append(key.id)

                if available_keys:
                    key_id = random.choice(available_keys)
                    key_def = SECRET_REGISTRY.get_key_item(key_id)
                    if key_def:
                        from item_system import Item
                        key_item = Item(
                            key_def.name, "tool", "🗝️", (255, 215, 0),
                            base_weight=0.1, base_value=key_def.market_value
                        )
                        key_item.x, key_item.y = entity.x, entity.y
                        key_item.key_data = {
                            "key_id": key_id,
                            "key_type": key_def.key_type,
                            "level": key_def.level,
                        }
                        self.engine.items_on_ground.append(key_item)
                        self.engine.log(f"{entity.name}が『{key_def.name}』を落とした！", (255, 215, 0))
        except Exception:
            pass

    # ==================== DAMAGE CALCULATION (moved from naRou.systems.CombatSystem) ====================

    @staticmethod
    def aoe_radius(cx: int, cy: int, radius: int = 1) -> list[tuple[int, int]]:
        """円形範囲の座標リスト"""
        from combat import aoe_radius
        return aoe_radius(cx, cy, radius)

    @staticmethod
    def aoe_beam(
        sx: int, sy: int, direction: tuple[int, int], length: int = 5
    ) -> list[tuple[int, int]]:
        """直線ビーム範囲"""
        from combat import aoe_beam
        return aoe_beam(sx, sy, direction, length)

    @staticmethod
    def aoe_nova(cx: int, cy: int) -> list[tuple[int, int]]:
        """周囲全方位（8マス）"""
        from combat import aoe_nova
        return aoe_nova(cx, cy)

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
        """属性耐性を考慮したダメージ計算"""
        from combat import calc_element_damage
        return calc_element_damage(base_dmg, element, resistance)

    @staticmethod
    def calc_spell_success(caster: Entity, spell_id: str) -> tuple[bool, int | None]:
        """魔法詠唱成功率 - 失敗時にマナ反動ダメージ"""
        skill_lv = caster.skills.get("magic_cast", None)
        skill_val = skill_lv.level if skill_lv else 1
        magic_attr = caster.attributes.magic if hasattr(caster, "attributes") else 10

        success_rate = min(98, max(5, skill_val * 8 + magic_attr * 3 - 20))
        roll = random.randint(1, 100)

        if roll <= success_rate:
            return True, None
        else:
            backlash = random.randint(3, 10 + magic_attr)
            return False, backlash

    @staticmethod
    def calculate_melee_attack(
        attacker: Entity,
        defender: Entity,
        weapon=None,
        element: Element = Element.PHYSICAL,
    ) -> tuple[int, bool, str]:
        """近接攻撃 + 属性ダメージ + 出血付与 + バックスタブ判定"""
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

        # バックスタブ判定: 攻撃者が防御者の背後にいる場合 ×1.5倍
        attacker_facing = getattr(attacker, "facing", "S")
        defender_facing = getattr(defender, "facing", "S")
        is_backstab = False
        # 向きが反対（攻撃者が防御者の背後から攻撃）の場合
        if (
            (attacker_facing == "N" and defender_facing == "S")
            or (attacker_facing == "S" and defender_facing == "N")
            or (attacker_facing == "E" and defender_facing == "W")
            or (attacker_facing == "W" and defender_facing == "E")
        ):
            is_backstab = True
            roll_dmg = int(roll_dmg * 1.5)

        try:
            from event_bus import EVENT_BEFORE_DAMAGE, event_bus

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

        # 属性耐性 & 弱点判定 (PR #8 integration: origin/main より移植, Steps 55, 56)
        elem_name = element.value if hasattr(element, "value") else str(element)
        is_weak = False
        if hasattr(defender, "is_weak_to") and defender.is_weak_to(elem_name):
            is_weak = True
            roll_dmg = int(roll_dmg * 1.5)

        from naRou.systems import ResistanceSet

        if hasattr(defender, "get_elemental_resistance"):
            res_val = defender.get_elemental_resistance(elem_name)
        else:
            res = getattr(defender, "resistances", ResistanceSet())
            res_val = res.get(element) if hasattr(res, "get") else 0
        final_dmg = CombatSystem.calc_element_damage(roll_dmg, element, res_val)
        final_dmg = max(
            1,
            final_dmg - random.randint(0, max(1, int(defender.attributes.endurance / 4))),
        )

        # 転生スケーリング適用
        # TODO: Reincarnation scaling
        if not getattr(attacker, "is_player", False):
            reinc_count = getattr(defender, "reincarnation_count", 0)
            if reinc_count > 0:
                mult = min(5.0, 1.0 + reinc_count * 0.15)
                final_dmg = int(final_dmg * mult)

        # 難易度補正: プレイヤーが受けるダメージを難易度で補正
        if getattr(defender, "is_player", False):
            from core.difficulty import DifficultyManager

            final_dmg = int(DifficultyManager().player_damage_taken(final_dmg))

        # 出血判定: 大きなダメージ時に5%
        if final_dmg > 8 and random.random() < 0.05:
            if not hasattr(defender, "status_effects"):
                defender.status_effects = []
            defender.status_effects = [
                s for s in defender.status_effects if s.name != STATUS_BLEEDING
            ]
            from naRou.systems import StatusEffect
            defender.status_effects.append(StatusEffect(STATUS_BLEEDING, 500, power=2))

        crit_msg = "★会心の一撃！ " if is_crit else ""
        backstab_msg = "【背後攻撃】" if is_backstab else ""
        weak_msg = "【効果はばつぐんだ！】" if is_weak else ""
        msg = f"{attacker.name}は{defender.name}に{final_dmg}ダメージ！ {crit_msg}{backstab_msg}{weak_msg}"
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
        """AoE範囲攻撃 - フレンドリーファイア含む"""
        from naRou.systems import ResistanceSet
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
                    if getattr(e, "is_pet", False):
                        if karma_ref is not None:
                            karma_ref["value"] -= 5
                        logs.append(f"    【悪行】{e.name}を巻き込んだ！ カルマ-5")
        return logs

    @staticmethod
    def process_status_effects(entity: Entity) -> list[str]:
        """状態異常のTick処理 (ステップ16, 45, Phase 4 Steps 27-31)"""
        logs = []
        is_bleeding = False

        # 1. ECS StatusEffectsComponent 処理 (PR #8 integration: origin/main より移植, Step 54, 58-61)
        if hasattr(entity, "get_component"):
            try:
                from ecs.components import StatusEffectsComponent

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

        # 2. 後方互換リスト型 status_effects 処理 (従来ロジック)
        if not hasattr(entity, "status_effects"):
            entity.status_effects = []
        legacy_list = isinstance(entity.status_effects, list)
        remaining = []
        for eff in (entity.status_effects if legacy_list else []):
            if not getattr(eff, "is_infinite", False):
                eff.remaining_ticks -= 10

            if eff.name == STATUS_POISON:
                dmg = max(1, eff.power)
                entity.hp -= dmg
                if random.random() < 0.1:
                    logs.append(f"{entity.name}は毒に蝕まれる！(-{dmg} HP)")
            elif eff.name == STATUS_BLEEDING:
                dmg = max(1, eff.power)
                entity.hp -= dmg
                if random.random() < 0.15:
                    logs.append(f"{entity.name}の傷口から血が流れ出す！(-{dmg} HP)")
            elif eff.name == "Husk":
                entity.energy = min(entity.energy, 0)
            elif eff.name == "Toxicity":
                dmg = max(1, int(entity.max_hp * (0.01 * eff.power)))
                entity.hp -= dmg
                if random.random() < 0.1:
                    logs.append(f"{entity.name}は拒絶反応に苦しむ！(-{dmg} HP)")
            elif eff.name == "Regen":
                heal = max(1, eff.power)
                entity.hp = min(entity.hp + heal, getattr(entity, "max_hp", entity.hp))
                if random.random() < 0.1:
                    logs.append(f"{entity.name}の傷が再生していく。(+{heal} HP)")
            elif eff.name == STATUS_PARALYSIS:
                entity.energy = min(entity.energy, 0)

            if eff.remaining_ticks > 0:
                remaining.append(eff)
            else:
                if eff.name == STATUS_BLEEDING:
                    logs.append(f"{entity.name}の出血が止まった。")

        if legacy_list:
            entity.status_effects = remaining
            is_bleeding = any(e.name == STATUS_BLEEDING for e in entity.status_effects)
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

        dmg = 0
        if skill_id == "shield_bash":
            dmg = int(caster.attributes.strength * 1.5) + random.randint(3, 8)
            target.hp -= dmg
            if not hasattr(target, "status_effects"):
                target.status_effects = []
            from naRou.systems import STATUS_PARALYSIS, StatusEffect
            target.status_effects.append(StatusEffect(STATUS_PARALYSIS, 30, power=2))
            return (
                dmg,
                f"{caster.name}の【{name}】！ {target.name}に{dmg}ダメージとスタンを付与！",
            )

        elif skill_id == "iaijutsu":
            dmg = int(caster.attributes.dexterity * 2) + random.randint(5, 12)
            target.hp -= dmg
            return (
                dmg,
                f"{caster.name}の【{name}】！ {target.name}に{dmg}ダメージ！",
            )

        return 0, f"未実装の専用スキル: {skill_id}"
