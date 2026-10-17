"""T37 案B: ダンジョン生成多様性と扉/トラップギミックのテスト

tests/test_reachability.py と同じ精神で、生成されたダンジョンが
「閉扉は踏み込み/攻撃で開放可能なギミックであり、到達を完全封鎖しない」
こと (開ければ階段へ到達可能) を検証する。
"""

from __future__ import annotations

import random
from collections import deque

from map_engine import GameMap
from procedural_dungeon_generator import ProceduralDungeonGenerator

_MAP_W, _MAP_H = 48, 36


def _generate_map(seed: int, **kwargs) -> GameMap:
    """シード固定で GameMap を生成する"""
    random.seed(seed)
    game_map = GameMap(_MAP_W, _MAP_H, "dungeon", kwargs.pop("floor_level", 1))
    game_map.generate_dungeon(**kwargs)
    return game_map


def _count_doors(game_map: GameMap) -> int:
    return sum(
        1
        for x in range(game_map.width)
        for y in range(game_map.height)
        if game_map.tiles[x][y] == "TILE_DOOR_CLOSED"
    )


def _count_traps(game_map: GameMap) -> int:
    """可視罠 + 隠し罠の合計数"""
    visible = sum(
        1
        for x in range(game_map.width)
        for y in range(game_map.height)
        if game_map.tiles[x][y] == "TILE_TRAP"
    )
    return visible + len(game_map.trap_data)


def _reachable_positions(game_map: GameMap, treat_door_open: bool) -> set[tuple[int, int]]:
    """開始位置から BFS で到達可能な座標集合を返す

    treat_door_open=True は「閉扉を踏み込み/攻撃で開けられる」状態を模擬する
    (開扉コストはあるが到達は可能なギミック)。
    """
    start = game_map.start_pos
    seen: set[tuple[int, int]] = {start}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in seen or not game_map.is_in_bounds(nx, ny):
                continue
            tile = game_map.tiles[nx][ny]
            if tile == "TILE_DOOR_CLOSED":
                if treat_door_open:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
                continue
            if game_map.is_walkable(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def test_room_shape_variety_over_20_generations():
    """20回生成で矩形以外 (L字/十字) の部屋形状が出ること"""
    shapes: set[str] = set()
    for seed in range(20):
        game_map = _generate_map(seed, max_rooms=20, use_variety=True, door_chance=0.0)
        shapes.update(game_map.room_shapes)
        assert len(game_map.room_shapes) == len(game_map.rooms)

    assert "rect" in shapes, "従来の矩形部屋が消えてはいけない"
    assert "l_shape" in shapes, f"L字部屋が20回中1つも生成されない: {shapes}"
    assert "cross" in shapes, f"十字部屋が20回中1つも生成されない: {shapes}"


def test_corridor_style_variety():
    """直線廊下とL字廊下が混在すること"""
    styles: set[str] = set()
    for seed in range(20):
        game_map = _generate_map(seed, max_rooms=20, use_variety=True, door_chance=0.0)
        styles.update(game_map.corridor_styles)

    assert "L" in styles
    assert "straight" in styles, f"直線廊下が20回中1本も生成されない: {styles}"


def test_doors_generated_and_openable():
    """扉が生成され、閉状態は不通・開状態は通行可/透過になること"""
    total_doors = 0
    for seed in range(5):
        game_map = _generate_map(seed, max_rooms=20, use_variety=True, door_chance=0.9)
        doors = [
            (x, y)
            for x in range(game_map.width)
            for y in range(game_map.height)
            if game_map.tiles[x][y] == "TILE_DOOR_CLOSED"
        ]
        total_doors += len(doors)

        for x, y in doors:
            # 閉扉は通行不可・視線遮断
            assert not game_map.is_walkable(x, y)
            assert not game_map.is_transparent(x, y)
            # 開扉操作で通行可・透過になる
            assert game_map.try_open_door(x, y) is True
            assert game_map.tiles[x][y] == "TILE_DOOR_OPEN"
            assert game_map.is_walkable(x, y)
            assert game_map.is_transparent(x, y)
            # 階段位置に扉は置かれない
            assert (x, y) not in (game_map.stairs_up_pos, game_map.stairs_down_pos)

    assert total_doors > 0, "door_chance=0.9 の5回生成で扉が1枚も出ない"


def test_try_open_door_rejects_non_door():
    """扉以外のタイルに対する開扉操作は False を返すこと"""
    game_map = _generate_map(0, max_rooms=10, use_variety=True, door_chance=0.0)
    floor_pos = next(
        (x, y)
        for x in range(game_map.width)
        for y in range(game_map.height)
        if game_map.tiles[x][y] == "TILE_FLOOR"
    )
    assert game_map.try_open_door(*floor_pos) is False
    assert game_map.try_open_door(-1, -1) is False


def test_stairs_reachable_with_openable_doors():
    """閉扉を開けられる状態で、開始位置から下り階段へ到達可能であること"""
    for seed in range(10):
        game_map = _generate_map(seed, max_rooms=20, use_variety=True, door_chance=0.9)
        assert game_map.stairs_down_pos is not None
        assert game_map.tiles[game_map.stairs_down_pos[0]][game_map.stairs_down_pos[1]] != (
            "TILE_DOOR_CLOSED"
        )
        reachable = _reachable_positions(game_map, treat_door_open=True)
        assert game_map.stairs_down_pos in reachable, (
            f"seed={seed}: 開扉可能なのに下り階段へ到達できない"
        )


def test_trap_depth_scaling_and_hidden_traps():
    """深度が深いほど罠が増え、隠し罠が存在すること"""
    shallow_total = 0
    deep_total = 0
    hidden_total = 0
    for seed in range(10):
        shallow = _generate_map(
            seed, floor_level=1, max_rooms=20, use_variety=True, door_chance=0.0
        )
        deep = _generate_map(
            seed + 100, floor_level=30, max_rooms=20, use_variety=True, door_chance=0.0
        )
        shallow_total += _count_traps(shallow)
        deep_total += _count_traps(deep)
        hidden_total += sum(1 for info in deep.trap_data.values() if info["hidden"])

    assert deep_total > shallow_total, (
        f"深度30の罠が深度1より少ない: shallow={shallow_total} deep={deep_total}"
    )
    assert hidden_total > 0, "深度30の10回生成で隠し罠が1つも出ない"


def test_check_trap_trigger():
    """罠踏みでダメージが返り、発動後は罠が解除されること"""
    game_map = GameMap(_MAP_W, _MAP_H, "dungeon", 1)
    # 可視罠: trap_data 登録 + TILE_TRAP タイル
    game_map.tiles[5][5] = "TILE_TRAP"
    game_map.trap_data[(5, 5)] = {"damage": 8, "hidden": False}

    result = game_map.check_trap_trigger(5, 5)
    assert result == {"damage": 8, "hidden": False}
    assert game_map.tiles[5][5] == "TILE_FLOOR"
    # 発動済み罠は二度と発動しない
    assert game_map.check_trap_trigger(5, 5) is None

    # 隠し罠: タイルは床のままで踏むと発動
    game_map.trap_data[(7, 7)] = {"damage": 5, "hidden": True}
    result = game_map.check_trap_trigger(7, 7)
    assert result == {"damage": 5, "hidden": True}
    assert game_map.check_trap_trigger(7, 7) is None

    # 罠のない床 / 範囲外
    assert game_map.check_trap_trigger(10, 10) is None
    assert game_map.check_trap_trigger(-1, 0) is None


def test_legacy_option_preserves_existing_generation():
    """use_variety=False で従来生成 (矩形のみ・扉なし) になること"""
    for seed in range(5):
        game_map = _generate_map(seed, max_rooms=20, use_variety=False)
        assert all(shape == "rect" for shape in game_map.room_shapes)
        assert _count_doors(game_map) == 0
        assert game_map.trap_data == {}


def test_procedural_generator_depth_scale():
    """generate_dungeon_map が深度スケール (world_layer整合式) に従うこと"""
    gen = ProceduralDungeonGenerator()

    for depth in (1, 30):
        random.seed(depth)
        game_map = gen.generate_dungeon_map(depth=depth)
        assert game_map.floor_level == depth
        # 部屋数 = 20 + depth//10 を超えない
        assert len(game_map.rooms) <= 20 + depth // 10
        assert game_map.rooms, f"depth={depth} で部屋が1つも生成されない"
        assert game_map.stairs_down_pos is not None
        # 扉が生成される (デフォルト door_chance=0.5)
        assert _count_doors(game_map) > 0 or depth == 1, (
            f"depth={depth} で扉が生成されない"
        )

    # 多様性オプションの無効化も委譲される
    random.seed(7)
    legacy_map = gen.generate_dungeon_map(depth=1, use_variety=False, door_chance=0.0)
    assert all(shape == "rect" for shape in legacy_map.room_shapes)
    assert _count_doors(legacy_map) == 0
