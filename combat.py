"""
Combat utility functions for pure calculations.
"""

from __future__ import annotations

from typing import Tuple
from constants import Element


def aoe_radius(cx: int, cy: int, radius: int = 1) -> list[tuple[int, int]]:
    """円形範囲の座標リスト"""
    coords = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if abs(dx) + abs(dy) <= radius * 1.5:
                coords.append((cx + dx, cy + dy))
    return coords


def aoe_beam(
    sx: int, sy: int, direction: tuple[int, int], length: int = 5
) -> list[tuple[int, int]]:
    """直線ビーム範囲"""
    dx, dy = direction
    return [(sx + dx * i, sy + dy * i) for i in range(1, length + 1)]


def aoe_nova(cx: int, cy: int) -> list[tuple[int, int]]:
    """周囲全方位（8マス）"""
    return [(cx + dx, cy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]


def calc_element_damage(base_dmg: int, element: Element, resistance: int) -> int:
    """属性耐性を考慮したダメージ計算

    Args:
        base_dmg: 基本ダメージ
        element: 属性タイプ
        resistance: 耐性値 (-100 to 100, 0=通常, 100=無効, -50=弱点)

    Returns:
        耐性を考慮したダメージ (最小0)
    """
    # resistance: 100=無効, 0=通常, -50=弱点(1.5倍)
    multiplier = max(0.0, 1.0 - (resistance / 100.0))
    return max(0, int(base_dmg * multiplier))
