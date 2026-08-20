"""Tests for the dynamic-lighting FOV / light-map foundation (Plan 2-A)."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fov import (  # noqa: E402
    compute_light_map,
    line_of_sight,
    recursive_shadowcast,
)

# 11x11 grid; 1 = wall, 0 = floor
WALLS = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]


def test_shadowcast_sees_origin_and_neighbours():
    vis = recursive_shadowcast(WALLS, 5, 5, radius=4)
    assert (5, 5) in vis
    # Open floor around the origin is visible.
    assert (6, 5) in vis and (5, 6) in vis


def test_shadowcast_occluded_by_wall():
    # Standing at (5,5) inside the central room; the thick wall column at x=7
    # is visible (you see its face) but the corridor on the far side (x=9) is
    # hidden behind it and must never be lit.
    vis = recursive_shadowcast(WALLS, 5, 5, radius=6)
    assert (7, 5) in vis  # wall surface is visible
    assert (9, 5) not in vis  # behind the wall, never lit


def test_line_of_sight_blocked_through_wall():
    assert line_of_sight(WALLS, 5, 5, 9, 5) is False  # wall column at x=7 blocks
    assert line_of_sight(WALLS, 1, 8, 9, 8) is True  # fully open row 8


def test_light_map_falls_off_with_distance():
    # Use a fully open grid so falloff is monotonic with distance.
    open_grid = [[0] * 11 for _ in range(11)]
    intensity, _ = compute_light_map(
        open_grid,
        [{"x": 5, "y": 5, "radius": 5, "intensity": 1.0}],
        11,
        11,
        ambient=0.0,
    )
    assert intensity[5][5] == pytest.approx(1.0, abs=1e-6)
    # Neighbours dimmer than origin and dimmer still further out.
    assert intensity[5][4] > intensity[5][3] > intensity[5][2] > 0.0
    # Beyond the radius the source contributes nothing.
    assert intensity[5][0] == 0.0


def test_light_map_walls_block_light():
    h = len(WALLS)
    w = len(WALLS[0])
    intensity, _ = compute_light_map(
        WALLS,
        [{"x": 5, "y": 5, "radius": 8, "intensity": 1.0}],
        w,
        h,
        ambient=0.0,
    )
    # The corridor beyond the wall (x=9, same row) stays dark.
    assert intensity[5][9] == 0.0


def test_light_map_torch_warm_tint():
    grid = [[0] * 9 for _ in range(9)]
    intensity, color = compute_light_map(
        grid,
        [{"x": 4, "y": 4, "radius": 4, "intensity": 1.0, "color": (255, 170, 80)}],
        9,
        9,
        ambient=0.0,
    )
    # Near the torch the tint is warm (red >= green >= blue).
    r, g, b = color[4][4]
    assert r >= g >= b
    assert intensity[4][4] > 0.9


def test_light_map_ambient_baseline():
    grid = [[0] * 5 for _ in range(5)]
    intensity, _ = compute_light_map(
        grid,
        [],
        5,
        5,
        ambient=0.1,
    )
    assert intensity[0][0] == pytest.approx(0.1)
