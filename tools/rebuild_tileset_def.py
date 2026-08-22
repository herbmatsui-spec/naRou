#!/usr/bin/env python3
"""
Rebuild tileset_def.json from scratch: original tiles + tiny_rogue atlas tiles.
"""

from __future__ import annotations

import json
from pathlib import Path

ORIGINAL_DEF = Path("assets/tiles/tileset_def.json")
ATLAS_META_PATH = Path("assets/tiles/tileset_tiny_rogue_16x16.json")
OUTPUT_DEF = Path("assets/tiles/tileset_def.json.new")

# Original tile IDs to preserve
ORIGINAL_TILE_IDS = {
    "TILE_WALL",
    "TILE_FLOOR",
    "TILE_STAIRS_DOWN",
    "TILE_STAIRS_UP",
    "TILE_WATER",
    "TILE_TRAP",
    "PLAYER",
    "PET",
    "ENEMY_GOBLIN",
    "ITEM_POTION",
    "ITEM_WEAPON",
    "ITEM_ARMOR",
    "ITEM_GOLD",
    "DECOR_TORCH",
    "DECOR_BLOOD",
    "EFFECT_MAGIC",
}

# Load original defs
with open(ORIGINAL_DEF) as f:
    original = json.load(f)

# Keep only original tiles
original_tiles = {k: v for k, v in original["tiles"].items() if k in ORIGINAL_TILE_IDS}

# Load atlas metadata
with open(ATLAS_META_PATH) as f:
    atlas_meta = json.load(f)

atlas_tiles = set(atlas_meta.get("tiles", {}).keys())
print(f"Atlas has {len(atlas_tiles)} tile entries")


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
                "variants": 12,
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

# Merge: original + new
merged_tiles = {**original_tiles, **new_tiles}

# Write new def file
output = {"version": "1.0", "tile_size": 16, "tiles": merged_tiles}

with open(OUTPUT_DEF, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(
    f"Generated {OUTPUT_DEF} with {len(original_tiles)} original + {len(new_tiles)} new = {len(merged_tiles)} total tiles"
)
