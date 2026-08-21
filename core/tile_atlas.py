"""
Unified Tile Atlas for naRou.
Loads tileset_def.json and atlas metadata (16x16, 32x32, 64x64).
Provides UV lookup for tile_id + variant + frame + direction + state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Import animated tile registration
try:
    from core.animated_tile import register_animated_tiles
except ImportError:

    def register_animated_tiles(tile_atlas):
        pass


@dataclass
class TileUV:
    """UV coordinates in atlas texture (pixels)."""

    x: int
    y: int
    w: int
    h: int
    scale: str  # "16" | "32" | "64"


@dataclass
class TileDef:
    """Tile definition from tileset_def.json."""

    tile_id: str
    file: str  # Key in atlas metadata (e.g., "WALL_DUNGEON")
    variants: int = 1
    animated: bool = False
    frames: int = 1
    fps: int = 10
    variant_width: int = 16
    frame_width: int = 0  # 0 = use variant_width or base width
    directions: int = 1
    states: list[str] = None
    autotile: bool = False
    atlas_scale: str = "16"
    anchor_x: float = 0.5
    anchor_y: float = 1.0

    def __post_init__(self):
        if self.states is None:
            self.states = ["idle"]
        if self.frame_width == 0:
            self.frame_width = self.variant_width


@dataclass
class AnimState:
    """Runtime animation state for a tile/entity."""

    tile_id: str
    atlas: TileAtlas
    frame: int = 0
    timer: float = 0.0
    fps: int = 10
    loop: bool = True
    direction: int = 0
    state: str = "idle"
    variant: int = 0

    def update(self, dt: float) -> bool:
        """Advance animation. Returns True if frame changed."""
        self.timer += dt
        frame_time = 1.0 / self.fps if self.fps > 0 else 1.0
        if self.timer >= frame_time:
            self.timer = 0.0
            td = self.atlas.defs.get(self.tile_id)
            if td:
                max_frames = td.frames
                self.frame = (self.frame + 1) % max_frames
            return True
        return False

    def get_uv(self, scale: str | None = None) -> TileUV:
        """Get current frame UV."""
        s = scale or self.atlas.default_scale
        return self.atlas.get_uv(
            self.tile_id,
            variant=self.variant,
            frame=self.frame,
            direction=self.direction,
            state=self.state,
            scale=s,
        )


# 4-bit autotile mapping: bit0=up, bit1=right, bit2=down, bit3=left
AUTOTILE_MAP = {
    0b0000: 0,  # isolated
    0b0001: 1,  # up
    0b0010: 2,  # right
    0b0100: 4,  # down
    0b1000: 8,  # left
    0b0011: 3,  # up+right
    0b0110: 6,  # right+down
    0b1100: 12,  # down+left
    0b1001: 9,  # left+up
    0b0101: 5,  # up+down
    0b1010: 10,  # left+right
    0b0111: 7,  # up+right+down
    0b1110: 14,  # right+down+left
    0b1101: 13,  # down+left+up
    0b1011: 11,  # left+up+right
    0b1111: 15,  # all four
}


class TileAtlas:
    """Unified tile atlas loader and UV provider."""

    def __init__(
        self, def_path: str = "assets/tiles/tileset_def.json", default_scale: str = "16"
    ):
        self.def_path = Path(def_path)
        self.default_scale = default_scale
        self.defs: dict[str, TileDef] = {}
        self.atlas_meta: dict[str, dict[str, Any]] = {}  # scale -> metadata
        self._load()

    def _load(self) -> None:
        """Load tileset_def.json and all atlas metadata files."""
        # 1. Load tile definitions
        with open(self.def_path) as f:
            raw = json.load(f)

        for tile_id, d in raw.get("tiles", {}).items():
            self.defs[tile_id] = TileDef(tile_id=tile_id, **d)

        # 2. Load atlas metadata for each scale
        for scale in ("16", "32", "64", "tiny_rogue_16"):
            if scale == "tiny_rogue_16":
                meta_path = self.def_path.parent / "tiny_rogue_atlas_16x16.json"
            else:
                meta_path = self.def_path.parent / f"tileset_{scale}x{scale}.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    self.atlas_meta[scale] = json.load(f)

        # 3. Register animated tiles (water, lava, etc.)
        register_animated_tiles(self)

    def get_uv(
        self,
        tile_id: str,
        variant: int = 0,
        frame: int = 0,
        direction: int = 0,
        state: str = "idle",
        scale: str | None = None,
    ) -> TileUV:
        """Get UV coordinates for a specific tile configuration."""
        s = scale or self.default_scale
        td = self.defs.get(tile_id)
        if not td:
            raise KeyError(f"TileDef not found: {tile_id}")

        meta = self.atlas_meta.get(s)
        if not meta:
            raise KeyError(f"Atlas metadata not loaded for scale: {s}")

        file_key = td.file
        if "tiles" not in meta or file_key not in meta["tiles"]:
            raise KeyError(f"Tile '{file_key}' not found in {s} atlas metadata")

        base = meta["tiles"][file_key]
        bx, by = base["x"], base["y"]
        _bw, bh = base["width"], base["height"]

        # Variant offset (horizontal)
        vw = td.variant_width
        vx = variant * vw

        # Frame offset (horizontal, after variant)
        fw = td.frame_width
        fx = frame * fw

        # Direction offset (vertical stacking)
        dy = direction * bh

        return TileUV(bx + vx + fx, by + dy, fw, bh, s)

    def get_autotile_variant(self, tile_id: str, neighbor_mask: int) -> int:
        """Convert 4-bit neighbor mask to autotile variant index (0-15)."""
        return AUTOTILE_MAP.get(neighbor_mask & 0xF, 0)

    def calculate_neighbor_mask(
        self, tile_map: list[list[str]], x: int, y: int, target_tile: str
    ) -> int:
        """Calculate 4-bit neighbor mask for autotiling.
        bit0=up, bit1=right, bit2=down, bit3=left
        """
        h = len(tile_map)
        w = len(tile_map[0]) if h > 0 else 0
        mask = 0
        if y > 0 and tile_map[y - 1][x] == target_tile:
            mask |= 1  # up
        if x < w - 1 and tile_map[y][x + 1] == target_tile:
            mask |= 2  # right
        if y < h - 1 and tile_map[y + 1][x] == target_tile:
            mask |= 4  # down
        if x > 0 and tile_map[y][x - 1] == target_tile:
            mask |= 8  # left
        return mask

    def create_anim_state(
        self,
        tile_id: str,
        variant: int = 0,
        direction: int = 0,
        state: str = "idle",
        fps: int | None = None,
        loop: bool = True,
    ) -> AnimState:
        """Create an AnimState for runtime animation."""
        td = self.defs.get(tile_id)
        if not td:
            raise KeyError(f"TileDef not found: {tile_id}")
        return AnimState(
            tile_id=tile_id,
            atlas=self,
            variant=variant,
            direction=direction,
            state=state,
            fps=fps or td.fps,
            loop=loop,
        )

    def get_tcod_tile_rect(
        self,
        tile_id: str,
        variant: int = 0,
        frame: int = 0,
        direction: int = 0,
        state: str = "idle",
        scale: str = "32",
    ) -> tuple[int, int, int, int]:
        """Get (x, y, w, h) in pixels for tcod tileset loading."""
        uv = self.get_uv(tile_id, variant, frame, direction, state, scale)
        return (uv.x, uv.y, uv.w, uv.h)

    def get_master_image_path(self, tile_id: str, scale: str | None = None) -> Path | None:
        """Get path to master atlas image for a tile."""
        s = scale or self.default_scale
        td = self.defs.get(tile_id)
        if not td:
            return None
        # Use the requested scale for the master image
        img_scale = s
        return self.def_path.parent / f"tileset_{img_scale}x{img_scale}.png"

    def get_all_tile_ids(self) -> list[str]:
        """Get list of all defined tile IDs."""
        return list(self.defs.keys())

    def has_tile(self, tile_id: str) -> bool:
        """Check if tile_id is defined."""
        return tile_id in self.defs


# Global instance for convenience
TILE_ATLAS = TileAtlas()


if __name__ == "__main__":
    # Quick test
    atlas = TileAtlas()
    print(f"Loaded {len(atlas.defs)} tile definitions")
    print(f"Available scales: {list(atlas.atlas_meta.keys())}")

    # Test UV lookup
    uv = atlas.get_uv("TILE_WALL", variant=0, scale="16")
    print(f"TILE_WALL variant=0: ({uv.x}, {uv.y}, {uv.w}, {uv.h}) @ {uv.scale}")

    uv = atlas.get_uv("TILE_WATER", frame=1, scale="16")
    print(f"TILE_WATER frame=1: ({uv.x}, {uv.y}, {uv.w}, {uv.h}) @ {uv.scale}")

    uv = atlas.get_uv("PLAYER", direction=1, frame=2, scale="32")
    print(f"PLAYER dir=1 frame=2: ({uv.x}, {uv.y}, {uv.w}, {uv.h}) @ {uv.scale}")

    # Test autotile
    mask = 0b0111  # up+right+down
    variant = atlas.get_autotile_variant("TILE_WALL", mask)
    print(f"Autotile mask {bin(mask)} -> variant {variant}")

    # Test neighbor mask calculation
    test_map = [
        ["TILE_WALL", "TILE_WALL", "TILE_WALL"],
        ["TILE_WALL", "TILE_FLOOR", "TILE_WALL"],
        ["TILE_WALL", "TILE_WALL", "TILE_WALL"],
    ]
    mask = atlas.calculate_neighbor_mask(test_map, 1, 1, "TILE_WALL")
    print(
        f"Center wall neighbor mask: {bin(mask)} -> variant {atlas.get_autotile_variant('TILE_WALL', mask)}"
    )

    print("All tests passed!")
