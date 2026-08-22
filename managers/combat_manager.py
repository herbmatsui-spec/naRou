"""CombatManager: encapsulates post-kill reward settlement logic.

Extracted from Engine._on_kill (game.py) to reduce the Engine god-class
surface and keep combat settlement cohesive and testable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecs.entity import Entity
    from game import Engine


class CombatManager:
    """Handles the rewards granted when an entity is killed by the player."""

    def handle_kill_rewards(self, engine: "Engine", entity: "Entity") -> None:
        """Corpse drop, reincarnation XP penalty, and quest reward settlement."""
        from constants import CAT_FOOD, COLOR_GOLD_YELLOW
        from item_system import Item

        corpse = Item(
            f"{entity.name}の肉",
            CAT_FOOD,
            "🍖",
            (220, 80, 80),
            entity.x,
            entity.y,
            base_weight=2.0,
            base_value=40,
            nutrition=2800,
        )
        engine.entity_manager.add_item(corpse)

        # 転生経験値ペナルティ適用 (Steps 57, 58)
        from constants import REINCARNATION_XP_PENALTY_BASE, REINCARNATION_XP_PENALTY_STEP

        base_exp = 35 * engine.dungeon_level
        reinc_cnt = getattr(engine.player, "reincarnation_count", 0)
        if reinc_cnt > 0:
            penalty = max(
                REINCARNATION_XP_PENALTY_BASE,
                1.0 - reinc_cnt * REINCARNATION_XP_PENALTY_STEP,
            )
            base_exp = max(1, int(base_exp * penalty))

        for l in engine.player.gain_exp(base_exp):
            engine.log(l, (255, 255, 100))
        for q in engine.quests:
            if q.target_monster in entity.name and not q.completed:
                q.current_count += 1
                if q.current_count >= q.target_count:
                    q.completed = True
            engine.survival.gold += q.reward_gold
            engine.survival.platinum += q.reward_platinum
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
            engine.log(
                f"★依頼達成！ {q.reward_gold}G + {q.reward_platinum}P 獲得！",
                COLOR_GOLD_YELLOW,
            )
            engine.entity_manager.remove_entity(entity)
