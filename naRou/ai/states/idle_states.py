"""AI behavior state definitions (auto-extracted from naRou/ai_states.py)."""

from __future__ import annotations


from typing import TYPE_CHECKING, Any

from naRou.ai.states.base_state import (
    AIState,
    AStar,
    Point,
    MAP_HEIGHT,
    MAP_WIDTH,
    TILE_STAIRS_DOWN,
)

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class RestRecoverState(AIState):
    """Waits in safe zones to naturally regenerate HP when safe and well-fed."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        hunger = getattr(self.bb.engine.survival, "hunger", 100)

        # Visible enemies interrupt rest
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            self.bb.current_target_enemy = enemies_near[0]
            if (
                self.bb.strategy_name in ("mage", "speed")
                or self.bb.strategy_params.get("focus") == "magic"
            ):
                return "KITE"
            return "COMBAT"

        # Fully or sufficiently recovered
        if hp_ratio >= 0.90:
            return "EXPLORE"

        # Hungry: do not waste turns starving
        if hunger < 35:
            return "EXPLORE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        return ("wait", None)

    def _get_visible_enemies(self, range_: int = 8) -> list[Entity]:
        engine = self.bb.engine
        player = engine.player
        enemies = []
        for ent in engine.entity_manager.get_living_entities():
            if ent in (player, getattr(engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - player.x), abs(ent.y - player.y))
            if dist <= range_ and engine.has_los(Point(player.x, player.y), Point(ent.x, ent.y)):
                enemies.append(ent)
        return enemies
