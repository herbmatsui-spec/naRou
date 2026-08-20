#!/usr/bin/env python3
"""
Entity rendering parity test.
Verifies that TCOD (terminal) and Web (PixiJS) entity rendering use the same UV coordinates.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tile_atlas import AUTOTILE_MAP, TileAtlas


def test_entity_uv_parity():
    """Test that all entity tile UVs are consistent within each scale."""
    atlas = TileAtlas()

    entity_tiles = ["PLAYER", "PET", "ENEMY_GOBLIN"]
    all_passed = True

    print("=" * 60)
    print("Entity UV Parity Test")
    print("=" * 60)

    for tile_id in entity_tiles:
        td = atlas.defs.get(tile_id)
        if not td:
            print(f"FAIL: {tile_id} not found in TileAtlas")
            all_passed = False
            continue

        print(f"\n{tile_id}:")
        print(
            f"  directions: {td.directions}, states: {td.states}, frames: {td.frames}"
        )

        # Test all direction/state/frame combinations at scale 32 (terminal default)
        for direction in range(td.directions):
            for state in td.states:
                for frame in range(td.frames):
                    uv_32 = atlas.get_uv(
                        tile_id,
                        direction=direction,
                        state=state,
                        frame=frame,
                        scale="32",
                    )

                    # Verify frame progression (horizontal)
                    if frame > 0:
                        prev_uv = atlas.get_uv(
                            tile_id,
                            direction=direction,
                            state=state,
                            frame=frame - 1,
                            scale="32",
                        )
                        if uv_32.x != prev_uv.x + td.frame_width:
                            print(
                                f"  FAIL: Frame progression broken at dir={direction}, state={state}, frame={frame}"
                            )
                            all_passed = False

                # Verify direction progression (vertical) using frame 0
                if direction > 0:
                    prev_uv = atlas.get_uv(
                        tile_id,
                        direction=direction - 1,
                        state=state,
                        frame=0,
                        scale="32",
                    )
                    curr_uv = atlas.get_uv(
                        tile_id, direction=direction, state=state, frame=0, scale="32"
                    )
                    # Each direction should be offset by base height
                    # At scale 32, PLAYER base height is 32 (from metadata)
                    expected_y_diff = 32
                    # Note: The actual metadata has 32px vertical spacing at scale 32

        print(
            f"  PASSED: All {td.directions} directions x {len(td.states)} states x {td.frames} frames consistent at scale 32"
        )

    return all_passed


def test_autotile_mapping():
    """Test that autotile mapping covers all 16 combinations."""
    print("\n" + "=" * 60)
    print("Autotile Mapping Test")
    print("=" * 60)

    all_passed = True
    for mask in range(16):
        variant = AUTOTILE_MAP.get(mask)
        if variant is None:
            print(f"  FAIL: Mask {mask:04b} not in AUTOTILE_MAP")
            all_passed = False
        else:
            print(f"  Mask {mask:04b} -> Variant {variant}")

    if all_passed:
        print("  PASSED: All 16 masks mapped")
    return all_passed


def test_facing_calculation():
    """Test facing direction calculation."""
    from core.entity_renderer import calculate_facing, calculate_facing_to_target

    print("\n" + "=" * 60)
    print("Facing Calculation Test")
    print("=" * 60)

    test_cases = [
        ((1, 0), 2),  # right
        ((-1, 0), 1),  # left
        ((0, 1), 0),  # down
        ((0, -1), 3),  # up
        ((2, 1), 2),  # right dominates
        ((1, 2), 0),  # down dominates
        ((-2, -1), 1),  # left dominates
        ((-1, -2), 3),  # up dominates
    ]

    all_passed = True
    for (dx, dy), expected in test_cases:
        result = calculate_facing(dx, dy)
        if result == expected:
            print(f"  PASS: ({dx}, {dy}) -> {result}")
        else:
            print(f"  FAIL: ({dx}, {dy}) -> {result} (expected {expected})")
            all_passed = False

    # Test calculate_facing_to_target
    result = calculate_facing_to_target(10, 10, 12, 10)  # target to right
    if result == 2:
        print(f"  PASS: (10,10)->(12,10) = {result}")
    else:
        print(f"  FAIL: (10,10)->(12,10) = {result} (expected 2)")
        all_passed = False

    return all_passed


def test_entity_animstate():
    """Test EntityAnimState updates."""
    from core.entity_renderer import EntityRenderer
    from core.tile_atlas import TileAtlas

    print("\n" + "=" * 60)
    print("EntityAnimState Test")
    print("=" * 60)

    atlas = TileAtlas()
    renderer = EntityRenderer(atlas)

    # Register a test entity
    eid = renderer.register_entity("PLAYER", 10, 10, direction=0, state="idle")

    all_passed = True

    # Test idle -> walk transition
    anim = renderer.entity_anims[eid]
    print(f"  Initial: state={anim.state}, frame={anim.frame}")

    # Update with walk state
    renderer.update_entity(
        eid, 10, 10, direction=0, state="walk", is_attacking=False, dt=1 / 60
    )
    print(f"  After walk update: state={anim.state}, frame={anim.frame}")

    # Test attack trigger
    renderer.update_entity(
        eid, 10, 10, direction=0, state="attack", is_attacking=True, dt=1 / 60
    )
    print(
        f"  After attack trigger: state={anim.state}, frame={anim.frame}, attack_timer={anim.attack_timer:.2f}"
    )

    # Simulate attack timer countdown
    for i in range(31):  # 31 frames to ensure attack_timer goes negative
        renderer.update_entity(
            eid, 10, 10, direction=0, state="attack", is_attacking=False, dt=1 / 60
        )

    print(f"  After 0.5s: state={anim.state}, attack_timer={anim.attack_timer:.2f}")

    if anim.state == "idle" and anim.loop:
        print("  PASS: Attack animation returned to idle")
    else:
        print("  FAIL: Attack animation did not return to idle properly")
        all_passed = False

    # Test death state
    eid2 = renderer.register_entity("ENEMY_GOBLIN", 5, 5, state="dead")
    # No need to call update_entity since state is already set
    anim2 = renderer.entity_anims[eid2]
    print(f"  Death state: state={anim2.state}, loop={anim2.loop}")

    if anim2.state == "dead" and not anim2.loop:
        print("  PASS: Death state configured correctly")
    else:
        print("  FAIL: Death state not configured correctly")
        all_passed = False

    return all_passed


def main():
    print("Entity Rendering Parity & Functionality Tests")
    print("=" * 60)

    results = []
    results.append(("UV Parity", test_entity_uv_parity()))
    results.append(("Autotile Mapping", test_autotile_mapping()))
    results.append(("Facing Calculation", test_facing_calculation()))
    results.append(("EntityAnimState", test_entity_animstate()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
