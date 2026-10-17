"""
World System - Handles world/dungeon management extracted from Engine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from constants import MAP_HEIGHT, MAP_WIDTH, TILE_STAIRS_DOWN, GameState
from map_engine import GameMap

if TYPE_CHECKING:
    from game import Engine

logger = logging.getLogger(__name__)


class WorldSystem:
    """Handles world/dungeon management, stairs, win conditions."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def descend_stairs(self) -> bool:
        """Descend to next dungeon level."""
        engine = self.engine

        on_stairs = (
            engine.game_map.tiles[engine.player.x][engine.player.y] in (TILE_STAIRS_DOWN, "TILE_STAIRS_DOWN", ">")
            or (engine.player.x, engine.player.y) == getattr(engine.game_map, "stairs_down_pos", None)
        )

        if not on_stairs:
            engine.log("ここには下り階段はない。")
            return False

        # Reincarnation dungeon check
        if hasattr(engine, "reincarnation_dungeon_manager") and engine.dungeon_level >= 10:
            pass  # Hook for future restrictions

        engine.dungeon_level += 1
        engine.log(f"★ダンジョン地下{engine.dungeon_level}階へ降り立った！", (255, 200, 100))

        # Procedural quest: exploration progress
        engine._progress_generated_quests("explore", "depth", 1)

        # Generate new dungeon
        engine.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT, floor_level=engine.dungeon_level)
        engine.game_map.generate_dungeon()
        engine.player.x, engine.player.y = engine.game_map.start_pos
        engine.pet.x = engine.player.x + 1
        engine.pet.y = engine.player.y

        # Reset entity manager
        engine.entity_manager.clear()
        engine.entity_manager.add_entity(engine.player)
        engine.entity_manager.add_entity(engine.pet)
        engine.entity_manager.items_on_ground.clear()
        engine.entity_manager.resource_nodes.clear()
        engine._spawn_dungeon()

        # Altar position
        rx, ry = engine.game_map.rooms[0].center
        engine.altar_pos = (rx + 2, ry)
        engine.game_map.compute_fov(engine.player.x, engine.player.y, radius=8)

        # Dungeon visit tracking
        if hasattr(engine.player, "dungeon_floors_visited"):
            engine.player.dungeon_floors_visited.add((1, engine.dungeon_level))
        if hasattr(engine.player, "max_dungeon_depth"):
            engine.player.max_dungeon_depth = max(
                engine.player.max_dungeon_depth, engine.dungeon_level
            )

        # Meta progression
        if hasattr(engine.player, "meta_progression"):
            engine.player.meta_progression["cumulative_depth_stat"] = (
                engine.player.meta_progression.get("cumulative_depth_stat", 0) + 1
            )

        # Achievements & meta goals
        if hasattr(engine, "achievement_manager"):
            engine.achievement_manager.check_all_achievements(engine.player, engine)
        if hasattr(engine, "meta_progression_manager"):
            engine.meta_progression_manager.check_meta_goals(engine.player, engine)

        # Tutorial trigger
        if engine.dungeon_level >= 10:
            engine.check_tutorial_triggers("reach_depth_10")

        # Auto-save
        from advanced_systems import SaveSystem
        msg = SaveSystem.save(engine)
        engine.log(f"[Auto] {msg}", (80, 200, 80))

        # Win condition check
        engine.check_win_condition()
        return True

    def check_win_condition(self) -> bool:
        """Check victory condition."""
        engine = self.engine

        if engine.game_state_machine.current != "playing":
            return False

        # Read win_depth from config instead of hardcoding
        try:
            from config import get_config

            win_depth = get_config("game.dungeon.win_depth", 20)
        except ImportError:
            win_depth = 20

        if engine.dungeon_level >= win_depth:
            # void_boss defeated check (future: boss-specific flag)
            engine.game_state_machine.transition("victory")
            engine.game_state_data.current_state = GameState.VICTORY
            engine.game_state_data.game_state = "victory"
            engine.log("【勝利】ヴォイド・ボスを撃破し、深淵から脱出した！", (255, 215, 0), level="SUCCESS")
            engine.run_summary = engine._build_run_summary()
            engine._present_run_summary(engine.run_summary)
            engine._record_run_history(engine.run_summary)
            return True
        return False

    def _spawn_dungeon(self) -> None:
        """Spawn dungeon entities."""
        try:
            self.engine.dungeon_spawner(self.engine.kernel, self.engine)
        except Exception as e:
            logger.exception("Failed to spawn dungeon entities: %s", e)
            from exceptions import ResourceLoadError

            raise ResourceLoadError(f"Dungeon spawn failure: {e}") from e
