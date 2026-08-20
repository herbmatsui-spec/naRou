"""Animated tile system for water, lava, and other animated terrain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnimatedTile:
    """Represents an animated tile with multiple frames."""

    tile_ids: list[str]
    fps: int
    loop: bool = True

    def __post_init__(self):
        if not self.tile_ids:
            raise ValueError("AnimatedTile must have at least one tile_id")
        if self.fps <= 0:
            raise ValueError("fps must be positive")

    def get_frame(self, frame_index: int) -> str:
        """Get tile ID for a specific frame index."""
        return self.tile_ids[frame_index % len(self.tile_ids)]

    def get_frame_at_time(self, time_seconds: float) -> str:
        """Get tile ID for a given time in seconds."""
        frame_index = int(time_seconds * self.fps)
        return self.get_frame(frame_index)

    @property
    def frame_count(self) -> int:
        return len(self.tile_ids)

    @property
    def frame_duration(self) -> float:
        return 1.0 / self.fps


# Predefined animated tiles using emote spritesheet frames
# These will be registered when ENABLE_TINY_ROGUE_GFX is enabled

ANIMATED_TILES = {
    "water": AnimatedTile(
        tile_ids=[
            "TR_EFFECT_02",  # water frame 1
            "TR_EFFECT_03",  # water frame 2
            "TR_EFFECT_04",  # water frame 3
        ],
        fps=5,
        loop=True,
    ),
    "lava": AnimatedTile(
        tile_ids=[
            "TR_EFFECT_05",  # lava frame 1
            "TR_EFFECT_06",  # lava frame 2
            "TR_EFFECT_07",  # lava frame 3
        ],
        fps=8,
        loop=True,
    ),
    "torch": AnimatedTile(
        tile_ids=[
            "TR_DECOR_01",  # torch frame 1
            "TR_DECOR_02",  # torch frame 2
            "TR_DECOR_03",  # torch frame 3
            "TR_DECOR_04",  # torch frame 4
        ],
        fps=8,
        loop=True,
    ),
    "magic_portal": AnimatedTile(
        tile_ids=[
            "TR_EFFECT_01",  # portal frame 1
            "TR_EFFECT_08",  # portal frame 2
            "TR_EFFECT_09",  # portal frame 3
            "TR_EFFECT_10",  # portal frame 4
        ],
        fps=12,
        loop=True,
    ),
}


def get_animated_tile(name: str) -> AnimatedTile | None:
    """Get an animated tile by name."""
    return ANIMATED_TILES.get(name)


def register_animated_tiles(tile_atlas) -> None:
    """Register animated tiles with the TileAtlas when feature flag is enabled."""
    try:
        from feature_flags import is_enabled

        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return
    except ImportError:
        pass

    # Add animated tile definitions to tile_atlas for runtime lookup
    if not hasattr(tile_atlas, "animated_tiles"):
        tile_atlas.animated_tiles = {}

    for name, anim_tile in ANIMATED_TILES.items():
        tile_atlas.animated_tiles[name] = anim_tile
