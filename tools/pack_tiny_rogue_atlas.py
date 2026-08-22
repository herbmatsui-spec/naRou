#!/usr/bin/env python3
"""
Pack Tiny Rogue tiles into a single 16x16 atlas.
Uses a simple shelf packing algorithm.
Handles directional tiles (4 directions stacked vertically).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

TILE_SIZE = 16
TILES_DIR = Path("assets/tiles/tiny_rogue/tiles")
OUTPUT_PNG = Path("assets/tiles/tiny_rogue_atlas_16x16.png")
OUTPUT_JSON = Path("assets/tiles/tiny_rogue_atlas_16x16.json")
MANIFEST_CSV = Path("assets/tiles/tiny_rogue/tiny_rogue_manifest.csv")

# Atlas dimensions
ATLAS_WIDTH = 512
ATLAS_HEIGHT = 512
PADDING = 1  # 1px padding between tiles to avoid bleeding

# Categories that have 4-directional frames (grouped by 4 consecutive tiles)
DIRECTIONAL_CATEGORIES = {"monster", "monster_variant", "player_npc"}


def load_manifest() -> list[tuple[int, str, str, str]]:
    """Load manifest CSV: returns list of (index, filename, suggested_id, category)."""
    import csv

    rows = []
    with open(MANIFEST_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                (
                    int(row["index"]),
                    row["filename"],
                    row["suggested_id"],
                    row["category"],
                )
            )
    return rows


def get_base_id(suggested_id: str, group_index: int) -> str:
    """Generate base ID for a directional group.
    e.g., TR_MONSTER_01, TR_MONSTER_02, TR_MONSTER_03 for 3 groups of 4.
    """
    # Extract prefix (TR_MONSTER, TR_MONSTER_VAR, TR_PLAYER)
    match = re.match(r"^(TR_[A-Z_]+)_\d+$", suggested_id)
    if match:
        prefix = match.group(1)
        return f"{prefix}_{group_index + 1:02d}"
    return suggested_id


def pack_atlas(
    tiles: list[tuple[int, str, str, str]],
) -> tuple[Image.Image, dict[str, dict[str, Any]]]:
    """Pack tiles into atlas. Returns (atlas_image, metadata_dict)."""
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    meta: dict[str, dict[str, Any]] = {}

    x = 0
    y = 0
    row_height = 0

    i = 0
    group_counters = {}  # category -> group count

    while i < len(tiles):
        _idx, filename, suggested_id, category = tiles[i]

        # Check if this is a directional tile group (4 consecutive tiles in a directional category)
        if category in DIRECTIONAL_CATEGORIES and i + 3 < len(tiles):
            # Check if next 3 tiles are same category and consecutive indices
            group = tiles[i : i + 4]
            if all(t[3] == category for t in group) and all(
                t[0] == group[0][0] + j for j, t in enumerate(group)
            ):
                # This is a 4-direction group - pack vertically
                group_count = group_counters.get(category, 0)
                base_id = get_base_id(suggested_id, group_count)
                group_counters[category] = group_count + 1

                print(
                    f"Directional group: category={category}, base_id={base_id}, tiles={[t[2] for t in group]}"
                )

                # Load all 4 direction frames
                dir_images = []
                for j, (_, fn, _, _) in enumerate(group):
                    tile_path = TILES_DIR / fn
                    if tile_path.exists():
                        img = Image.open(tile_path).convert("RGBA")
                        if img.size != (TILE_SIZE, TILE_SIZE):
                            img = img.resize((TILE_SIZE, TILE_SIZE), Image.NEAREST)
                        dir_images.append(img)
                    else:
                        dir_images.append(Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0)))

                # Check row space
                if x + TILE_SIZE + PADDING > ATLAS_WIDTH:
                    x = 0
                    y += row_height + PADDING
                    row_height = 0

                # Height for 4 directions stacked
                stack_height = TILE_SIZE * 4
                if y + stack_height + PADDING > ATLAS_HEIGHT:
                    raise RuntimeError(
                        f"Atlas too small! Need larger than {ATLAS_WIDTH}x{ATLAS_HEIGHT}"
                    )

                # Paste 4 frames vertically
                for dir_idx, dir_img in enumerate(dir_images):
                    atlas.paste(dir_img, (x, y + dir_idx * TILE_SIZE))

                # Record metadata for the base tile (directions=4, height=16 per direction)
                meta[base_id] = {
                    "x": x,
                    "y": y,
                    "width": TILE_SIZE,
                    "height": TILE_SIZE,  # per direction
                    "variants": 1,
                    "animated": True,
                    "frames": 4,
                    "fps": 8,
                    "directions": 4,
                }

                x += TILE_SIZE + PADDING
                row_height = max(row_height, stack_height)
                i += 4
                continue

        # Regular single tile
        tile_path = TILES_DIR / filename
        if not tile_path.exists():
            print(f"Warning: {tile_path} not found, skipping")
            i += 1
            continue

        tile_img = Image.open(tile_path).convert("RGBA")
        if tile_img.size != (TILE_SIZE, TILE_SIZE):
            tile_img = tile_img.resize((TILE_SIZE, TILE_SIZE), Image.NEAREST)

        # Check if we need to move to next row
        if x + TILE_SIZE + PADDING > ATLAS_WIDTH:
            x = 0
            y += row_height + PADDING
            row_height = 0

        if y + TILE_SIZE + PADDING > ATLAS_HEIGHT:
            raise RuntimeError(f"Atlas too small! Need larger than {ATLAS_WIDTH}x{ATLAS_HEIGHT}")

        # Paste tile
        atlas.paste(tile_img, (x, y))

        # Record metadata
        meta[suggested_id] = {
            "x": x,
            "y": y,
            "width": TILE_SIZE,
            "height": TILE_SIZE,
            "variants": 1,
            "animated": False,
            "frames": 1,
            "fps": 1,
            "directions": 1,
        }

        x += TILE_SIZE + PADDING
        row_height = max(row_height, TILE_SIZE)
        i += 1

    # Crop atlas to used area
    used_width = 0
    used_height = 0
    for m in meta.values():
        used_width = max(used_width, m["x"] + m["width"])
        used_height = max(used_height, m["y"] + m["height"])

    atlas = atlas.crop((0, 0, used_width, used_height))
    return atlas, meta


def main():
    print("Loading manifest...")
    tiles = load_manifest()
    print(f"Found {len(tiles)} tiles")

    print("Packing atlas...")
    atlas_img, meta = pack_atlas(tiles)

    print(f"Atlas size: {atlas_img.size}")
    print(f"Saving PNG to {OUTPUT_PNG}")
    atlas_img.save(OUTPUT_PNG)

    # Write metadata JSON
    metadata = {
        "tile_size": TILE_SIZE,
        "atlas_width": atlas_img.width,
        "atlas_height": atlas_img.height,
        "tiles": meta,
    }
    print(f"Saving JSON to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
