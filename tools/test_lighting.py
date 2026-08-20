#!/usr/bin/env python3
"""
Lighting system test for terminal renderer.
Tests TerminalLightingSystem functionality.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tcod
import tcod.console

from core.lighting import (
    EnemyCone,
    LightingDrawCall,
    LightMap,
    LightSource,
    TerminalLightingSystem,
)


def test_light_map_update():
    """Test light map update from intensity/color grids."""
    print("Testing light map update...")

    lighting = TerminalLightingSystem(40, 24)

    # Create test grids
    intensity_grid = [
        [1.0, 1.0, 0.5, 0.0],
        [1.0, 0.5, 0.0, -1.0],
        [0.5, 0.0, -1.0, -1.0],
    ]
    color_grid = [
        [(255, 240, 210), (255, 240, 210), (255, 200, 150), (100, 100, 100)],
        [(255, 240, 210), (255, 200, 150), (100, 100, 100), (0, 0, 0)],
        [(255, 200, 150), (100, 100, 100), (0, 0, 0), (0, 0, 0)],
    ]

    lighting.update_light_map(intensity_grid, color_grid)

    assert lighting.light_map is not None
    assert len(lighting.light_map.intensity) == 3
    assert len(lighting.light_map.intensity[0]) == 4
    assert lighting.light_map.intensity[0][0] == 1.0
    assert lighting.light_map.intensity[2][3] == -1.0

    print("  PASS: Light map update works")


def test_light_sources():
    """Test light source flicker calculation."""
    print("Testing light sources...")

    lighting = TerminalLightingSystem(40, 24)

    sources = [
        LightSource(x=10, y=10, radius=7.5, intensity=1.0, color=(255, 240, 210)),
        LightSource(x=20, y=15, radius=5.0, intensity=0.8, color=(255, 180, 100)),
    ]

    lighting.set_light_sources(sources, 0.0)

    assert len(lighting.light_sources) == 2
    assert lighting.light_sources[0].seed == 10 * 13.13 + 10 * 7.7
    assert lighting.light_sources[0].flicker >= 0.8  # flicker should be positive
    assert lighting.light_sources[0].effective_radius > 0

    # Test flicker update
    lighting.set_light_sources(sources, 1.0)
    assert lighting.light_sources[0].flicker != 1.0  # Should have flickered

    print("  PASS: Light source flicker works")


def test_enemy_cones():
    """Test enemy cone pulse calculation."""
    print("Testing enemy cones...")

    lighting = TerminalLightingSystem(40, 24)

    cones = [
        EnemyCone(
            x=15, y=10, angle=0.0, half_angle=0.6, range=6.0, color=(255, 60, 60)
        ),
    ]

    lighting.set_enemy_cones(cones, 0.0)

    assert len(lighting.enemy_cones) == 1
    assert lighting.enemy_cones[0].pulse >= 0.0

    # Test pulse update
    lighting.set_enemy_cones(cones, 1.0)
    # Pulse should oscillate

    print("  PASS: Enemy cone pulse works")


def test_lighting_draw_calls():
    """Test LightingDrawCall integration."""
    print("Testing LightingDrawCall...")

    lighting = TerminalLightingSystem(40, 24)

    lm = LightMap(
        intensity=[[1.0, 0.5], [0.0, -1.0]],
        color=[[(255, 240, 210), (200, 200, 150)], [(100, 100, 100), (0, 0, 0)]],
    )
    sources = [LightSource(x=5, y=5, radius=7.5)]
    cones = [EnemyCone(x=10, y=10, angle=0.0)]

    call = LightingDrawCall(
        light_map=lm,
        light_sources=sources,
        enemy_cones=cones,
        ambient_light=0.08,
        time=0.5,
    )

    # Test that data is stored
    assert call.light_map is lm
    assert len(call.light_sources) == 1
    assert len(call.enemy_cones) == 1
    assert call.ambient_light == 0.08
    assert call.time == 0.5

    print("  PASS: LightingDrawCall works")


def test_render_pass():
    """Test full render pass on a real console."""
    print("Testing render pass...")

    # Create a real tcod console
    console = tcod.console.Console(40, 24, order="F")
    lighting = TerminalLightingSystem(40, 24)

    # Setup test data
    intensity_grid = [
        [1.0 if (x + y) % 2 == 0 else 0.5 for x in range(40)] for y in range(24)
    ]
    color_grid = [[(255, 240, 210) for x in range(40)] for y in range(24)]

    lighting.update_light_map(intensity_grid, color_grid)

    sources = [
        LightSource(x=20, y=12, radius=7.5, intensity=1.0, color=(255, 240, 210))
    ]
    cones = [EnemyCone(x=10, y=10, angle=0.0, half_angle=0.6, range=6.0)]

    lighting.set_light_sources(sources, 0.0)
    lighting.set_enemy_cones(cones, 0.0)

    # Create visibility/explored grids
    visible = [[True for _ in range(40)] for _ in range(24)]
    explored = [[True for _ in range(40)] for _ in range(24)]

    # Execute render pass
    lighting.render_pass(console, 0, 0, 40, 24, visible, explored, 0.0)

    # Check that background was modified
    bg = console.tiles_rgb["bg"]
    # At least some tiles should be non-zero
    non_zero = sum(
        1
        for y in range(24)
        for x in range(40)
        if bg[x, y][0] > 0 or bg[x, y][1] > 0 or bg[x, y][2] > 0
    )

    assert non_zero > 0, "Background should be lit"

    print("  PASS: Render pass works")


def main():
    print("=" * 60)
    print("Terminal Lighting System Tests")
    print("=" * 60)

    test_light_map_update()
    test_light_sources()
    test_enemy_cones()
    test_lighting_draw_calls()
    test_render_pass()

    print("\n" + "=" * 60)
    print("ALL LIGHTING TESTS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
