"""照準ユーティリティテスト (Phase 2 Step 37)"""

from __future__ import annotations

import os
import sys
from unittest.mock import Mock

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core_framework import Point  # noqa: E402
from ecs.entity import Entity  # noqa: E402
from systems import aimed_tile, find_nearest_visible_target  # noqa: E402


def create_test_entity(name: str, x: int, y: int, hp: int = 10, max_hp: int = 10, faction: str = "monster", is_pet: bool = False) -> Entity:
    """テスト用エンティティ作成ヘルパー"""
    e = Entity(name=name, x=x, y=y, is_pet=is_pet)
    e.hp = hp
    e.max_hp = max_hp
    e.faction = faction
    return e


class TestAimedTile:
    """aimed_tile ユーティリティの詳細テスト"""

    def test_aimed_tile_is_direction_relative(self):
        """aimed_tile は方向に相対的な座標を返す"""
        origin = create_test_entity("Player", 10, 10)

        # 8方向すべてテスト
        directions = [
            ((0, -1), (10, 7)),   # 北
            ((1, -1), (13, 7)),   # 北東
            ((1, 0), (13, 10)),   # 東
            ((1, 1), (13, 13)),   # 南東
            ((0, 1), (10, 13)),   # 南
            ((-1, 1), (7, 13)),   # 南西
            ((-1, 0), (7, 10)),   # 西
            ((-1, -1), (7, 7)),   # 北西
        ]

        for direction, expected in directions:
            result = aimed_tile(origin, direction, 3)
            assert result is not None, f"Direction {direction} returned None"
            assert result.x == expected[0], f"Direction {direction}: x={result.x} != {expected[0]}"
            assert result.y == expected[1], f"Direction {direction}: y={result.y} != {expected[1]}"

    def test_aimed_tile_distance_zero(self):
        """距離0なら元の座標"""
        origin = create_test_entity("Player", 10, 10)
        result = aimed_tile(origin, (1, 0), 0)
        assert result is not None
        assert result.x == 10
        assert result.y == 10

    def test_aimed_tile_stops_at_wall(self):
        """壁で遮断される"""
        origin = create_test_entity("Player", 10, 10)

        mock_engine = Mock()
        mock_engine.is_tile_free.side_effect = lambda x, y: (x, y) != (12, 10)
        mock_engine.get_entity_at.return_value = None

        # 右方向、距離5、壁が(12,10)にある
        result = aimed_tile(origin, (1, 0), 5, mock_engine)
        assert result is None, "壁で遮断された場合Noneが返るべき"

    def test_aimed_tile_returns_target_when_enemy_found(self):
        """敵が見つかったらその座標を返す"""
        origin = create_test_entity("Player", 10, 10)

        target = create_test_entity("Goblin", 12, 10, 10, 10, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.side_effect = lambda x, y: target if (x, y) == (12, 10) else None

        result = aimed_tile(origin, (1, 0), 5, mock_engine)

        assert result is not None
        assert result.x == 12
        assert result.y == 10

    def test_aimed_tile_ignores_friendly_entities(self):
        """味方(プレイヤー/ペット)は無視する"""
        origin = create_test_entity("Player", 10, 10)

        pet = create_test_entity("Pet", 12, 10, 10, 10, "player", is_pet=True)

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = pet

        result = aimed_tile(origin, (1, 0), 5, mock_engine)

        # ペットは無視され、射程末端が返る
        assert result is not None
        assert result.x == 15
        assert result.y == 10

    def test_aimed_tile_ignores_neutral_entities(self):
        """中立NPCは無視する"""
        origin = create_test_entity("Player", 10, 10)

        neutral = create_test_entity("Villager", 12, 10, 10, 10, "neutral")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = neutral

        result = aimed_tile(origin, (1, 0), 5, mock_engine)

        # 中立は無視され、射程末端が返る
        assert result is not None
        assert result.x == 15
        assert result.y == 10

    def test_aimed_tile_returns_none_out_of_bounds(self):
        """マップ範囲外ならNone"""
        from constants import MAP_HEIGHT, MAP_WIDTH

        # 左端
        origin = create_test_entity("Player", 0, 10)
        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = None

        result = aimed_tile(origin, (-1, 0), 5, mock_engine)
        assert result is None

        # 右端
        origin = create_test_entity("Player", MAP_WIDTH - 1, 10)
        result = aimed_tile(origin, (1, 0), 5, mock_engine)
        assert result is None

        # 上端
        origin = create_test_entity("Player", 10, 0)
        result = aimed_tile(origin, (0, -1), 5, mock_engine)
        assert result is None

        # 下端
        origin = create_test_entity("Player", 10, MAP_HEIGHT - 1)
        result = aimed_tile(origin, (0, 1), 5, mock_engine)
        assert result is None

    def test_aimed_tile_wall_blocks_before_enemy(self):
        """敵の手前に壁があれば敵を見つけない"""
        origin = create_test_entity("Player", 10, 10)

        target = create_test_entity("Goblin", 13, 10, 10, 10, "monster")

        mock_engine = Mock()
        # (12,10) が壁
        mock_engine.is_tile_free.side_effect = lambda x, y: (x, y) != (12, 10)
        mock_engine.get_entity_at.side_effect = lambda x, y: target if (x, y) == (13, 10) else None

        result = aimed_tile(origin, (1, 0), 5, mock_engine)

        # 壁で遮断されるためNone
        assert result is None


class TestFindNearestVisibleTarget:
    """find_nearest_visible_target のテスト"""

    def test_finds_nearest_enemy(self):
        """最寄りの敵を正しく見つける"""
        origin = create_test_entity("Player", 10, 10)

        near = create_test_entity("Goblin", 12, 10, 10, 10, "monster")
        far = create_test_entity("Orc", 15, 10, 20, 20, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True

        def get_entity_at(x, y):
            if (x, y) == (12, 10):
                return near
            if (x, y) == (15, 10):
                return far
            return None
        mock_engine.get_entity_at.side_effect = get_entity_at

        result = find_nearest_visible_target(origin, 6, mock_engine)

        assert result is not None
        target, point = result
        assert target is near
        assert point.x == 12
        assert point.y == 10

    def test_picks_nearest_among_multiple_directions(self):
        """複数方向に敵がいる場合、最寄りを選ぶ"""
        origin = create_test_entity("Player", 10, 10)

        # 右: 距離3
        right = create_test_entity("Goblin", 13, 10, 10, 10, "monster")
        # 上: 距離2 (より近い)
        up = create_test_entity("Slime", 10, 8, 5, 5, "monster")
        # 左上斜め: 距離2 (チェビシェフ距離)
        diag = create_test_entity("Bat", 8, 8, 5, 5, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True

        def get_entity_at(x, y):
            if (x, y) == (13, 10):
                return right
            if (x, y) == (10, 8):
                return up
            if (x, y) == (8, 8):
                return diag
            return None
        mock_engine.get_entity_at.side_effect = get_entity_at

        result = find_nearest_visible_target(origin, 6, mock_engine)

        assert result is not None
        target, point = result
        # 距離2の敵が優先される (up または diag)
        assert target in (up, diag)
        # チェビシェフ距離で最小

    def test_returns_none_when_no_enemy(self):
        """敵がいなければNone"""
        origin = create_test_entity("Player", 10, 10)

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = None

        result = find_nearest_visible_target(origin, 6, mock_engine)
        assert result is None

    def test_respects_max_range(self):
        """最大射程を超える敵は無視"""
        origin = create_test_entity("Player", 10, 10)

        far = create_test_entity("Dragon", 20, 10, 100, 100, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.side_effect = lambda x, y: far if (x, y) == (20, 10) else None

        # max_range=6 なので距離10の敵は無視
        result = find_nearest_visible_target(origin, 6, mock_engine)
        assert result is None

    def test_ignores_dead_entities(self):
        """HP0のエンティティは無視"""
        origin = create_test_entity("Player", 10, 10)

        dead = create_test_entity("Dead Goblin", 12, 10, 0, 10, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = dead

        result = find_nearest_visible_target(origin, 6, mock_engine)
        assert result is None


class TestAimCannotWrap:
    """照準が壁の裏側に回り込まないことを確認"""

    def test_aim_cannot_wrap_to_the_other_side_of_a_wall(self):
        """壁の裏側の敵を照準できない"""
        origin = create_test_entity("Player", 10, 10)

        # (11,10) に壁、(12,10) に敵
        target = create_test_entity("Goblin", 12, 10, 10, 10, "monster")

        mock_engine = Mock()
        mock_engine.is_tile_free.side_effect = lambda x, y: (x, y) != (11, 10)
        mock_engine.get_entity_at.side_effect = lambda x, y: target if (x, y) == (12, 10) else None

        result = aimed_tile(origin, (1, 0), 5, mock_engine)

        # 壁の手前で止まるため、敵の座標は返らない
        assert result is None

        # find_nearest_visible_target も同様
        result2 = find_nearest_visible_target(origin, 5, mock_engine)
        assert result2 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
