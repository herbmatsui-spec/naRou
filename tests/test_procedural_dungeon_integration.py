"""
test_procedural_dungeon_integration.py
プロシージャルダンジョンと探索システムの統合テスト
"""
import sys

sys.path.insert(0, r"E:\narou3\naRou")

from skill_eater_exploration_system import SkillEaterExplorationSystem
from skill_eater_procedural_dungeon import SkillEaterProceduralDungeon


def test_procedural_dungeon_integration():
    """プロシージャルダンジョンが探索システムと正しく統合されることを確認"""
    # 探索システムを作成
    exploration = SkillEaterExplorationSystem()

    # プロシージャルダンジョンを作成
    dungeon = SkillEaterProceduralDungeon()
    dungeon.set_seed(42)

    # 最初のフロアを生成
    floor = dungeon.generate_floor(1)

    # 探索システムにプロシージャルダンジョンを設定
    exploration.set_procedural_dungeon(dungeon)

    # 現在の部屋が設定されていることを確認
    current_room = exploration.get_current_room()
    assert current_room is not None
    assert current_room.room_id == floor.entrance_id

    # 接続部屋が取得できることを確認
    connected = exploration.get_connected_rooms()
    assert len(connected) > 0

    # ミニマップデータが取得できることを確認
    minimap = exploration.get_minimap_data()
    assert "nodes" in minimap
    assert len(minimap["nodes"]) == len(floor.rooms)

    # 探索進行度が取得できることを確認
    progress = exploration.exploration_progress
    assert progress > 0

    # 部屋移動がプロシージャルダンジョン経由で動作することを確認
    if connected:
        target = connected[0]
        result = exploration.move_to_room(target)
        assert result.action_type == "MOVE_ROOM"
        assert exploration.current_room_id == target

    # 階層移動が動作することを確認（出口まで移動してから）
    results = exploration._procedural_dungeon.auto_explore(floor.exit_id)
    assert len(results) > 0

    descend_result = exploration.descend_stairs()
    assert descend_result.action_type == "DESCEND"
    assert exploration._procedural_dungeon.current_floor_id == "floor_2"

    print("[OK] Procedural dungeon integration works")


def test_legacy_mode_still_works():
    """レガシーモード（ハードコード部屋）がまだ動作することを確認"""
    exploration = SkillEaterExplorationSystem()

    # プロシージャルダンジョンを設定しない
    assert exploration._use_procedural is False

    # レガシー部屋が存在することを確認
    assert "slum_alley" in exploration.dungeon_rooms
    assert "vault_chamber" in exploration.dungeon_rooms

    # レガシー移動が動作することを確認
    result = exploration.move_to_room("underground_market")
    assert result.action_type == "MOVE_ROOM"
    assert exploration.current_room_id == "underground_market"

    # レガシー機能が動作することを確認
    result = exploration.open_treasure_chest()
    assert result.action_type == "LOOT_CHEST"

    result = exploration.escape_combat()
    assert result.action_type == "ESCAPE"

    result = exploration.trigger_trap_door()
    assert result.action_type == "TRAP"

    print("[OK] Legacy mode still works")


if __name__ == "__main__":
    test_procedural_dungeon_integration()
    test_legacy_mode_still_works()
    print("\n=== All integration tests passed! ===")
