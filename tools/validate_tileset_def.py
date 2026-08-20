#!/usr/bin/env python3
"""
Validate tileset_def.json against actual atlas metadata and image files.
Checks for missing tiles, mismatched definitions, and autotile readiness.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def validate_tileset_def() -> ValidationResult:
    base = Path("assets/tiles")
    errors = []
    warnings = []
    info = []

    # 1. Load tileset_def.json
    def_path = base / "tileset_def.json"
    if not def_path.exists():
        return ValidationResult(False, [f"Missing: {def_path}"], [], [])
    defs = load_json(def_path)

    # 2. Load atlas metadata for each scale
    scales = ["16", "32", "64", "tiny_rogue_16"]
    atlas_meta = {}
    for scale in scales:
        if scale == "tiny_rogue_16":
            meta_path = base / "tileset_tiny_rogue_16x16.json"
        else:
            meta_path = base / f"tileset_{scale}x{scale}.json"
        if meta_path.exists():
            atlas_meta[scale] = load_json(meta_path)
            info.append(f"Loaded metadata: {meta_path}")
        else:
            warnings.append(f"Missing metadata: {meta_path}")

    # 3. Check image files exist
    for scale in scales:
        if scale == "tiny_rogue_16":
            img_path = base / "tileset_tiny_rogue_16x16.png"
        else:
            img_path = base / f"tileset_{scale}x{scale}.png"
        if img_path.exists():
            info.append(f"Found image: {img_path} ({img_path.stat().st_size} bytes)")
        else:
            errors.append(f"Missing image: {img_path}")

    # 4. Validate each tile definition
    tiles = defs.get("tiles", {})
    info.append(f"tileset_def.json defines {len(tiles)} tiles")

    for tile_id, tile_def in tiles.items():
        file_key = tile_def.get("file", "")
        atlas_scale = tile_def.get("atlas_scale", "16")
        variants = tile_def.get("variants", 1)
        animated = tile_def.get("animated", False)
        frames = tile_def.get("frames", 1)
        variant_width = tile_def.get("variant_width", 16)
        frame_width = tile_def.get("frame_width", 0)

        # Check atlas_scale metadata exists
        if atlas_scale not in atlas_meta:
            errors.append(f"{tile_id}: atlas_scale '{atlas_scale}' metadata not loaded")
            continue

        meta = atlas_meta[atlas_scale]
        if "tiles" not in meta:
            errors.append(
                f"{tile_id}: metadata for scale {atlas_scale} has no 'tiles' key"
            )
            continue

        if file_key not in meta["tiles"]:
            errors.append(
                f"{tile_id}: file '{file_key}' not found in {atlas_scale} atlas metadata"
            )
            continue

        meta_tile = meta["tiles"][file_key]
        meta_w = meta_tile.get("width", 0)
        meta_h = meta_tile.get("height", 0)

        # Check variant width consistency
        if variants > 1:
            expected_w = variant_width * variants
            if meta_w != expected_w:
                warnings.append(
                    f"{tile_id}: variants={variants} * variant_width={variant_width} "
                    f"= {expected_w}, but atlas width={meta_w}"
                )

        # Check frame width consistency
        if animated and frames > 1:
            fw = frame_width or meta_w
            expected_w = fw * frames
            if meta_w != expected_w:
                warnings.append(
                    f"{tile_id}: frames={frames} * frame_width={fw} "
                    f"= {expected_w}, but atlas width={meta_w}"
                )

        # Check directions (vertical stacking)
        directions = tile_def.get("directions", 1)
        if directions > 1:
            # Note: metadata only has single tile entry, directions are vertical stack
            info.append(f"{tile_id}: directions={directions} (vertical stack in atlas)")

        # Autotile check
        if tile_def.get("autotile", False):
            if variants != 16:
                warnings.append(
                    f"{tile_id}: autotile=true but variants={variants} (expected 16 for 4-bit mask)"
                )
            info.append(f"{tile_id}: autotile enabled, will use 4-bit neighbor mask")

        info.append(
            f"  {tile_id}: file={file_key}, scale={atlas_scale}, "
            f"variants={variants}, animated={animated}, frames={frames}, "
            f"dirs={directions}, atlas_wh=({meta_w}x{meta_h})"
        )

    # 5. Check for tiles in metadata but not in defs (orphaned)
    for scale in scales:
        if scale in atlas_meta:
            meta_tiles = set(atlas_meta[scale].get("tiles", {}).keys())
            def_files = {t.get("file") for t in tiles.values()}
            orphaned = meta_tiles - def_files
            if orphaned:
                warnings.append(
                    f"Scale {scale}: orphaned in metadata (not in defs): {orphaned}"
                )

    ok = len(errors) == 0
    return ValidationResult(ok, errors, warnings, info)


def main():
    print("=" * 60)
    print("tileset_def.json Validation")
    print("=" * 60)

    result = validate_tileset_def()

    for msg in result.info:
        print(f"[INFO]  {msg}")
    for msg in result.warnings:
        print(f"[WARN]  {msg}")
    for msg in result.errors:
        print(f"[ERROR] {msg}")

    print("=" * 60)
    if result.ok:
        print("VALIDATION PASSED")
    else:
        print(f"VALIDATION FAILED: {len(result.errors)} error(s)")
    print("=" * 60)

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
