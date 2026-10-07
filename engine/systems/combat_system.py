"""
Combat System - Handles combat-related logic extracted from Engine.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from constants import ENERGY_THRESHOLD
from run_summary import CAUSE_COMBAT, CAUSE_HUNGER, CAUSE_SELF, CAUSE_UNKNOWN
from sound_manager import SoundManager
from ui_fx_systems import FloatingText, Particle

if TYPE_CHECKING:
    from game import Engine

logger = logging.getLogger(__name__)


class CombatSystem:
    """Handles combat events, kill rewards, and combat progression."""

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

    def cast_fireball(self) -> bool:
        """Cast fireball spell."""
        engine = self.engine
        success, backlash = engine.combat_system.calc_spell_success(engine.player, "fireball")
        if not success:
            engine.player.hp -= backlash
            engine._record_harm_cause(CAUSE_SELF)
            SoundManager.play_se("hit")
            engine.floating_texts.append(
                FloatingText(f"-{backlash}", engine.player.x, engine.player.y - 0.2, (255, 80, 80))
            )
            engine.log(
                f"魔法の詠唱に失敗！ 魔力が暴走し {backlash} ダメージを受けた！",
                (255, 80, 80),
            )
            engine.player.energy -= ENERGY_THRESHOLD
            engine.advance_world()
            return False

        mp_cost = 10
        if engine.player.mp < mp_cost:
            engine.log("MPが足りない！", (255, 100, 100))
            return False

        SoundManager.play_se("cast")
        engine.player.mp -= mp_cost
        tx, ty = engine.player.x + 3, engine.player.y

        # Trail particles
        for i in range(1, 4):
            engine.particles.append(
                Particle("🔥", engine.player.x + i, engine.player.y, (255, 120, 30), life=2)
            )

        from constants import Element
        from naRou.systems import CombatSystem as SysCombatSystem
        coords = SysCombatSystem.aoe_radius(tx, ty, radius=1)
        karma_ref = {"value": engine.survival.karma}
        logs = SysCombatSystem.apply_aoe(
            engine.player,
            coords,
            (18, 35),
            Element.FIRE,
            engine.entity_manager.get_living_entities(),
            karma_ref,
        )
        engine.survival.karma = karma_ref["value"]
        for l in logs:
            engine.log(l, (255, 140, 60))

        # Death check
        for e in list(engine.entity_manager.get_living_entities()):
            if e not in (engine.player, engine.pet) and e.hp <= 0:
                self.handle_kill(e)

        engine.player.energy -= ENERGY_THRESHOLD
        engine.advance_world()
        return True