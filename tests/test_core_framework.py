"""Unit tests for geometry and pathfinding in core_framework."""

from __future__ import annotations

from core_framework import AStar, Point, bresenham_line


def test_point_add_sub():
    a = Point(1, 2)
    b = Point(3, 5)
    assert a + b == Point(4, 7)
    assert b - a == Point(2, 3)


def test_point_distances():
    a = Point(0, 0)
    b = Point(3, 4)
    assert a.distance_to(b) == 5.0
    assert a.chebyshev_distance(b) == 4


def test_bresenham_line_endpoints():
    line = bresenham_line(Point(0, 0), Point(3, 0))
    assert line[0] == Point(0, 0)
    assert line[-1] == Point(3, 0)
    assert len(line) == 4


def test_astar_straight_path():
    start = Point(0, 0)
    goal = Point(3, 0)

    def walkable(x, y):
        return 0 <= x <= 3 and y == 0

    path = AStar.get_path(start, goal, walkable)
    assert path[0] == Point(1, 0)
    assert path[-1] == Point(3, 0)


def test_astar_no_path_when_blocked():
    start = Point(0, 0)
    goal = Point(2, 0)

    def walkable(x, y):
        return (x, y) == (0, 0)  # only start is walkable

    assert AStar.get_path(start, goal, walkable) == []


def test_astar_returns_empty_for_same_point():
    assert AStar.get_path(Point(1, 1), Point(1, 1), lambda x, y: True) == []
