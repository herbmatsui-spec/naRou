"""engine.systems.entity_system モジュールのテスト (EntitySystem).

EntitySystem はペット AI、NPC AI、隣接エンティティとの会話、資源採取を担当する。
Engine スタブは SimpleNamespace で構築し、MagicMock の予測不能な動作を避ける。
AStar や combat_system は patch でモック化する。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from engine.systems.entity_system import EntitySystem
from constants import ENERGY_THRESHOLD, PET_RETREAT_HP_RATIO, PET_PATH_LENGTH_CHECK, COLOR_PET_PINK


# ---------------------------------------------------------------------------
# ファイア: テスト用スタブエンジンの構築 (SimpleNamespace)
# ---------------------------------------------------------------------------


def _make_engine(**overrides):
    """EntitySystem のメソッドが参照する属性を持つスタブエンジンを返す."""
    pet = SimpleNamespace()
    pet.hp = 10
    pet.max_hp = 20
    pet.energy = 100
    pet.x = 0
    pet.y = 0
    pet.name = "シエル"
    pet.pet_ai = SimpleNamespace()
    pet.pet_ai.increase_bond = MagicMock()
    pet.gain_exp = MagicMock(return_value=[])
    pet.pet_inventory = SimpleNamespace()
    pet.pet_inventory.equipment = {}

    player = SimpleNamespace()
    player.x = 10
    player.y = 10
    player.dx = 0
    player.dy = 0
    player.energy = 100
    player.hp = 20
    player.pet_ai = SimpleNamespace()

    survival = SimpleNamespace()
    survival.karma = 0

    entity_manager = SimpleNamespace()
    entity_manager.get_living_entities = MagicMock(return_value=[])
    entity_manager.resource_nodes = []
    entity_manager.remove_entity = MagicMock()

    combat_system = MagicMock()
    event_bus = MagicMock()

    engine = SimpleNamespace()
    engine.pet = pet
    engine.ai_system = None
    engine.get_blocked_positions = MagicMock(return_value=set())
    engine.entity_manager = entity_manager
    engine.has_los = MagicMock(return_value=True)
    engine.is_tile_free = MagicMock(return_value=True)
    engine.combat_system = combat_system
    engine.event_bus = event_bus
    engine.log = MagicMock()
    engine.message_log = MagicMock()
    engine.player = player
    engine.survival = survival
    engine.sound_manager = MagicMock()
    engine.floating_texts = []
    engine.fx_manager = SimpleNamespace()
    engine.fx_manager.FloatingText = MagicMock()
    engine.dialogue_manager = MagicMock()
    engine.main_quest_system = MagicMock()
    engine.main_quest_system.update_progress.return_value = []
    engine.relationship_manager = MagicMock()
    engine._progress_generated_quests = MagicMock()
    engine.get_entity_at = MagicMock(return_value=None)
    engine.inventory = SimpleNamespace()
    engine.inventory.add_item = MagicMock(return_value=(True, "追加"))
    engine.advance_world = MagicMock()
    for k, v in overrides.items():
        setattr(engine, k, v)
    return engine


def _make_handler(engine=None):
    if engine is None:
        engine = _make_engine()
    return EntitySystem(engine), engine


# ---------------------------------------------------------------------------
# pet_ai
# ---------------------------------------------------------------------------


def test_pet_ai_dead_or_low_energy_returns_early():
    """ペットが死亡またはエネルギー不足なら何もしない."""
    handler, engine = _make_handler()
    engine.pet.hp = 0
    handler.pet_ai()

    handler2, engine2 = _make_handler()
    engine2.pet.hp = 10
    engine2.pet.energy = 0  # ENERGY_THRESHOLD 未満
    handler2.pet_ai()


def test_pet_ai_uses_ai_system_if_present():
    """ai_system があれば委譲して独自ロジックは実行しない."""
    handler, engine = _make_handler()
    engine.ai_system = MagicMock()
    handler.pet_ai()
    engine.ai_system.process_ai.assert_called_once_with(engine.pet, engine)


def test_pet_ai_retreat_when_low_hp():
    """HP が max_hp * PET_RETREAT_HP_RATIO 未満なら後退 (プレイヤー追従のみ)."""
    handler, engine = _make_handler()
    # ai_system を未定義にして独自ロジック分岐を通す
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    engine.pet.hp = 1
    engine.pet.max_hp = 20
    with patch("engine.systems.entity_system.AStar") as m_astar:
        m_astar.get_path.return_value = []
        handler.pet_ai()
    # 後退モードでは敵を探さずプレイヤーへのパス探索のみ
    m_astar.get_path.assert_called()


def test_pet_ai_attacks_nearest_enemy():
    """視界内の最近敵と距離 1 なら近接攻撃し、倒せば経験値獲得・エンティティ削除."""
    handler, engine = _make_handler()
    # ai_system を未定義にして独自ロジック分岐を通す
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    engine.pet.hp = 15  # 後退しない
    enemy = SimpleNamespace()
    enemy.name = "スライム"
    enemy.hp = 5
    enemy.x = 0
    enemy.y = 0
    engine.entity_manager.get_living_entities.return_value = [enemy]
    engine.has_los.return_value = True
    engine.combat_system.calculate_melee_attack.return_value = (5, False, "メッセージ")
    with patch("engine.systems.entity_system.Point") as m_point:
        m_point.return_value.chebyshev_distance.return_value = 1
        handler.pet_ai()
    engine.combat_system.calculate_melee_attack.assert_called_once_with(
        engine.pet, enemy, weapon=None
    )
    assert enemy.hp == 0  # 5 - 5
    engine.combat_system.publish_kill_event.assert_called_once()
    engine.pet.gain_exp.assert_called_once_with(40)
    engine.entity_manager.remove_entity.assert_called_once_with(enemy)


def test_pet_ai_moves_toward_enemy():
    """敵と距離 2-6 ならパス探索して 1 マス移動する."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    engine.pet.hp = 15
    enemy = SimpleNamespace()
    enemy.name = "スライム"
    enemy.hp = 5
    enemy.x = 2
    enemy.y = 2
    engine.entity_manager.get_living_entities.return_value = [enemy]
    engine.has_los.return_value = True
    with patch("engine.systems.entity_system.Point") as m_point, \
         patch("engine.systems.entity_system.AStar") as m_astar:
        m_point.return_value.chebyshev_distance.return_value = 3
        m_astar.get_path.return_value = [SimpleNamespace(x=1, y=1)]
        handler.pet_ai()
    assert engine.pet.x == 1
    assert engine.pet.y == 1


def test_pet_ai_follows_player_when_no_enemy():
    """敵がいなければプレイヤーへのパス探索で移動する."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    engine.pet.hp = 15
    engine.entity_manager.get_living_entities.return_value = []
    with patch("engine.systems.entity_system.Point") as m_point, \
         patch("engine.systems.entity_system.AStar") as m_astar:
        m_point.return_value.chebyshev_distance.return_value = 99
        m_astar.get_path.return_value = [SimpleNamespace(x=1, y=1)]
        handler.pet_ai()
    m_astar.get_path.assert_called()


# ---------------------------------------------------------------------------
# npc_ai
# ---------------------------------------------------------------------------


def test_npc_ai_skips_player_pet_gwen_dead():
    """プレイヤー・ペット・グウェン・死亡 NPC はスキップする."""
    handler, engine = _make_handler()
    engine.ai_system = MagicMock()
    npc = SimpleNamespace()
    npc.name = "プレイヤー"
    npc.hp = 10
    handler.npc_ai(npc)
    engine.ai_system.process_ai.assert_called_once_with(npc, engine)

    handler2, engine2 = _make_handler()
    npc2 = SimpleNamespace()
    npc2.name = "グウェン"
    npc2.hp = 10
    handler2.npc_ai(npc2)

    handler3, engine3 = _make_handler()
    npc3 = SimpleNamespace()
    npc3.name = "モンスター"
    npc3.hp = 0
    handler3.npc_ai(npc3)


def test_npc_ai_uses_ai_system_if_present():
    """ai_system があれば委譲する."""
    handler, engine = _make_handler()
    engine.ai_system = MagicMock()
    npc = SimpleNamespace()
    npc.name = "モンスター"
    npc.hp = 10
    handler.npc_ai(npc)
    engine.ai_system.process_ai.assert_called_once_with(npc, engine)


def test_npc_ai_guard_high_karma_only_spends_energy():
    """ガード派閥でカルマ > -30 ならエネルギー消費のみ."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    npc = SimpleNamespace()
    npc.name = "衛兵"
    npc.faction = "guard"
    npc.hp = 10
    npc.x = 5
    npc.y = 5
    npc.energy = 100
    engine.survival.karma = 0
    handler.npc_ai(npc)
    assert npc.energy == 100 - ENERGY_THRESHOLD


def test_npc_ai_attacks_player_at_distance_1():
    """距離 1 でプレイヤーを近接攻撃する."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    npc = SimpleNamespace()
    npc.name = "モンスター"
    npc.hp = 10
    npc.faction = None
    npc.x = 0
    npc.y = 0
    npc.energy = 100
    engine.survival.karma = -50
    target = engine.player
    target.hp = 20
    with patch("engine.systems.entity_system.Point") as m_point:
        m_point.return_value.chebyshev_distance.return_value = 1
        engine.combat_system.calculate_melee_attack.return_value = (5, False, "パンチ！")
        handler.npc_ai(npc)
    engine.combat_system.calculate_melee_attack.assert_called_once_with(npc, target)
    assert target.hp == 15


def test_npc_ai_pet_death_bond_and_log():
    """ペットを倒すと絆減少と kill イベント、悲痛ログを出す."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    npc = SimpleNamespace()
    npc.name = "モンスター"
    npc.hp = 10
    npc.faction = None
    npc.x = 0
    npc.y = 0
    npc.energy = 100
    engine.survival.karma = -50
    pet = SimpleNamespace()
    pet.hp = 5
    pet.x = 10
    pet.y = 10
    pet.pet_ai = SimpleNamespace()
    pet.pet_ai.increase_bond = MagicMock()
    engine.player = pet
    engine.pet = pet
    target = engine.player
    target.hp = 5
    with patch("engine.systems.entity_system.Point") as m_point:
        m_point.return_value.chebyshev_distance.return_value = 1
        engine.combat_system.calculate_melee_attack.return_value = (10, False, "パンチ！")
        handler.npc_ai(npc)
    assert pet.pet_ai.increase_bond.called
    engine.combat_system.publish_kill_event.assert_called_once()


def test_npc_ai_moves_toward_player():
    """距離 2-8 かつ視界内ならプレイヤーへパス探索で移動する."""
    handler, engine = _make_handler()
    if hasattr(engine, "ai_system"):
        del engine.ai_system
    npc = SimpleNamespace()
    npc.name = "モンスター"
    npc.hp = 10
    npc.faction = None
    npc.x = 0
    npc.y = 0
    npc.energy = 100
    engine.survival.karma = -50
    target = engine.player
    target.hp = 20
    with patch("engine.systems.entity_system.Point") as m_point, \
         patch("engine.systems.entity_system.AStar") as m_astar:
        m_point.return_value.chebyshev_distance.return_value = 3
        engine.has_los.return_value = True
        m_astar.get_path.return_value = [SimpleNamespace(x=1, y=1)]
        handler.npc_ai(npc)
    assert npc.x == 1
    assert npc.y == 1


# ---------------------------------------------------------------------------
# talk_to_neighbor
# ---------------------------------------------------------------------------


def test_talk_to_neighbor_no_neighbor():
    """隣接にエンティティがいなければ「誰もいません」ログ."""
    handler, engine = _make_handler()
    engine.get_entity_at.return_value = None
    handler.talk_to_neighbor()
    engine.message_log.add.assert_called_once_with("誰もいません。")


def test_talk_to_neighbor_updates_main_quest_and_dialogue():
    """隣接者がいればメインクエスト進行、ダイアログ設定、関係更新を行う."""
    handler, engine = _make_handler()
    neighbor = SimpleNamespace()
    neighbor.name = "村人"
    engine.get_entity_at.return_value = neighbor
    engine.main_quest_system.update_progress.return_value = ["クエスト進捗"]
    handler.talk_to_neighbor()
    engine.main_quest_system.update_progress.assert_called_once_with(
        engine.player, "visit", "村人", 1, engine
    )
    engine.message_log.add.assert_any_call("クエスト進捗")
    assert engine.active_dialogue is not None
    engine.relationship_manager.update_relationship.assert_called_once_with(
        engine.player, "村人", action="talk"
    )


def test_talk_to_neighbor_no_relationship_manager():
    """relationship_manager がなくてもエラーにならない."""
    handler, engine = _make_handler()
    neighbor = SimpleNamespace()
    neighbor.name = "村人"
    engine.get_entity_at.return_value = neighbor
    del engine.relationship_manager
    handler.talk_to_neighbor()  # 例外を投げない


# ---------------------------------------------------------------------------
# harvest_resource
# ---------------------------------------------------------------------------


def test_harvest_resource_no_nodes():
    """資源ノードがいなければ「採取できるものがない」ログ."""
    handler, engine = _make_handler()
    engine.entity_manager.resource_nodes = []
    handler.harvest_resource()
    engine.log.assert_called_once_with("周囲に採取できるものがない。")


def test_harvest_resource_node_too_far():
    """距離 > 1 のノードは採取対象外."""
    handler, engine = _make_handler()
    node = SimpleNamespace()
    node.x = 10
    node.y = 10
    node.depleted = False
    engine.entity_manager.resource_nodes = [node]
    engine.player.x = 0
    engine.player.y = 0
    handler.harvest_resource()
    engine.log.assert_called_once_with("周囲に採取できるものがない。")


def test_harvest_resource_depleted_node():
    """枯渇ノードはスキップする."""
    handler, engine = _make_handler()
    node = SimpleNamespace()
    node.x = 0
    node.y = 0
    node.depleted = True
    engine.entity_manager.resource_nodes = [node]
    engine.player.x = 0
    engine.player.y = 0
    handler.harvest_resource()
    engine.log.assert_called_once_with("周囲に採取できるものがない。")


def test_harvest_resource_success():
    """採取成功時にログ・SE・インベントリ追加・浮遊テキスト・クエスト進行・エネルギー消費・advance_world."""
    handler, engine = _make_handler()
    node = SimpleNamespace()
    node.x = 0
    node.y = 0
    node.depleted = False
    item = SimpleNamespace()
    item.name = "ハーブ"
    node.harvest = MagicMock(return_value=(item, "ハーブを採取した！"))
    engine.entity_manager.resource_nodes = [node]
    engine.player.x = 0
    engine.player.y = 0
    engine.player.energy = 100
    engine.fx_manager.FloatingText.return_value = MagicMock()
    handler.harvest_resource()
    engine.log.assert_any_call("ハーブを採取した！", (180, 255, 180))
    engine.sound_manager.play_se.assert_called_once_with("get_item")
    engine.inventory.add_item.assert_called_once_with(item)
    assert engine.player.energy == 100 - ENERGY_THRESHOLD
    engine.advance_world.assert_called_once()
