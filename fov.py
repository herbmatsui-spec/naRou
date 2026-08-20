"""
Dynamic lighting foundation for Phase 2-A.

Provides:
  * recursive_shadowcast() - recursive shadowcasting field-of-view (Björn Bergström's
    algorithm) used to occlude light behind walls.
  * line_of_sight()        - Bresenham LOS test honouring transparency.
  * compute_light_map()    - combines any number of light sources (player lantern,
    torches, spells) into a per-cell (intensity, color) grid. Walls block light via
    shadowcasting so "only the area around a torch is lit" and "walls behind go dark".

A `blocked(x, y)` callable (or a 2D 0/1 grid) defines opaque tiles. Coordinates are
integer tile coordinates.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

# Octant transforms for recursive shadowcasting. Each tuple is (xx, xy, yx, yy)
# mapping the algorithm's local (dx, dy) onto world coordinates.
_OCTANTS = (
    (1, 0, 0, 1),
    (0, 1, 1, 0),
    (0, -1, 1, 0),
    (-1, 0, 0, 1),
    (-1, 0, 0, -1),
    (0, -1, -1, 0),
    (0, 1, -1, 0),
    (1, 0, 0, -1),
)


def _as_blocked(blocked) -> Callable[[int, int], bool]:
    if callable(blocked):
        return blocked
    grid = blocked
    h = len(grid)
    w = len(grid[0]) if h else 0

    def _blocked(x: int, y: int) -> bool:
        if x < 0 or y < 0 or y >= h or x >= w:
            return True
        cell = grid[y][x]
        return bool(cell)

    return _blocked


def recursive_shadowcast(
    blocked,
    ox: int,
    oy: int,
    radius: int,
    origin_visible: bool = True,
) -> set:
    """Return the set of (x, y) tiles visible from (ox, oy) within `radius`.

    Uses recursive shadowcasting. `blocked(x, y)` returns True for opaque tiles.
    The origin tile is included when `origin_visible` is True.
    """
    is_blocked = _as_blocked(blocked)
    visible: set = set()
    if origin_visible:
        visible.add((ox, oy))

    for xx, xy, yx, yy in _OCTANTS:
        _cast_light(visible, is_blocked, ox, oy, radius, 1, 1.0, 0.0, xx, xy, yx, yy)
    return visible


def _cast_light(
    visible, is_blocked, ox, oy, radius, row, start_slope, end_slope, xx, xy, yx, yy
):
    if start_slope < end_slope:
        return

    next_start_slope = start_slope
    for i in range(row, radius + 1):
        blocked_prev = False
        dy = -i
        for dx in range(-i, 1):
            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)
            if r_slope > start_slope:
                break
            if l_slope < end_slope:
                continue

            x = ox + dx * xx + dy * xy
            y = oy + dx * yx + dy * yy
            visible.add((x, y))

            if is_blocked(x, y):
                if not blocked_prev:
                    nx = ox + (dx - 1) * xx + dy * xy
                    ny = oy + (dx - 1) * yx + dy * yy
                    _cast_light(
                        visible,
                        is_blocked,
                        ox,
                        oy,
                        radius,
                        i + 1,
                        next_start_slope,
                        l_slope,
                        xx,
                        xy,
                        yx,
                        yy,
                    )
                blocked_prev = True
            else:
                blocked_prev = False
                next_start_slope = r_slope
        if blocked_prev:
            break


def line_of_sight(blocked, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Bresenham line-of-sight test. Endpoints are included; intermediate opaque
    tiles block. The origin and target themselves are never treated as blockers."""
    is_blocked = _as_blocked(blocked)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    cx, cy = x0, y0
    while True:
        if (cx, cy) != (x0, y0) and (cx, cy) != (x1, y1) and is_blocked(cx, cy):
            return False
        if cx == x1 and cy == y1:
            return True
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            cx += sx
        if e2 <= dx:
            err += dx
            cy += sy


# Light source definition fields:
#   x, y          tile coordinates
#   radius        light reach in tiles
#   intensity     peak brightness 0..1
#   color         optional (r, g, b) 0..255 tint; default neutral white
LightSource = dict[str, object]


def compute_light_map(
    blocked,
    sources: Sequence[LightSource],
    width: int,
    height: int,
    ambient: float = 0.06,
) -> tuple[list[list[float]], list[list[tuple[int, int, int]]]]:
    """Compute a (intensity, color) light map.

    Returns two height x width grids:
      * intensity[y][x] in 0..1 (ambient baseline + per-source falloff)
      * color[y][x]    blended (r, g, b) 0..255 tint of the contributing light

    Each source lights only cells it has line-of-sight to (walls block), with
    linear falloff: factor = intensity * (1 - dist / radius).
    """
    is_blocked = _as_blocked(blocked)
    intensity: list[list[float]] = [[ambient] * width for _ in range(height)]
    cr: list[list[float]] = [[0.0] * width for _ in range(height)]
    cg: list[list[float]] = [[0.0] * width for _ in range(height)]
    cb: list[list[float]] = [[0.0] * width for _ in range(height)]

    for src in sources:
        sx = int(src["x"])
        sy = int(src["y"])
        radius = float(src.get("radius", 6.0))
        peak = float(src.get("intensity", 1.0))
        col = src.get("color", (255, 255, 255))
        r0, g0, b0 = (int(col[0]), int(col[1]), int(col[2]))
        if radius <= 0:
            continue
        # Limit work to the source's bounding box.
        x0 = max(0, sx - int(radius))
        x1 = min(width - 1, sx + int(radius))
        y0 = max(0, sy - int(radius))
        y1 = min(height - 1, sy + int(radius))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if is_blocked(x, y):
                    continue
                d = math.hypot(x - sx, y - sy)
                if d > radius:
                    continue
                if (x, y) != (sx, sy) and not line_of_sight(is_blocked, sx, sy, x, y):
                    continue
                f = peak * (1.0 - d / radius)
                if f <= 0:
                    continue
                if f > intensity[y][x]:
                    intensity[y][x] = f
                # Accumulate a distance-weighted colour so warm torches tint
                # nearby tiles while the player lantern stays neutral.
                cr[y][x] += f * r0
                cg[y][x] += f * g0
                cb[y][x] += f * b0

    color: list[list[tuple[int, int, int]]] = []
    for y in range(height):
        row_cols = []
        for x in range(width):
            w = intensity[y][x]
            if w > ambient:
                row_cols.append(
                    (
                        min(255, int(cr[y][x] / w)),
                        min(255, int(cg[y][x] / w)),
                        min(255, int(cb[y][x] / w)),
                    )
                )
            else:
                row_cols.append((255, 255, 255))
        color.append(row_cols)

    return intensity, color
