"""
Unit tests for SkillEaterSecretAccess - Map Generation Integration (Step 60)
"""
from __future__ import annotations

import unittest

from constants import (
    TILE_FALSE_WALL,
    TILE_HIDDEN_DOOR,
    TILE_SECRET_FLOOR,
    TILE_VENT,
)
from map_engine import GameMap
from secret_area_system import SECRET_REGISTRY, SecretArea


class MockWorldLayer:
    """テスト用モックワールドレイヤー"""
    def __init__(self):
        self.zone = "underground"
        self.biome = "ruins"
        self.depth = 15
        self.dimension = "material"
        self.theme_data = {
            "gimmicks": [
                "secret_doors:0.3",
                "false_walls:0.2",
                "secret_floors:0.1",
                "vents:0.15",
            ]
        }


class TestMapGenerationSecrets(unittest.TestCase):
    """マップ生成時の秘密配置テスト"""

    def setUp(self):
        self.game_map = GameMap(
            width=120,
            height=80,
            map_type="dungeon",
            floor_level=15,
        )
        self.game_map.world_layer = MockWorldLayer()

        # レジストリにテストエリア追加
        SECRET_REGISTRY._secret_areas.clear()
        SECRET_REGISTRY._areas_by_layer.clear()

        self.test_area_hidden = SecretArea(
            id="test_hidden_door",
            name="テスト隠し扉",
            layer_key="underground:ruins:15:material",
            secret_type="hidden_door",
            position=(10, 10),
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        SECRET_REGISTRY._secret_areas["test_hidden_door"] = self.test_area_hidden
        SECRET_REGISTRY._areas_by_layer["underground:ruins:15:material"] = [self.test_area_hidden]

    def test_place_secret_areas_hidden_door(self):
        """隠し扉が配置される"""
        # 壁タイルで初期化
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        self.test_area_hidden.position = (10, 10)
        self.game_map.tiles[10][10] = "TILE_WALL"

        self.game_map._place_secret_areas()

        # 隠し扉が配置されているか
        self.assertIn((10, 10), self.game_map.hidden_tiles)
        self.assertEqual(self.game_map.hidden_tiles[(10, 10)]["secret_type"], "hidden_door")
        self.assertEqual(self.game_map.hidden_tiles[(10, 10)]["area_id"], "test_hidden_door")
        # 元の壁タイルが保存されているか
        self.assertEqual(self.game_map.hidden_tiles[(10, 10)]["original_tile"], "TILE_WALL")

    def test_place_secret_areas_false_wall(self):
        """偽の壁が配置される"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        test_area = SecretArea(
            id="test_false_wall",
            name="テスト偽の壁",
            layer_key="underground:ruins:15:material",
            secret_type="false_wall",
            position=(20, 20),
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        SECRET_REGISTRY._secret_areas["test_false_wall"] = test_area
        SECRET_REGISTRY._areas_by_layer["underground:ruins:15:material"].append(test_area)

        test_area.position = (20, 20)
        self.game_map.tiles[20][20] = "TILE_WALL"

        self.game_map._place_secret_areas()

        self.assertIn((20, 20), self.game_map.hidden_tiles)
        self.assertEqual(self.game_map.hidden_tiles[(20, 20)]["secret_type"], "false_wall")

    def test_place_secret_areas_secret_floor(self):
        """床下通路が配置される"""
        self.game_map.tiles = [["TILE_FLOOR" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        test_area = SecretArea(
            id="test_secret_floor",
            name="テスト床下通路",
            layer_key="underground:ruins:15:material",
            secret_type="secret_floor",
            position=(30, 30),
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        SECRET_REGISTRY._secret_areas["test_secret_floor"] = test_area
        SECRET_REGISTRY._areas_by_layer["underground:ruins:15:material"].append(test_area)

        test_area.position = (30, 30)
        self.game_map.tiles[30][30] = "TILE_FLOOR"

        self.game_map._place_secret_areas()

        self.assertIn((30, 30), self.game_map.hidden_tiles)
        self.assertEqual(self.game_map.hidden_tiles[(30, 30)]["secret_type"], "secret_floor")

    def test_place_secret_areas_vent(self):
        """換気ダクトが配置される"""
        self.game_map.tiles = [["TILE_FLOOR" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        test_area = SecretArea(
            id="test_vent",
            name="テスト換気ダクト",
            layer_key="underground:ruins:15:material",
            secret_type="vent",
            position=(40, 40),
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        SECRET_REGISTRY._secret_areas["test_vent"] = test_area
        SECRET_REGISTRY._areas_by_layer["underground:ruins:15:material"].append(test_area)

        test_area.position = (40, 40)
        self.game_map.tiles[40][40] = "TILE_FLOOR"

        self.game_map._place_secret_areas()

        self.assertIn((40, 40), self.game_map.hidden_tiles)
        self.assertEqual(self.game_map.hidden_tiles[(40, 40)]["secret_type"], "vent")

    def test_is_walkable_hidden_types(self):
        """隠しタイプが通行可能か"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.tiles[10][10] = TILE_HIDDEN_DOOR
        self.game_map.tiles[20][20] = TILE_FALSE_WALL
        self.game_map.tiles[30][30] = TILE_SECRET_FLOOR
        self.game_map.tiles[40][40] = TILE_VENT

        # 発見済みなら通行可能
        self.assertTrue(self.game_map.is_walkable(10, 10))
        self.assertTrue(self.game_map.is_walkable(20, 20))
        self.assertTrue(self.game_map.is_walkable(30, 30))
        self.assertTrue(self.game_map.is_walkable(40, 40))

    def test_is_transparent_hidden_types(self):
        """隠しタイプの透過性"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.tiles[10][10] = TILE_HIDDEN_DOOR
        self.game_map.tiles[20][20] = TILE_FALSE_WALL
        self.game_map.tiles[30][30] = TILE_SECRET_FLOOR
        self.game_map.tiles[40][40] = TILE_VENT

        # 隠し扉・偽の壁は光を通さない
        self.assertFalse(self.game_map.is_transparent(10, 10))
        self.assertFalse(self.game_map.is_transparent(20, 20))
        # 床下通路・換気ダクトは光を通す
        self.assertTrue(self.game_map.is_transparent(30, 30))
        self.assertTrue(self.game_map.is_transparent(40, 40))

    def test_get_secret_minimap_data(self):
        """ミニマップ用データ取得"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        self.test_area_hidden.position = (10, 10)
        self.test_area_hidden.is_discovered = True
        self.test_area_hidden.is_unlocked = True
        self.game_map.tiles[10][10] = "TILE_WALL"

        self.game_map._place_secret_areas()

        data = self.game_map.get_secret_minimap_data()

        self.assertIn((10, 10), data["discovered"])
        self.assertEqual(data["discovered"][(10, 10)]["type"], "hidden_door")
        self.assertEqual(data["discovered"][(10, 10)]["name"], "テスト隠し扉")
        self.assertEqual(data["discovered"][(10, 10)]["icon"], "🔓")

    def test_get_secret_hint_at(self):
        """ヒント取得"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        self.test_area_hidden.position = (10, 10)
        self.test_area_hidden.is_discovered = True
        self.test_area_hidden.is_unlocked = False
        self.test_area_hidden.access_conditions = [
            {"type": "faction_rep", "faction": "resistance", "min_rep": 30}
        ]
        self.game_map.tiles[10][10] = "TILE_WALL"

        self.game_map._place_secret_areas()

        hint = self.game_map.get_secret_hint_at(10, 10)

        self.assertIsNotNone(hint)
        self.assertIn("テスト隠し扉", hint)
        self.assertIn("resistance", hint)
        self.assertIn("30", hint)

    def test_get_secret_hint_at_locked(self):
        """未発見時のヒント"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}

        self.test_area_hidden.position = (10, 10)
        self.test_area_hidden.is_discovered = False
        self.game_map.tiles[10][10] = "TILE_WALL"

        self.game_map._place_secret_areas()

        hint = self.game_map.get_secret_hint_at(10, 10)

        self.assertIsNotNone(hint)
        self.assertIn("秘密がありそうだ", hint)


class TestSecretAreaPlacementOverlap(unittest.TestCase):
    """秘密配置の重複回避テスト"""

    def setUp(self):
        self.game_map = GameMap(
            width=120,
            height=80,
            map_type="dungeon",
            floor_level=15,
        )
        self.game_map.world_layer = MockWorldLayer()

        SECRET_REGISTRY._secret_areas.clear()
        SECRET_REGISTRY._areas_by_layer.clear()

    def test_stairs_positions_excluded(self):
        """階段位置は除外される"""
        self.game_map.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.game_map.hidden_tiles = {}
        self.game_map.stairs_up_pos = (10, 10)
        self.game_map.stairs_down_pos = (20, 20)

        test_area = SecretArea(
            id="test_exclude",
            name="除外テスト",
            layer_key="underground:ruins:15:material",
            secret_type="hidden_door",
            position=(10, 10),  # 上り階段と同じ
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        SECRET_REGISTRY._secret_areas["test_exclude"] = test_area
        SECRET_REGISTRY._areas_by_layer["underground:ruins:15:material"] = [test_area]

        self.game_map._place_secret_areas()

        # 階段位置には配置されない（代替位置を探すが、この場合は配置されない可能性）
        # 少なくとも元の位置には hidden_tiles が作られない
        self.assertNotIn((10, 10), self.game_map.hidden_tiles)


if __name__ == "__main__":
    unittest.main()
