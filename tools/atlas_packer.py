#!/usr/bin/env python3
"""
Universal Atlas Packer CLI
Packs individual tile PNGs into a unified atlas with metadata JSON.
Supports Kenney-style tile sheets and custom tile collections.

Usage:
    python tools/atlas_packer.py <input_dir> <output_prefix> [options]

Examples:
    # Pack Kenney Tiny Rogue tiles
    python tools/atlas_packer.py assets/tiles/tiny_rogue/tiles assets/tiles/tileset_tiny_rogue_16x16 \\
        --manifest assets/tiles/tiny_rogue/tiny_rogue_manifest.csv \\
        --tile-size 16 --padding 1

    # Pack custom tiles with simple naming
    python tools/atlas_packer.py my_tiles assets/tiles/my_atlas \\
        --tile-size 32 --max-size 1024
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image


def load_manifest(manifest_path: Path) -> list[tuple[int, str, str, str]]:
    """Load manifest CSV: returns list of (index, filename, suggested_id, category)."""
    rows = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
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


def scan_directory(
    tiles_dir: Path, pattern: str = "*.png"
) -> list[tuple[int, str, str, str]]:
    """Scan directory for PNG files, generate manifest from filenames."""
    files = sorted(tiles_dir.glob(pattern))
    rows = []
    for i, f in enumerate(files):
        # Use filename stem as suggested_id
        suggested_id = f.stem.upper()
        # Guess category from prefix
        category = "custom"
        if suggested_id.startswith("FLOOR"):
            category = "floor"
        elif suggested_id.startswith("WALL"):
            category = "wall"
        elif suggested_id.startswith("ITEM"):
            category = "item"
        elif suggested_id.startswith("MONSTER"):
            category = "monster"
        elif suggested_id.startswith("EFFECT"):
            category = "effect"
        elif suggested_id.startswith("UI"):
            category = "ui"
        elif suggested_id.startswith("DECOR"):
            category = "decoration"
        rows.append((i, f.name, suggested_id, category))
    return rows


def pack_atlas(
    tiles: list[tuple[int, str, str, str]],
    tiles_dir: Path,
    tile_size: int = 16,
    max_atlas_size: int = 2048,
    padding: int = 1,
    directional_categories: set | None = None,
) -> tuple[Image.Image, dict[str, dict[str, Any]]]:
    """Pack tiles into atlas. Returns (atlas_image, metadata_dict)."""
    if directional_categories is None:
        directional_categories = {"monster", "monster_variant", "player_npc"}

    atlas = Image.new("RGBA", (max_atlas_size, max_atlas_size), (0, 0, 0, 0))
    meta: dict[str, dict[str, Any]] = {}

    x = 0
    y = 0
    row_height = 0
    i = 0
    group_counters = {}

    while i < len(tiles):
        _idx, filename, suggested_id, category = tiles[i]
        tile_path = tiles_dir / filename

        if not tile_path.exists():
            print(f"Warning: {tile_path} not found, skipping", file=sys.stderr)
            i += 1
            continue

        tile_img = Image.open(tile_path).convert("RGBA")
        if tile_img.size != (tile_size, tile_size):
            tile_img = tile_img.resize((tile_size, tile_size), Image.NEAREST)

        # Check for directional group (4 consecutive tiles in same category)
        if category in directional_categories and i + 3 < len(tiles):
            group = tiles[i : i + 4]
            if all(t[3] == category for t in group) and all(
                t[0] == group[0][0] + j for j, t in enumerate(group)
            ):
                # Directional group - pack vertically
                group_count = group_counters.get(category, 0)
                match = re.match(r"^(TR_[A-Z_]+)_\d+$", suggested_id)
                if match:
                    prefix = match.group(1)
                    base_id = f"{prefix}_{group_count + 1:02d}"
                else:
                    base_id = suggested_id
                group_counters[category] = group_count + 1

                # Load all 4 frames
                dir_images = []
                for j, (_, fn, _, _) in enumerate(group):
                    tp = tiles_dir / fn
                    if tp.exists():
                        img = Image.open(tp).convert("RGBA")
                        if img.size != (tile_size, tile_size):
                            img = img.resize((tile_size, tile_size), Image.NEAREST)
                        dir_images.append(img)
                    else:
                        dir_images.append(
                            Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
                        )

                # Check row space
                if x + tile_size + padding > max_atlas_size:
                    x = 0
                    y += row_height + padding
                    row_height = 0

                stack_height = tile_size * 4
                if y + stack_height + padding > max_atlas_size:
                    raise RuntimeError(
                        f"Atlas too small! Need larger than {max_atlas_size}x{max_atlas_size}"
                    )

                # Paste 4 frames vertically
                for dir_idx, dir_img in enumerate(dir_images):
                    atlas.paste(dir_img, (x, y + dir_idx * tile_size))

                meta[base_id] = {
                    "x": x,
                    "y": y,
                    "width": tile_size,
                    "height": tile_size,
                    "variants": 1,
                    "animated": True,
                    "frames": 4,
                    "fps": 8,
                    "directions": 4,
                }

                x += tile_size + padding
                row_height = max(row_height, stack_height)
                i += 4
                continue

        # Regular single tile
        if x + tile_size + padding > max_atlas_size:
            x = 0
            y += row_height + padding
            row_height = 0

        if y + tile_size + padding > max_atlas_size:
            raise RuntimeError(
                f"Atlas too small! Need larger than {max_atlas_size}x{max_atlas_size}"
            )

        atlas.paste(tile_img, (x, y))

        meta[suggested_id] = {
            "x": x,
            "y": y,
            "width": tile_size,
            "height": tile_size,
            "variants": 1,
            "animated": False,
            "frames": 1,
            "fps": 1,
            "directions": 1,
        }

        x += tile_size + padding
        row_height = max(row_height, tile_size)
        i += 1

    # Crop to used area
    used_width = 0
    used_height = 0
    for m in meta.values():
        used_width = max(used_width, m["x"] + m["width"])
        used_height = max(used_height, m["y"] + m["height"])

    atlas = atlas.crop((0, 0, used_width, used_height))
    return atlas, meta


def generate_tileset_def(
    meta: dict[str, dict[str, Any]], tile_size: int, scale_name: str, output_path: Path
) -> None:
    """Generate a minimal tileset_def.json for the packed atlas."""
    tiles = {}
    for tile_id, m in meta.items():
        # Detect category from tile_id prefix
        if tile_id.startswith("TR_FLOOR"):
            cat = "floor"
        elif tile_id.startswith("TR_WALL_VAR"):
            cat = "wall_variant"
        elif tile_id.startswith("TR_WALL"):
            cat = "wall"
        elif tile_id.startswith("TR_DECOR"):
            cat = "decoration"
        elif tile_id.startswith("TR_ITEM"):
            cat = "item"
        elif tile_id.startswith("TR_MONSTER_VAR"):
            cat = "monster_variant"
        elif tile_id.startswith("TR_MONSTER"):
            cat = "monster"
        elif tile_id.startswith("TR_EFFECT"):
            cat = "effect"
        elif tile_id.startswith("TR_UI"):
            cat = "ui"
        elif tile_id.startswith("TR_PLAYER"):
            cat = "player_npc"
        else:
            cat = "misc"

        defn = {
            "file": tile_id,
            "atlas_scale": scale_name,
            "frame_width": m.get("width", tile_size),
            "variant_width": m.get("width", tile_size),
        }

        if cat in ("floor", "wall"):
            defn.update(
                {"variants": 12, "autotile": True, "directions": 1, "states": ["idle"]}
            )
        elif cat == "wall_variant":
            defn.update(
                {"variants": 1, "autotile": False, "directions": 1, "states": ["idle"]}
            )
        elif cat == "decoration":
            defn.update(
                {
                    "variants": 1,
                    "animated": m.get("animated", False),
                    "frames": m.get("frames", 1),
                    "fps": m.get("fps", 1),
                    "directions": 1,
                    "states": ["idle"],
                }
            )
        elif cat == "item":
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
        elif cat in ("monster", "monster_variant", "player_npc"):
            defn.update(
                {
                    "variants": 1,
                    "animated": True,
                    "frames": m.get("frames", 4),
                    "fps": m.get("fps", 8),
                    "directions": m.get("directions", 4),
                    "states": ["idle", "walk", "attack"],
                    "anchor_x": 0.5,
                    "anchor_y": 1.0,
                }
            )
        elif cat == "effect":
            defn.update(
                {
                    "variants": 1,
                    "animated": True,
                    "frames": m.get("frames", 3),
                    "fps": m.get("fps", 12),
                    "directions": 1,
                    "states": ["cast"],
                    "anchor_x": 0.5,
                    "anchor_y": 0.5,
                }
            )
        elif cat == "ui":
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
        else:
            defn.update(
                {"variants": 1, "animated": False, "directions": 1, "states": ["idle"]}
            )

        tiles[tile_id] = defn

    output = {"version": "1.0", "tile_size": tile_size, "tiles": tiles}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Universal Atlas Packer for tile-based games"
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing tile PNGs")
    parser.add_argument(
        "output_prefix",
        type=Path,
        help="Output prefix (e.g., assets/tiles/tileset_mypack_16x16)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="CSV manifest file (index,filename,suggested_id,category)",
    )
    parser.add_argument(
        "--tile-size", type=int, default=16, help="Tile size in pixels (default: 16)"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=2048,
        help="Maximum atlas dimension (default: 2048)",
    )
    parser.add_argument(
        "--padding", type=int, default=1, help="Padding between tiles (default: 1)"
    )
    parser.add_argument(
        "--scale-name",
        type=str,
        help="Scale name for tileset_def.json (default: derived from tile-size)",
    )
    parser.add_argument(
        "--directional-cats",
        nargs="+",
        default=["monster", "monster_variant", "player_npc"],
        help="Categories with 4-directional frames",
    )
    parser.add_argument(
        "--generate-def", action="store_true", help="Generate tileset_def.json"
    )
    parser.add_argument(
        "--def-output", type=Path, help="Output path for tileset_def.json"
    )

    args = parser.parse_args()

    tiles_dir = args.input_dir
    output_png = args.output_prefix.with_suffix(".png")
    output_json = args.output_prefix.with_suffix(".json")

    if not tiles_dir.exists():
        print(f"Error: Input directory {tiles_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Load tiles
    if args.manifest:
        tiles = load_manifest(args.manifest)
    else:
        tiles = scan_directory(tiles_dir)

    print(f"Found {len(tiles)} tiles")

    # Pack atlas
    print("Packing atlas...")
    atlas_img, meta = pack_atlas(
        tiles,
        tiles_dir,
        tile_size=args.tile_size,
        max_atlas_size=args.max_size,
        padding=args.padding,
        directional_categories=set(args.directional_cats),
    )

    print(f"Atlas size: {atlas_img.size}")
    print(f"Packed {len(meta)} tile entries")

    # Save outputs
    print(f"Saving PNG to {output_png}")
    atlas_img.save(output_png)

    metadata = {
        "tile_size": args.tile_size,
        "atlas_width": atlas_img.width,
        "atlas_height": atlas_img.height,
        "tiles": meta,
    }
    print(f"Saving JSON to {output_json}")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Generate tileset_def.json if requested
    if args.generate_def:
        scale_name = args.scale_name or f"custom_{args.tile_size}"
        def_output = args.def_output or args.output_prefix.with_name(
            f"tileset_{scale_name}.json"
        )
        print(f"Generating tileset_def.json to {def_output}")
        generate_tileset_def(meta, args.tile_size, scale_name, def_output)

    print("Done!")


if __name__ == "__main__":
    main()
