#!/usr/bin/env python3
"""
Visual regression test - generates reference screenshots for entity rendering.
Uses the core TCOD renderer to generate reference images.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.entity_renderer import EntityRenderer
from core.tile_atlas import TileAtlas


def generate_entity_reference_images():
    """Generate reference images for all entity states."""
    print("=" * 60)
    print("Generating Entity Reference Images")
    print("=" * 60)

    output_dir = Path("tools/visual_refs")
    output_dir.mkdir(parents=True, exist_ok=True)

    atlas = TileAtlas()
    entity_renderer = EntityRenderer(atlas)

    entity_types = ["PLAYER", "PET", "ENEMY_GOBLIN"]
    states = ["idle", "walk", "attack"]
    dir_names = ["down", "left", "right", "up"]

    for entity_type in entity_types:
        td = atlas.defs.get(entity_type)
        if not td:
            continue

        valid_states = td.states if td.states else ["idle"]

        for state in valid_states:
            if state not in states:
                continue

            for direction in range(td.directions):
                # Calculate max valid frames for this entity/direction
                # Based on atlas dimensions and frame_width from metadata
                atlas.get_uv(
                    entity_type,
                    variant=0,
                    frame=0,
                    direction=direction,
                    state=state,
                    scale="32",
                )
                meta = atlas.atlas_meta["32"]
                file_key = td.file
                base_meta = meta["tiles"][file_key]
                atlas_width = base_meta["width"]
                max_frames_atlas = (
                    (atlas_width // td.frame_width) if td.frame_width > 0 else td.frames
                )
                max_frames = min(td.frames, max_frames_atlas)

                for frame in range(max_frames):
                    # Register entity
                    eid = entity_renderer.register_entity(
                        entity_type, 10, 10, direction=direction, state=state
                    )

                    # Set specific frame
                    anim = entity_renderer.entity_anims[eid]
                    anim.frame = frame
                    anim.direction = direction
                    anim.state = state

                    # Get subimage
                    sub_image = entity_renderer.get_subimage(eid)
                    if sub_image:
                        # Convert to numpy array
                        arr = np.array(sub_image)

                        # Save as reference
                        filename = (
                            f"{entity_type}_{state}_dir{dir_names[direction]}_frame{frame}.npy"
                        )
                        filepath = output_dir / filename
                        np.save(filepath, arr)
                        print(f"  Saved: {filename}")

                    entity_renderer.remove_entity(eid)

    print(f"\nReference images saved to {output_dir}")
    return True


def compare_entity_rendering():
    """Compare current rendering with reference images."""
    print("=" * 60)
    print("Comparing Entity Rendering with References")
    print("=" * 60)

    ref_dir = Path("tools/visual_refs")
    if not ref_dir.exists():
        print("No reference images found. Run generate_entity_reference_images first.")
        return False

    atlas = TileAtlas()
    entity_renderer = EntityRenderer(atlas)

    all_passed = True

    for ref_file in ref_dir.glob("*.npy"):
        # Parse filename: ENTITY_STATE_dirDIR_frameFRAME.npy
        name = ref_file.stem
        # Parse: ENTITY_STATE_dirDIR_frameFRAME
        parts = name.split("_")
        if len(parts) < 4:
            continue

        entity_type = parts[0]
        state = parts[1]
        # Direction part is like "dirdown", "dirleft", etc.
        direction_part = parts[2]
        if not direction_part.startswith("dir"):
            continue
        direction_str = direction_part[3:]  # Remove "dir" prefix
        frame_str = parts[3].replace("frame", "")

        direction_map = {"down": 0, "left": 1, "right": 2, "up": 3}
        direction = direction_map.get(direction_str, 0)
        frame = int(frame_str)

        # Render current
        eid = entity_renderer.register_entity(entity_type, 10, 10, direction=direction, state=state)
        anim = entity_renderer.entity_anims[eid]
        anim.frame = frame
        anim.direction = direction
        anim.state = state

        sub_image = entity_renderer.get_subimage(eid)
        if sub_image:
            arr = np.array(sub_image)
            ref_arr = np.load(ref_file)

            if arr.shape == ref_arr.shape:
                diff = np.abs(arr.astype(np.float32) - ref_arr.astype(np.float32))
                max_diff = np.max(diff)
                mean_diff = np.mean(diff)

                if max_diff > 1:
                    print(f"  FAIL: {name} - max_diff={max_diff:.1f}, mean_diff={mean_diff:.4f}")
                    all_passed = False
                else:
                    print(f"  PASS: {name} - max_diff={max_diff:.1f}")
            else:
                print(f"  FAIL: {name} - shape mismatch {arr.shape} vs {ref_arr.shape}")
                all_passed = False

        entity_renderer.remove_entity(eid)

    return all_passed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Visual regression test for entity rendering")
    parser.add_argument("--generate", action="store_true", help="Generate reference images")
    parser.add_argument("--compare", action="store_true", help="Compare with references")
    args = parser.parse_args()

    if args.generate:
        return 0 if generate_entity_reference_images() else 1
    elif args.compare:
        return 0 if compare_entity_rendering() else 1
    else:
        print("Use --generate or --compare")
        return 1


if __name__ == "__main__":
    sys.exit(main())
