"""
test_procedural_dungeon.py
プロシージャルダンジョン生成のテスト
"""
import sys

sys.path.insert(0, r"E:\narou3\naRou")

from skill_eater_procedural_dungeon import (
    ROOM_TEMPLATES,
    THEME_ROOM_WEIGHTS,
    DungeonTheme,
    RoomType,
    SkillEaterProceduralDungeon,
)


def test_room_templates_exist():
    assert len(ROOM_TEMPLATES) == 10
    assert RoomType.CORRIDOR in ROOM_TEMPLATES
    assert RoomType.BOSS_ROOM in ROOM_TEMPLATES
    assert RoomType.SECRET_ROOM in ROOM_TEMPLATES
    print("[OK] Room templates defined correctly")


def test_theme_weights_exist():
    for theme in DungeonTheme:
        assert theme in THEME_ROOM_WEIGHTS
        weights = THEME_ROOM_WEIGHTS[theme]
        assert len(weights) > 0
    print("[OK] Theme weights defined correctly")


def test_floor_generation():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(42)
    floor = dungeon.generate_floor(1)

    assert floor.floor_id == "floor_1"
    assert floor.depth == 1
    assert floor.theme == DungeonTheme.INDUSTRIAL_RUINS
    assert len(floor.rooms) >= 8
    assert len(floor.rooms) <= 15
    assert floor.entrance_id != ""
    assert floor.exit_id != ""
    assert floor.boss_room_id != ""
    print(f"[OK] Floor generated: {len(floor.rooms)} rooms, entrance={floor.entrance_id}, exit={floor.exit_id}")


def test_all_nodes_connected():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(123)
    floor = dungeon.generate_floor(3)

    from collections import deque
    visited = set()
    queue = deque([floor.entrance_id])
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = floor.rooms.get(node_id)
        if node:
            for conn in node.connections:
                if conn not in visited:
                    queue.append(conn)

    assert len(visited) == len(floor.rooms), f"Not all rooms connected: {len(visited)}/{len(floor.rooms)}"
    print(f"[OK] All {len(visited)} rooms connected via MST + loops")


def test_secret_room_generation():
    found_secret = False
    for seed in range(100):
        dungeon = SkillEaterProceduralDungeon()
        dungeon.set_seed(seed)
        floor = dungeon.generate_floor(5)
        for node in floor.rooms.values():
            if node.room_type == RoomType.SECRET_ROOM:
                found_secret = True
                break
        if found_secret:
            break

    assert found_secret, "Secret room should generate with some probability"
    print("[OK] Secret room generation works")


def test_floor_progression():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(456)
    floor1 = dungeon.generate_floor(1)
    floor2 = dungeon.generate_floor(2)
    floor6 = dungeon.generate_floor(6)
    floor11 = dungeon.generate_floor(11)
    floor16 = dungeon.generate_floor(16)

    assert floor1.theme == DungeonTheme.INDUSTRIAL_RUINS
    assert floor2.theme == DungeonTheme.INDUSTRIAL_RUINS
    assert floor6.theme == DungeonTheme.NEON_SEWERS
    assert floor11.theme == DungeonTheme.MIDAS_LABS
    assert floor16.theme == DungeonTheme.BABEL_CORE
    print("[OK] Theme progression by depth works")


def test_exploration_log():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(789)
    floor = dungeon.generate_floor(1)

    dungeon.add_log_entry("floor_1", floor.entrance_id, "MOVE_ROOM", discovered_items=["item1"])
    dungeon.log_combat_encounter("floor_1", floor.entrance_id, ["enemy1"], "VICTORY")
    dungeon.log_treasure_found("floor_1", floor.entrance_id, ["gold", "potion"])
    dungeon.log_trap_triggered("floor_1", floor.entrance_id, "spike", 10)

    assert len(dungeon.exploration_log) == 4
    logs_by_floor = dungeon.get_logs_by_floor("floor_1")
    assert len(logs_by_floor) == 4
    combat_logs = dungeon.get_logs_by_action("COMBAT_VICTORY")
    assert len(combat_logs) == 1
    json_logs = dungeon.export_logs_json()
    assert len(json_logs) == 4
    print("[OK] Exploration logging works")


def test_exploration_progress():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(999)
    floor = dungeon.generate_floor(1)

    initial_progress = dungeon.exploration_progress
    assert initial_progress > 0

    for room_id in list(floor.rooms.keys())[:3]:
        dungeon.log_room_discovery("floor_1", room_id)

    progress_after = dungeon.exploration_progress
    assert progress_after > initial_progress

    floor_progress = dungeon.get_floor_progress("floor_1")
    assert floor_progress > 0
    print(f"[OK] Exploration progress: initial={initial_progress:.2f}, after={progress_after:.2f}, floor={floor_progress:.2f}")


def test_minimap_data():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(111)
    floor = dungeon.generate_floor(1)

    minimap = dungeon.get_minimap_data()
    assert "nodes" in minimap
    assert "connections" in minimap
    assert minimap["current_room"] == floor.entrance_id
    assert len(minimap["nodes"]) == len(floor.rooms)
    print(f"[OK] Minimap data: {len(minimap['nodes'])} nodes, {len(minimap['connections'])} connections")


def test_navigation():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(222)
    floor = dungeon.generate_floor(1)

    connected = dungeon.get_connected_rooms(floor.entrance_id)
    assert len(connected) > 0

    target = connected[0].node_id
    path = dungeon.find_path(floor.entrance_id, target)
    assert len(path) >= 2
    assert path[0] == floor.entrance_id
    assert path[-1] == target
    print(f"[OK] Pathfinding works: {path}")


def test_floor_transition():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(333)
    floor1 = dungeon.generate_floor(1)
    floor2 = dungeon.generate_floor(2)

    assert dungeon.current_floor_id == "floor_1"
    assert dungeon.current_room_id == floor1.entrance_id

    # Use auto_explore to navigate to exit
    results = dungeon.auto_explore(floor1.exit_id)
    assert len(results) > 0
    last_result = results[-1]
    assert last_result.action_type == "MOVE_ROOM"
    assert dungeon.current_room_id == floor1.exit_id

    result = dungeon.descend_stairs()
    assert dungeon.current_floor_id == "floor_2"
    assert dungeon.current_room_id == floor2.entrance_id

    # Ascend back
    result2 = dungeon.ascend_stairs()
    assert dungeon.current_floor_id == "floor_1"
    print("[OK] Floor transitions work")


def test_serialization():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(444)
    dungeon.generate_floor(1)
    dungeon.generate_floor(2)
    dungeon.log_room_discovery("floor_1", dungeon.floors["floor_1"].entrance_id)

    data = dungeon.to_dict()
    assert "floors" in data
    assert "current_floor_id" in data
    assert "exploration_log" in data

    restored = SkillEaterProceduralDungeon.from_dict(data)
    assert restored.current_floor_id == dungeon.current_floor_id
    assert restored.current_room_id == dungeon.current_room_id
    assert len(restored.floors) == len(dungeon.floors)
    assert len(restored.exploration_log) == len(dungeon.exploration_log)
    print("[OK] Serialization/deserialization works")


def test_explore_command():
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(555)
    floor = dungeon.generate_floor(1)

    connected = dungeon.get_connected_rooms()
    if connected:
        target = connected[0].node_id
        result = dungeon.explore_command("move", target)
        assert result.action_type == "MOVE_ROOM"

    result = dungeon.explore_command("map")
    assert result.action_type == "MAP"

    result = dungeon.explore_command("log")
    assert result.action_type == "LOG"

    result = dungeon.explore_command("unknown")
    assert result.action_type == "UNKNOWN"
    print("[OK] Explore commands work")


if __name__ == "__main__":
    test_room_templates_exist()
    test_theme_weights_exist()
    test_floor_generation()
    test_all_nodes_connected()
    test_secret_room_generation()
    test_floor_progression()
    test_exploration_log()
    test_exploration_progress()
    test_minimap_data()
    test_navigation()
    test_floor_transition()
    test_serialization()
    test_explore_command()
    print("\n=== All tests passed! ===")
