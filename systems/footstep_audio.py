"""Footstep audio system - plays terrain-specific footstep sounds."""

from __future__ import annotations

from feature_flags import is_enabled
from sound_manager import SoundManager


class FootstepAudioSystem:
    """Manages footstep sounds based on terrain type and entity movement."""

    # Terrain type mapping based on tile IDs
    TERRAIN_TILE_MAP = {
        "TILE_FLOOR": "stone",
        "TR_FLOOR_01": "stone",
        "TR_FLOOR_02": "stone",
        "TR_FLOOR_03": "stone",
        "TR_FLOOR_04": "stone",
        "TR_FLOOR_05": "dirt",
        "TR_FLOOR_06": "dirt",
        "TR_FLOOR_07": "grass",
        "TR_FLOOR_08": "grass",
        "TR_FLOOR_09": "sand",
        "TR_FLOOR_10": "sand",
        "TR_FLOOR_11": "snow",
        "TR_FLOOR_12": "snow",
        "TILE_WATER": "water",
        "TR_EFFECT_02": "water",
        "TILE_GRASS": "grass",
        "TILE_DIRT": "dirt",
        "TILE_SAND": "sand",
        "TILE_SNOW": "snow",
        "TILE_WOOD": "wood",
        "TILE_CARPET": "carpet",
        "TILE_STONE": "stone",
        "TILE_METAL": "metal",
        "TILE_GRAVEL": "gravel",
    }

    def __init__(self, game_map=None):
        self.game_map = game_map
        self._last_footstep_time = 0
        self._footstep_interval = 0.4  # seconds between footsteps

    def get_terrain_at(self, x: int, y: int) -> str:
        """Get terrain type at map coordinates."""
        if self.game_map and hasattr(self.game_map, "tiles"):
            try:
                tile_id = self.game_map.tiles[x][y]
                return self.TERRAIN_TILE_MAP.get(tile_id, "stone")
            except (IndexError, TypeError):
                pass
        return "stone"

    def on_entity_move(
        self,
        entity,
        old_x: int,
        old_y: int,
        new_x: int,
        new_y: int,
        current_time: float = 0.0,
        is_player: bool = False,
    ):
        """Call when an entity moves to play footstep sound."""
        if not is_enabled("ENABLE_AUDIO_PACK"):
            return

        # Throttle footstep sounds
        if current_time - self._last_footstep_time < self._footstep_interval:
            return
        self._last_footstep_time = current_time

        # Get terrain at new position
        terrain = self.get_terrain_at(new_x, new_y)

        # Determine direction for directional audio
        new_x - old_x
        new_y - old_y

        # Play footstep
        SoundManager.play_footstep(terrain)

        # Also trigger footstep particles if Tiny Rogue GFX enabled
        if is_enabled("ENABLE_TINY_ROGUE_GFX"):
            try:
                from core_framework import EventBus
                from fx_manager import FXManager

                # We can't easily access FXManager here without passing it
                # The game loop should handle particle spawning
            except ImportError:
                pass

    @staticmethod
    def get_terrain_for_tile(tile_id: str) -> str:
        """Static method to get terrain type for a tile ID."""
        return FootstepAudioSystem.TERRAIN_TILE_MAP.get(tile_id, "stone")


# Convenience function for direct use
def play_footstep_for_tile(tile_id: str):
    """Play footstep sound for a specific tile type."""
    terrain = FootstepAudioSystem.get_terrain_for_tile(tile_id)
    SoundManager.play_footstep(terrain)
