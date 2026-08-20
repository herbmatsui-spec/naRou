"""
Elona Roguelike Masterpiece - Geometry, Time, EventBus & Action Framework
Steps 2, 4, 7, 9, 20, 21, 24, 25 (Bresenham & A* Pathfinding)
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, order=True)
class Point:
    """不変な2次元座標クラス (ステップ2)"""

    x: int
    y: int

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def distance_to(self, other: Point) -> float:
        """ユークリッド距離"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def chebyshev_distance(self, other: Point) -> int:
        """チェビシェフ距離 (斜め移動ありのローグライク用)"""
        return max(abs(self.x - other.x), abs(self.y - other.y))


def bresenham_line(start: Point, end: Point) -> list[Point]:
    """Bresenhamアルゴリズムによる2点間の直線上グリッド座標の算出 (ステップ20)"""
    x1, y1 = start.x, start.y
    x2, y2 = end.x, end.y
    points: list[Point] = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy

    while True:
        points.append(Point(x1, y1))
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy
    return points


class AStar:
    """A*による最短経路探索 (ステップ24, 25) - 賢いNPC追跡"""

    @staticmethod
    def get_path(
        start: Point,
        goal: Point,
        is_walkable_fn: Callable[[int, int], bool],
        max_depth: int = 40,
    ) -> list[Point]:
        if start == goal:
            return []

        open_set: list[tuple[float, int, Point]] = []
        heapq.heappush(open_set, (0.0, 0, start))
        came_from: dict[Point, Point] = {}
        g_score: dict[Point, float] = {start: 0.0}

        count = 0
        while open_set and count < max_depth * 10:
            count += 1
            _, _, current = heapq.heappop(open_set)

            if current == goal:
                path: list[Point] = []
                curr = goal
                while curr in came_from:
                    path.append(curr)
                    curr = came_from[curr]
                path.reverse()
                return path

            # 8方向への展開
            for dx, dy in [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
                (-1, -1),
                (1, 1),
                (-1, 1),
                (1, -1),
            ]:
                neighbor = Point(current.x + dx, current.y + dy)
                # ゴール位置そのものは通過可能として扱う
                if neighbor != goal and not is_walkable_fn(neighbor.x, neighbor.y):
                    continue

                step_cost = 1.414 if dx != 0 and dy != 0 else 1.0
                tentative_g = g_score[current] + step_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + neighbor.chebyshev_distance(goal)
                    heapq.heappush(open_set, (f_score, count, neighbor))

        return []  # 経路なし


class EventBus:
    """モジュール間の疎結合イベント通知バス (ステップ7, 商用高信頼性対応)"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        if (
            event_type in self._subscribers
            and callback in self._subscribers[event_type]
        ):
            self._subscribers[event_type].remove(callback)
            return True
        return False

    def publish(self, event_type: str, data: Any = None) -> None:
        if event_type in self._subscribers:
            for cb in list(self._subscribers[event_type]):
                try:
                    cb(data)
                except Exception as e:
                    import logging

                    logging.getLogger("EventBus").error(
                        f"Error handling event {event_type} in {cb}: {e}", exc_info=True
                    )

    def clear(self) -> None:
        self._subscribers.clear()


@dataclass
class LogMessage:
    """色付きメッセージログ (ステップ8)"""

    text: str
    color: tuple[int, int, int] = (230, 230, 230)
    level: str = "INFO"  # INFO, SUCCESS, WARNING, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "color": list(self.color), "level": self.level}


class MessageLog:
    """高度なメッセージ履歴管理 (ステップ8, 66, UX強化)"""

    def __init__(self, max_history: int = 150):
        self.history: list[LogMessage] = []
        self.max_history = max_history

    def add(
        self,
        text: str,
        color: tuple[int, int, int] = (230, 230, 230),
        level: str = "INFO",
    ) -> None:
        self.history.append(LogMessage(text=text, color=color, level=level))
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_recent(self, count: int = 5) -> list[LogMessage]:
        return self.history[-count:]


class BaseSystem:
    """商用アーキテクチャ用サブシステム基底クラス (Step 12, 13)"""

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__

    def initialize(self, engine: Any = None) -> None:
        """システムの初期化フック"""

    def update(self, engine: Any = None, delta_time: float = 1.0) -> None:
        """毎ターンのシステム更新フック"""


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str | None = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager

    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
