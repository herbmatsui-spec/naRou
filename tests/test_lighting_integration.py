"""Integration test: server-style light-map construction (Plan 2-A).

Mirrors web_server._serialize_engine_state's use of fov.compute_light_map:
a viewport window, a blocked grid derived from GameMap.is_transparent, and
light sources for the player lantern + torches.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fov import compute_light_map
from map_engine import GameMap


def _build_viewport(game_map, cam_x, cam_y, view_w, view_h, sources):
    blocked = [
        [
            (
                not game_map.is_transparent(cam_x + vx, cam_y + vy)
                if (0 <= cam_x + vx < game_map.width and 0 <= cam_y + vy < game_map.height)
                else True
            )
            for vx in range(view_w)
        ]
        for vy in range(view_h)
    ]
    intensity, _ = compute_light_map(blocked, sources, view_w, view_h, ambient=0.06)
    return intensity


def test_torches_light_floor_around_them():
    m = GameMap(60, 40, "dungeon")
    m.generate_dungeon()
    assert len(m.torch_positions) > 0

    tx, ty = m.torch_positions[0]
    view_w = view_h = 15
    cam_x = max(0, tx - view_w // 2)
    cam_y = max(0, ty - view_h // 2)
    lx, ly = tx - cam_x, ty - cam_y

    sources = [
        {
            "x": lx,
            "y": ly,
            "radius": 5.0,
            "intensity": 0.9,
            "color": (255, 170, 80),
        }
    ]
    intensity = _build_viewport(m, cam_x, cam_y, view_w, view_h, sources)

    # Torch sits on a wall (correctly unlit), but an adjacent floor cell glows.
    lit = False
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = lx + dx, ly + dy
        if 0 <= nx < view_w and 0 <= ny < view_h and intensity[ny][nx] > 0.4:
            lit = True
            break
    assert lit, "no adjacent floor cell lit by torch"


def test_player_lantern_lights_own_tile():
    m = GameMap(60, 40, "dungeon")
    m.generate_dungeon()
    px, py = m.start_pos
    view_w = view_h = 21
    cam_x = max(0, min(m.width - view_w, px - view_w // 2))
    cam_y = max(0, min(m.height - view_h, py - view_h // 2))
    lx, ly = px - cam_x, py - cam_y
    sources = [
        {
            "x": lx,
            "y": ly,
            "radius": 8.0,
            "intensity": 1.0,
            "color": (255, 240, 210),
        }
    ]
    intensity = _build_viewport(m, cam_x, cam_y, view_w, view_h, sources)
    assert intensity[ly][lx] > 0.9  # player tile is fully lit
