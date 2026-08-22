#!/usr/bin/env python3
"""
Generate TileDef entries for tiny_rogue tiles and merge into tileset_def.json.
Reads the actual atlas metadata to know which tile IDs exist.
"""

from __future__ import annotations

import json
from pathlib import Path

DEF_PATH = Path("assets/tiles/tileset_def.json")
ATLAS_META_PATH = Path("assets/tiles/tileset_tiny_rogue_16x16.json")
OUTPUT_DEF = Path("assets/tiles/tileset_def.json.new")

# Load existing defs
with open(DEF_PATH) as f:
    existing = json.load(f)

# Load atlas metadata to know which tile IDs exist
with open(ATLAS_META_PATH) as f:
    atlas_meta = json.load(f)

atlas_tiles = set(atlas_meta.get("tiles", {}).keys())
print(f"Atlas has {len(atlas_tiles)} tile entries: {sorted(atlas_tiles)}")


# Category detection from tile ID prefix
def detect_category(tile_id: str) -> str:
    if tile_id.startswith("TR_FLOOR"):
        return "floor"
    elif tile_id.startswith("TR_WALL_VAR"):
        return "wall_variant"
    elif tile_id.startswith("TR_WALL"):
        return "wall"
    elif tile_id.startswith("TR_DECOR"):
        return "decoration"
    elif tile_id.startswith("TR_ITEM"):
        return "item"
    elif tile_id.startswith("TR_MONSTER_VAR"):
        return "monster_variant"
    elif tile_id.startswith("TR_MONSTER"):
        return "monster"
    elif tile_id.startswith("TR_EFFECT"):
        return "effect"
    elif tile_id.startswith("TR_UI"):
        return "ui"
    elif tile_id.startswith("TR_PLAYER"):
        return "player_npc"
    else:
        return "misc"


# Build new tile definitions from atlas metadata
new_tiles = {}
for tile_id in sorted(atlas_tiles):
    category = detect_category(tile_id)
    meta = atlas_meta["tiles"][tile_id]

    # Base definition from atlas metadata
    defn = {
        "file": tile_id,
        "atlas_scale": "tiny_rogue_16",
        "frame_width": meta.get("width", 16),
        "variant_width": meta.get("width", 16),
    }

    # Category-specific properties, enhanced by atlas metadata
    if category in ("floor", "wall"):
        defn.update(
            {
                "variants": 12,  # 12 variants per row in source
                "autotile": True,
                "variant_width": 16,
                "directions": 1,
                "states": ["idle"],
            }
        )
    elif category == "wall_variant":
        defn.update(
            {
                "variants": 1,
                "autotile": False,
                "directions": 1,
                "states": ["idle"],
            }
        )
    elif category == "decoration":
        defn.update(
            {
                "variants": 1,
                "animated": meta.get("animated", False),
                "frames": meta.get("frames", 1),
                "fps": meta.get("fps", 1),
                "directions": 1,
                "states": ["idle"],
            }
        )
    elif category == "item":
        defn.update(
            {
                "variants": 1,
                "animated": meta.get("animated", False),
                "frames": meta.get("frames", 1),
                "fps": meta.get("fps", 1),
                "directions": 1,
                "states": ["idle"],
                "anchor_x": 0.5,
                "anchor_y": 0.5,
            }
        )
    elif category in ("monster", "monster_variant", "player_npc"):
        defn.update(
            {
                "variants": 1,
                "animated": meta.get("animated", True),
                "frames": meta.get("frames", 4),
                "fps": meta.get("fps", 8),
                "directions": meta.get("directions", 4),
                "states": ["idle", "walk", "attack"],
                "anchor_x": 0.5,
                "anchor_y": 1.0,
            }
        )
    elif category == "effect":
        defn.update(
            {
                "variants": 1,
                "animated": meta.get("animated", True),
                "frames": meta.get("frames", 3),
                "fps": meta.get("fps", 12),
                "directions": 1,
                "states": ["cast"],
                "anchor_x": 0.5,
                "anchor_y": 0.5,
            }
        )
    elif category == "ui":
        defn.update(
            {
                "variants": 1,
                "animated": False,
                "directions": 1,
                "states": ["idle"],
                "anchor_x": 0.5,
                "anchor_y": 0.5,
            }
        )
    else:  # misc
        defn.update(
            {
                "variants": 1,
                "animated": False,
                "directions": 1,
                "states": ["idle"],
            }
        )

    new_tiles[tile_id] = defn

# Merge with existing
existing["tiles"].update(new_tiles)

# Write new def file
with open(OUTPUT_DEF, "w", encoding="utf-8") as f:
    json.dump(existing, f, indent=2)

print(
    f"Generated {OUTPUT_DEF} with {len(new_tiles)} new tile defs (total {len(existing['tiles'])})"
)
