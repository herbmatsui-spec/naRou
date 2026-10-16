"""core/world_state_manager モジュールのテスト。

GameStateInitializer.initialize_world_state() の正常系・異常系をカバーする。
エンジンと依存モジュール (constants, ecs.entity, game_state, item_system, map_engine, systems)
はすべてモックして外部依存を避ける。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core import world_state_manager


def _make_engine(player_cfg=None, pet_cfg=None):
    """テスト用のモックエンジンを作成する。"""
    if player_cfg is None:
        player_cfg = {
            "start_x": 20,
            "start_y": 20,
            "char": "@",
            "color": [255, 255, 255],
            "name": "テスト冒険者",
            "speed": 85,
            "attributes": {},
            "world": "main",
        }
    if pet_cfg is None:
        pet_cfg = {
            "start_x": 21,
            "start_y": 20,
            "char": "p",
            "color": [255, 180, 210],
            "name": "テストペット",
            "speed": 90,
            "attributes": {},
        }
    config_mgr = MagicMock()
    config_mgr.get_player_config.return_value = player_cfg
    config_mgr.get_pet_config.return_value = pet_cfg
    return SimpleNamespace(config_mgr=config_mgr)


def _start_patches():
    """world_state_manager が依存するすべての名前をモックして開始する。"""
    mock_entity = MagicMock()
    mock_game_state_data = MagicMock()
    mock_inventory = MagicMock()
    mock_game_map = MagicMock()
    mock_game_map.return_value.rooms = []
    mock_game_map.return_value.start_pos = (10, 10)
    mock_quest = MagicMock()
    mock_survival = MagicMock()

    patchers = [
        patch.object(world_state_manager, "Entity", mock_entity),
        patch.object(world_state_manager, "GameStateData", mock_game_state_data),
        patch.object(world_state_manager, "Inventory", mock_inventory),
        patch.object(world_state_manager, "GameMap", mock_game_map),
        patch.object(world_state_manager, "Quest", mock_quest),
        patch.object(world_state_manager, "SurvivalSystem", mock_survival),
        patch.object(world_state_manager, "MAP_WIDTH", 80),
        patch.object(world_state_manager, "MAP_HEIGHT", 50),
        patch.object(world_state_manager, "GameState", MagicMock()),
    ]
    for p in patchers:
        p.start()
    return {
        "Entity": mock_entity,
        "GameStateData": mock_game_state_data,
        "Inventory": mock_inventory,
        "GameMap": mock_game_map,
        "Quest": mock_quest,
        "SurvivalSystem": mock_survival,
    }


def test_initialize_world_state_returns_gamestatedata():
    """initialize_world_state() が GameStateData インスタンスを返す。"""
    mocks = _start_patches()
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        result = initializer.initialize_world_state()
        assert result is mocks["GameStateData"].return_value
        # GameMap が生成され generate_dungeon が呼ばれる
        mocks["GameMap"].assert_called_once()
        mocks["GameMap"].return_value.generate_dungeon.assert_called_once()
    finally:
        patch.stopall()


def test_initialize_world_state_player_and_pet_created():
    """プレイヤーとペットがエンティティとして作成される。"""
    mocks = _start_patches()
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        initializer.initialize_world_state()
        # Entity がプレイヤーとペットの2回呼ばれる
        assert mocks["Entity"].call_count == 2
        player_call = mocks["Entity"].call_args_list[0]
        pet_call = mocks["Entity"].call_args_list[1]
        assert player_call.kwargs["is_player"] is True
        assert pet_call.kwargs["is_pet"] is True
    finally:
        patch.stopall()


def test_initialize_world_state_inventory_created():
    """プレイヤー用・ペット用インベントリが作成される。"""
    mocks = _start_patches()
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        initializer.initialize_world_state()
        # Inventory が2回呼ばれる (player, pet)
        assert mocks["Inventory"].call_count == 2
        player_inv_call = mocks["Inventory"].call_args_list[0]
        pet_inv_call = mocks["Inventory"].call_args_list[1]
        assert player_inv_call.kwargs["max_items"] == 26
        assert player_inv_call.kwargs["max_weight"] == 60.0
        assert pet_inv_call.kwargs["max_items"] == 12
        assert pet_inv_call.kwargs["max_weight"] == 30.0
    finally:
        patch.stopall()


def test_initialize_world_state_quests_created():
    """2つのクエストが作成される。"""
    mocks = _start_patches()
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        initializer.initialize_world_state()
        # Quest が2回呼ばれる
        assert mocks["Quest"].call_count == 2
        quest1_call = mocks["Quest"].call_args_list[0]
        quest2_call = mocks["Quest"].call_args_list[1]
        assert quest1_call.kwargs["title"] == "ぷち掃討の栄誉"
        assert quest1_call.kwargs["target_monster"] == "ぷち"
        assert quest1_call.kwargs["target_count"] == 3
        assert quest1_call.kwargs["reward_gold"] == 350
        assert quest1_call.kwargs["reward_platinum"] == 2
        assert quest2_call.kwargs["title"] == "オーク討伐令"
        assert quest2_call.kwargs["target_monster"] == "オーク"
        assert quest2_call.kwargs["target_count"] == 2
        assert quest2_call.kwargs["reward_gold"] == 750
        assert quest2_call.kwargs["reward_platinum"] == 3
    finally:
        patch.stopall()


def test_initialize_world_state_game_state_fields():
    """ゲーム状態の各フィールドが正しく設定される。"""
    mocks = _start_patches()
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        result = initializer.initialize_world_state()
        state = mocks["GameStateData"].return_value

        # マップ関連
        assert state.dungeon_level == 1
        assert state.game_map is mocks["GameMap"].return_value
        # プレイヤー位置がマップの start_pos に更新される
        assert state.player.x == 10
        assert state.player.y == 10
        # ペット位置はプレイヤーの隣
        assert state.pet.x == 11
        assert state.pet.y == 10

        # ゲーム状態
        assert state.game_state == "play"
        assert state.current_world == "main"
        assert state.world_a_data == {}
        assert state.help_tab == 0
        assert state.inventory_target == "player"
        assert state.inventory_cursor == 0
        assert state.inventory_tab == 0
        assert state.active_dialogue is None
        assert state.wish_input == ""
        assert state.debug_input == ""
        assert state.turns == 0
        assert state.arch_interpret_active is False
        assert state.arch_interpret_groups_cache == []
        assert state.arch_interpret_truth_idx == 0
        assert state.arch_interpret_ending_idx == 0
    finally:
        patch.stopall()


def test_initialize_world_state_altar_pos_with_rooms():
    """マップに部屋がある場合、祭壇位置は最初の部屋の中心ベースで設定される。"""
    mocks = _start_patches()
    mocks["GameMap"].return_value.rooms = [SimpleNamespace(center=(30, 20))]
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        initializer.initialize_world_state()
        state = mocks["GameStateData"].return_value
        # rx=30, ry=20 → altar_pos = (32, 20)
        assert state.altar_pos == (32, 20)
    finally:
        patch.stopall()


def test_initialize_world_state_altar_pos_without_rooms():
    """マップに部屋がない場合、祭壇位置はプレイヤー位置ベースで設定される。"""
    mocks = _start_patches()
    mocks["GameMap"].return_value.rooms = []
    mocks["GameMap"].return_value.start_pos = (10, 10)
    try:
        engine = _make_engine()
        initializer = world_state_manager.GameStateInitializer(engine)
        initializer.initialize_world_state()
        state = mocks["GameStateData"].return_value
        # プレイヤー位置は start_pos (10,10) に更新済み → altar_pos = (12, 10)
        assert state.altar_pos == (12, 10)
    finally:
        patch.stopall()


def test_initialize_world_state_custom_config():
    """カスタム設定が反映される。"""
    mocks = _start_patches()
    player_cfg = {
        "start_x": 5,
        "start_y": 7,
        "char": "#",
        "color": [100, 100, 100],
        "name": "カスタム名",
        "speed": 50,
        "attributes": {"str": 10},
        "world": "skill_eater",
    }
    pet_cfg = {
        "start_x": 6,
        "start_y": 7,
        "char": "q",
        "color": [50, 50, 50],
        "name": "カスタムペット",
        "speed": 60,
        "attributes": {},
    }
    engine = _make_engine(player_cfg=player_cfg, pet_cfg=pet_cfg)
    initializer = world_state_manager.GameStateInitializer(engine)
    initializer.initialize_world_state()
    # Entity 呼び出しにカスタム設定が渡されている
    player_call = mocks["Entity"].call_args_list[0]
    assert player_call.kwargs["name"] == "カスタム名"
    assert player_call.kwargs["char"] == "#"
    assert player_call.kwargs["speed"] == 50
    assert player_call.kwargs["attributes"] == {"str": 10}
    assert player_call.kwargs["x"] == 5
    assert player_call.kwargs["y"] == 7
    pet_call = mocks["Entity"].call_args_list[1]
    assert pet_call.kwargs["name"] == "カスタムペット"
    assert pet_call.kwargs["char"] == "q"
    assert pet_call.kwargs["speed"] == 60
    assert pet_call.kwargs["x"] == 6
    assert pet_call.kwargs["y"] == 7
    # state の current_world
    state = mocks["GameStateData"].return_value
    assert state.current_world == "skill_eater"
    patch.stopall()
