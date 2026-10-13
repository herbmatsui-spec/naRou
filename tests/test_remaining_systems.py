"""Unit tests for small uncovered system modules.

Covers:
- systems_manager.SystemManager (register/get/has/unregister/initialize_all/update_all)
- system_coordinator.SystemCoordinator (kernel delegation)
- managers/combat_manager.CombatManager (kill rewards, quest settlement)
- managers/skill_reward_manager.SkillRewardManager
- managers/world_news_manager.WorldNewsManager
- managers/context_menu_builder.ContextMenuBuilder
- managers/faction_manager.FactionManager
- event_scheduler.EventScheduler
- karma_system (REGISTRY.load, KarmaManager)
- god_system.GodInfo
- scaling (pure helper functions)
- job_queue.JobQueue
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

import scaling
from constants import CAT_FOOD, TILE_WALL
from event_scheduler import EventScheduler
from god_system import GodInfo
from job_queue import JobQueue
from karma_system import REGISTRY, KarmaData, KarmaManager, KarmaRegistry
from managers.combat_manager import CombatManager
from managers.context_menu_builder import ContextMenuBuilder
from managers.faction_manager import FactionManager
from managers.skill_reward_manager import SkillRewardManager
from managers.world_news_manager import WorldNewsManager
from system_coordinator import SystemCoordinator
from systems_manager import SystemManager

# =============================================================================
# systems_manager.SystemManager
# =============================================================================


class FullSystem:
    """System honoring the full protocol: initialize(engine) / update(engine, dt)."""

    def __init__(self):
        self.initialized_with = []
        self.updates = []

    def initialize(self, engine):
        self.initialized_with.append(engine)

    def update(self, engine, delta_time):
        self.updates.append((engine, delta_time))


class NoArgInitSystem:
    """System whose initialize/update take no extra args (fallback paths)."""

    def __init__(self):
        self.calls = []

    def initialize(self):
        self.calls.append("init")

    def update(self):
        self.calls.append("update")


class EngineOnlyUpdateSystem:
    """System whose update accepts only the engine (middle fallback path)."""

    def __init__(self):
        self.updates = []

    def update(self, engine):
        self.updates.append(engine)


class TestSystemManager:
    def test_init_starts_empty(self):
        mgr = SystemManager()
        assert mgr.systems == {}
        assert len(mgr) == 0

    def test_register_returns_system_and_stores_it(self):
        mgr = SystemManager()
        system = FullSystem()
        result = mgr.register("combat", system)
        assert result is system
        assert mgr.systems["combat"] is system
        assert mgr.has("combat")
        assert len(mgr) == 1

    def test_get_returns_registered_system(self):
        mgr = SystemManager()
        system = FullSystem()
        mgr.register("skills", system)
        assert mgr.get("skills") is system

    def test_get_with_system_type_returns_system(self):
        """system_type is a typing aid only; no runtime check is performed."""
        mgr = SystemManager()
        system = FullSystem()
        mgr.register("full", system)
        assert mgr.get("full", dict) is system

    def test_get_missing_returns_default(self):
        mgr = SystemManager()
        sentinel = object()
        assert mgr.get("nope") is None
        assert mgr.get("nope", default=sentinel) is sentinel

    def test_has_missing_system(self):
        mgr = SystemManager()
        assert not mgr.has("nope")

    def test_unregister_removes_and_returns_system(self):
        mgr = SystemManager()
        system = FullSystem()
        mgr.register("tmp", system)
        removed = mgr.unregister("tmp")
        assert removed is system
        assert not mgr.has("tmp")

    def test_unregister_missing_returns_none(self):
        mgr = SystemManager()
        assert mgr.unregister("never-registered") is None

    def test_register_same_name_overwrites(self):
        mgr = SystemManager()
        first, second = FullSystem(), FullSystem()
        mgr.register("dup", first)
        mgr.register("dup", second)
        assert mgr.get("dup") is second
        assert len(mgr) == 1

    def test_initialize_all_passes_engine(self):
        mgr = SystemManager()
        sys_a, sys_b = FullSystem(), NoArgInitSystem()
        mgr.register("a", sys_a)
        mgr.register("b", sys_b)
        engine = object()
        mgr.initialize_all(engine)
        assert sys_a.initialized_with == [engine]
        assert sys_b.calls == ["init"]

    def test_initialize_all_skips_systems_without_initialize(self):
        mgr = SystemManager()
        bare = SimpleNamespace()
        mgr.register("bare", bare)
        mgr.initialize_all(object())  # must not raise

    def test_update_all_full_signature(self):
        mgr = SystemManager()
        system = FullSystem()
        mgr.register("full", system)
        engine = object()
        mgr.update_all(engine, delta_time=0.5)
        assert system.updates == [(engine, 0.5)]

    def test_update_all_engine_only_fallback(self):
        mgr = SystemManager()
        system = EngineOnlyUpdateSystem()
        mgr.register("eo", system)
        engine = object()
        mgr.update_all(engine, delta_time=1.0)
        assert system.updates == [engine]

    def test_update_all_no_arg_fallback(self):
        mgr = SystemManager()
        system = NoArgInitSystem()
        mgr.register("bare", system)
        mgr.update_all(object(), delta_time=1.0)
        assert system.calls == ["update"]

    def test_update_all_skips_systems_without_update(self):
        mgr = SystemManager()
        mgr.register("bare", SimpleNamespace())
        mgr.update_all(object())  # must not raise

    def test_iter_yields_names_in_registration_order(self):
        mgr = SystemManager()
        for name in ("c", "a", "b"):
            mgr.register(name, FullSystem())
        assert list(mgr) == ["c", "a", "b"]


# =============================================================================
# system_coordinator.SystemCoordinator
# =============================================================================


class StubKernel:
    def __init__(self):
        self.systems: dict[str, object] = {}
        self.registered: list[tuple[str, object]] = []

    def register_system(self, name, system):
        self.registered.append((name, system))
        self.systems[name] = system
        return system

    def get_system(self, name):
        return self.systems.get(name)

    def has_system(self, name):
        return name in self.systems


class TestSystemCoordinator:
    def _make_coordinator(self):
        kernel = StubKernel()
        engine = SimpleNamespace(kernel=kernel)
        return SystemCoordinator(engine), kernel, engine

    def test_init_keeps_engine_and_kernel(self):
        coord, kernel, engine = self._make_coordinator()
        assert coord.engine is engine
        assert coord._kernel is kernel
        assert coord._registration_order == []

    def test_register_system_delegates_to_kernel(self):
        coord, kernel, _ = self._make_coordinator()
        system = FullSystem()
        result = coord.register_system("ai", system, dependencies=["pathfinding"])
        assert result is system
        assert kernel.systems["ai"] is system
        assert coord._registration_order == ["ai"]

    def test_register_system_ignores_dependencies_list(self):
        coord, _, _ = self._make_coordinator()
        coord.register_system("s1", FullSystem(), dependencies=["a", "b"])
        coord.register_system("s2", FullSystem())  # no dependencies arg
        assert coord._registration_order == ["s1", "s2"]

    def test_get_system_delegates(self):
        coord, _, _ = self._make_coordinator()
        system = FullSystem()
        coord.register_system("render", system)
        assert coord.get_system("render") is system
        assert coord.get_system("missing") is None

    def test_has_system_delegates(self):
        coord, _, _ = self._make_coordinator()
        coord.register_system("render", FullSystem())
        assert coord.has_system("render")
        assert not coord.has_system("missing")

    def test_initialize_all_and_update_all_are_noops(self):
        coord, kernel, engine = self._make_coordinator()
        coord.initialize_all(engine)
        coord.update_all(engine, 0.5)
        assert kernel.registered == []


# =============================================================================
# managers/combat_manager.CombatManager
# =============================================================================


class KillPlayer:
    def __init__(self, reincarnation_count=0):
        self.exp = 0
        self.exp_awards = []
        self.reincarnation_count = reincarnation_count

    def gain_exp(self, amount):
        self.exp += amount
        self.exp_awards.append(amount)
        return [f"EXP+{amount}"]


class KillQuest:
    def __init__(self, target_monster, target_count, reward_gold, reward_platinum):
        self.target_monster = target_monster
        self.target_count = target_count
        self.current_count = 0
        self.completed = False
        self.reward_gold = reward_gold
        self.reward_platinum = reward_platinum


class KillEntityManager:
    def __init__(self):
        self.added_items = []
        self.removed_entities = []

    def add_item(self, item):
        self.added_items.append(item)

    def remove_entity(self, entity):
        self.removed_entities.append(entity)


class KillEngine:
    def __init__(self, player=None, dungeon_level=1):
        self.dungeon_level = dungeon_level
        self.player = player if player is not None else KillPlayer()
        self.quests = []
        self.survival = SimpleNamespace(gold=0, platinum=0)
        self.entity_manager = KillEntityManager()
        self.logs = []

    def log(self, msg, color=None):
        self.logs.append(msg)


class KillEntity:
    def __init__(self, name="ゴブリン", x=4, y=7):
        self.name = name
        self.x = x
        self.y = y


class TestCombatManager:
    def test_corpse_drop_added_at_entity_position(self):
        engine = KillEngine()
        entity = KillEntity("テストオオカミ", x=4, y=7)

        CombatManager().handle_kill_rewards(engine, entity)

        assert len(engine.entity_manager.added_items) == 1
        corpse = engine.entity_manager.added_items[0]
        assert corpse.name == "テストオオカミの肉"
        assert corpse.category == CAT_FOOD
        assert corpse.x == 4
        assert corpse.y == 7
        assert corpse.nutrition == 2800

    def test_base_exp_without_reincarnation(self):
        engine = KillEngine(dungeon_level=2)
        entity = KillEntity()

        CombatManager().handle_kill_rewards(engine, entity)

        assert engine.player.exp_awards == [35 * 2]
        # gain_exp messages are forwarded to the engine log
        assert "EXP+70" in engine.logs

    def test_reincarnation_one_reduces_exp(self):
        engine = KillEngine(player=KillPlayer(reincarnation_count=1), dungeon_level=1)
        CombatManager().handle_kill_rewards(engine, KillEntity())
        # 35 * (1 - 0.05) = 33.25 -> int 33
        assert engine.player.exp_awards == [33]

    def test_reincarnation_penalty_floors_at_half(self):
        engine = KillEngine(player=KillPlayer(reincarnation_count=20), dungeon_level=1)
        CombatManager().handle_kill_rewards(engine, KillEntity())
        # penalty clamped to REINCARNATION_XP_PENALTY_BASE (0.5): 35 * 0.5 = 17.5 -> 17
        assert engine.player.exp_awards == [17]

    def test_quest_progresses_without_completion(self):
        engine = KillEngine()
        quest = KillQuest("ゴブリン", target_count=3, reward_gold=100, reward_platinum=0)
        engine.quests.append(quest)
        entity = KillEntity("ゴブリン戦士")

        CombatManager().handle_kill_rewards(engine, entity)

        assert quest.current_count == 1
        assert not quest.completed
        assert engine.survival.gold == 0
        assert engine.survival.platinum == 0
        assert engine.entity_manager.removed_entities == []

    def test_quest_completion_grants_rewards_and_removes_entity(self):
        engine = KillEngine()
        quest = KillQuest("ゴブリン", target_count=1, reward_gold=120, reward_platinum=3)
        engine.quests.append(quest)
        entity = KillEntity("ゴブリン")

        with patch("sound_manager.SoundManager.play_se") as mock_play_se:
            CombatManager().handle_kill_rewards(engine, entity)

        assert quest.completed
        assert engine.survival.gold == 120
        assert engine.survival.platinum == 3
        assert engine.entity_manager.removed_entities == [entity]
        assert any("依頼達成" in msg for msg in engine.logs)
        mock_play_se.assert_called_once_with("level_up")

    def test_unrelated_quest_not_progressed(self):
        engine = KillEngine()
        quest = KillQuest("スライム", target_count=2, reward_gold=50, reward_platinum=1)
        engine.quests.append(quest)

        CombatManager().handle_kill_rewards(engine, KillEntity("ゴブリン"))

        assert quest.current_count == 0
        assert not quest.completed

    def test_already_completed_quest_not_reprocessed(self):
        engine = KillEngine()
        quest = KillQuest("ゴブリン", target_count=1, reward_gold=100, reward_platinum=2)
        quest.current_count = 1
        quest.completed = True
        engine.quests.append(quest)
        engine.survival.gold = 100
        engine.survival.platinum = 2

        CombatManager().handle_kill_rewards(engine, KillEntity("ゴブリン"))

        assert quest.current_count == 1
        assert engine.survival.gold == 100
        assert engine.entity_manager.removed_entities == []

    def test_multiple_matching_quests_all_settle(self):
        engine = KillEngine()
        quest_a = KillQuest("ゴブリン", target_count=1, reward_gold=10, reward_platinum=0)
        quest_b = KillQuest("ゴブリン", target_count=2, reward_gold=20, reward_platinum=0)
        engine.quests.extend([quest_a, quest_b])
        entity = KillEntity("ゴブリン")

        CombatManager().handle_kill_rewards(engine, entity)

        assert quest_a.completed
        assert quest_b.current_count == 1
        assert not quest_b.completed
        assert engine.survival.gold == 10
        assert engine.entity_manager.removed_entities == [entity]


# =============================================================================
# managers/skill_reward_manager.SkillRewardManager
# =============================================================================


class SkillPlayer:
    def __init__(self):
        self.skill_points = 0
        self.total_skill_points_earned = 0


class SkillEngine:
    def __init__(self):
        self.player = SkillPlayer()
        self.logs = []

    def log(self, msg, color=None):
        self.logs.append(msg)


class TestSkillRewardManager:
    def test_kill_grants_skill_points_on_drop(self):
        engine = SkillEngine()
        with patch("managers.skill_reward_manager.random.random", return_value=0.1), \
             patch("managers.skill_reward_manager.random.randint", return_value=2):
            SkillRewardManager().grant_kill_skill_points(engine, KillEntity())

        assert engine.player.skill_points == 2
        assert engine.player.total_skill_points_earned == 2
        assert any("2" in msg for msg in engine.logs)

    def test_no_skill_points_below_drop_chance(self):
        engine = SkillEngine()
        with patch("managers.skill_reward_manager.random.random", return_value=0.9):
            SkillRewardManager().grant_kill_skill_points(engine, KillEntity())

        assert engine.player.skill_points == 0
        assert engine.player.total_skill_points_earned == 0
        assert engine.logs == []


# =============================================================================
# managers/world_news_manager.WorldNewsManager
# =============================================================================


def make_news_engine(turns, player=None):
    engine = SimpleNamespace(
        turns=turns,
        player=player,
        skill_tree_manager=MagicMock(),
        logs=[],
    )
    engine.log = lambda msg, color=None: engine.logs.append(msg)
    return engine


def make_news_player(**overrides):
    values = dict(
        total_turns=1,
        job="戦士",
        job_exp=0,
        job_level=1,
        skill_points=0,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class TestWorldNewsManager:
    def test_world_news_generated_on_interval(self):
        engine = make_news_engine(turns=50)
        engine.world_state_manager = MagicMock()

        WorldNewsManager().advance(engine)

        engine.world_state_manager.generate_world_news.assert_called_once_with(engine)

    def test_world_news_not_generated_off_interval(self):
        engine = make_news_engine(turns=51)
        engine.world_state_manager = MagicMock()

        WorldNewsManager().advance(engine)

        engine.world_state_manager.generate_world_news.assert_not_called()

    def test_title_check_when_total_turns_hits_interval(self):
        player = make_news_player(total_turns=9)
        engine = make_news_engine(turns=3, player=player)

        with patch("title_system.MANAGER") as mock_manager:
            WorldNewsManager().advance(engine)

        assert player.total_turns == 10
        mock_manager.check_all_titles.assert_called_once_with(player)

    def test_title_check_skipped_off_interval(self):
        player = make_news_player(total_turns=1)
        engine = make_news_engine(turns=3, player=player)

        with patch("title_system.MANAGER") as mock_manager:
            WorldNewsManager().advance(engine)

        assert player.total_turns == 2
        mock_manager.check_all_titles.assert_not_called()

    def test_player_without_total_turns_is_ignored(self):
        player = SimpleNamespace(job_exp=0, job_level=1, job="無職", skill_points=0)
        engine = make_news_engine(turns=1, player=player)

        WorldNewsManager().advance(engine)  # must not raise

        assert player.job_exp == 1  # job exp still accrues

    def test_job_exp_accumulates_without_level_up(self):
        player = make_news_player(job_exp=50, job_level=1)
        engine = make_news_engine(turns=2, player=player)

        WorldNewsManager().advance(engine)

        assert player.job_exp == 51
        assert player.job_level == 1
        assert engine.logs == []

    def test_job_level_up_at_threshold(self):
        player = make_news_player(job_exp=99, job_level=1)
        engine = make_news_engine(turns=2, player=player)

        WorldNewsManager().advance(engine)

        assert player.job_exp == 0
        assert player.job_level == 2
        assert any("職業" in msg for msg in engine.logs)

    def test_skill_tree_notification_when_skills_available(self):
        player = make_news_player(skill_points=2)
        engine = make_news_engine(turns=20, player=player)
        engine.skill_tree_manager.get_available_skills.return_value = ["fire_bolt"]

        WorldNewsManager().advance(engine)

        engine.skill_tree_manager.get_available_skills.assert_called_once_with(player)
        assert any("スキルポイント" in msg for msg in engine.logs)

    def test_skill_tree_notification_silent_without_skills(self):
        player = make_news_player(skill_points=2)
        engine = make_news_engine(turns=20, player=player)
        engine.skill_tree_manager.get_available_skills.return_value = []

        WorldNewsManager().advance(engine)

        assert engine.logs == []

    def test_guild_quest_reset_log_on_interval(self):
        player = make_news_player(guild_quest_progress={})
        engine = make_news_engine(turns=1000, player=player)

        WorldNewsManager().advance(engine)

        assert any("ギルド" in msg for msg in engine.logs)

    def test_guild_reset_requires_progress_attribute(self):
        player = make_news_player()  # no guild_quest_progress attr
        engine = make_news_engine(turns=1000, player=player)

        WorldNewsManager().advance(engine)

        assert engine.logs == []

    def test_no_player_skips_player_scoped_steps(self):
        engine = make_news_engine(turns=50)
        engine.world_state_manager = MagicMock()

        WorldNewsManager().advance(engine)  # must not raise

        engine.world_state_manager.generate_world_news.assert_called_once()

# =============================================================================
# managers/context_menu_builder.ContextMenuBuilder
# =============================================================================


class CtxItem:
    def __init__(self, display_name, category):
        self.display_name = display_name
        self.category = category


class CtxEntity:
    def __init__(self, name):
        self.name = name


class CtxResourceNode:
    def __init__(self, x, y, node_type="鉱石", depleted=False):
        self.x = x
        self.y = y
        self.node_type = node_type
        self.depleted = depleted


class CtxEntityManager:
    def __init__(self, items=None, nodes=None):
        self._items = items if items is not None else []
        self.resource_nodes = nodes if nodes is not None else []

    def get_items_at(self, x, y):
        return self._items


class CtxGameMap:
    SIZE = 50

    def __init__(self):
        self.tiles = defaultdict(lambda: defaultdict(int))

    def is_in_bounds(self, x, y):
        return 0 <= x < self.SIZE and 0 <= y < self.SIZE


class CtxEngine:
    def __init__(self, items=None, nodes=None):
        self.player = CtxEntity("主人公")
        self.player.x = 3
        self.player.y = 3
        # The real engine always carries a pet entity; without one, `ent == pet`
        # would match every empty tile (None == None).
        self.pet = CtxEntity("シエル")
        self.altar_pos = None
        self.entity_manager = CtxEntityManager(items=items, nodes=nodes)
        self.game_map = CtxGameMap()
        self._neighbors: dict[tuple[int, int], CtxEntity] = {}

    def place_neighbor(self, dx, dy, entity):
        self._neighbors[(self.player.x + dx, self.player.y + dy)] = entity

    def get_entity_at(self, x, y):
        return self._neighbors.get((x, y))


class TestContextMenuBuilder:
    def test_empty_position_yields_no_actions(self):
        engine = CtxEngine()
        actions = ContextMenuBuilder().build_actions(engine)
        assert actions == []

    def test_ground_item_pickup_action(self):
        item = CtxItem("鉄の剣", category="weapon")
        engine = CtxEngine(items=[item])

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].label == "拾う: 鉄の剣"
        assert actions[0].action_key == "pickup"
        assert actions[0].handler_name == "pickup_item"
        assert actions[0].payload is item

    def test_ground_food_gets_pickup_and_eat(self):
        item = CtxItem("パン", category=CAT_FOOD)
        engine = CtxEngine(items=[item])

        actions = ContextMenuBuilder().build_actions(engine)

        assert [a.handler_name for a in actions] == ["pickup_item", "eat_ground"]
        assert actions[1].action_key == "eat"
        assert actions[1].payload is item

    def test_adjacent_npc_gets_talk_action(self):
        npc = CtxEntity("村人")
        engine = CtxEngine()
        engine.place_neighbor(1, 0, npc)

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].label == "話す / 調べる: 村人"
        assert actions[0].action_key == "talk"
        assert actions[0].handler_name == "talk_target"
        assert actions[0].payload is npc

    def test_adjacent_pet_gets_inventory_action(self):
        pet = CtxEntity("シエル")
        engine = CtxEngine()
        engine.pet = pet
        engine.place_neighbor(0, 1, pet)

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].label == "シエルの荷物を見る"
        assert actions[0].action_key == "pet_inv"
        assert actions[0].handler_name == "open_pet_inv"

    def test_player_itself_is_not_a_talk_target(self):
        engine = CtxEngine()
        engine.place_neighbor(-1, 0, engine.player)

        actions = ContextMenuBuilder().build_actions(engine)

        assert actions == []

    def test_altar_offers_pray_and_offer(self):
        engine = CtxEngine()
        engine.altar_pos = (engine.player.x, engine.player.y)

        actions = ContextMenuBuilder().build_actions(engine)

        assert [a.handler_name for a in actions] == ["pray", "offer_altar"]
        assert all(a.payload is None for a in actions)

    def test_adjacent_resource_node_harvestable(self):
        node = CtxResourceNode(3, 4, node_type="木材")
        engine = CtxEngine(nodes=[node])

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].action_key == "harvest"
        assert actions[0].handler_name == "harvest_resource"
        assert actions[0].payload is node
        assert "木材" in actions[0].label

    def test_depleted_resource_node_not_offered(self):
        node = CtxResourceNode(3, 4, depleted=True)
        engine = CtxEngine(nodes=[node])

        assert ContextMenuBuilder().build_actions(engine) == []

    def test_distant_resource_node_not_offered(self):
        node = CtxResourceNode(3, 6)  # manhattan distance 3
        engine = CtxEngine(nodes=[node])

        assert ContextMenuBuilder().build_actions(engine) == []

    def test_only_first_matching_node_offered(self):
        node_a = CtxResourceNode(2, 3, node_type="A")
        node_b = CtxResourceNode(4, 3, node_type="B")
        engine = CtxEngine(nodes=[node_a, node_b])

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].payload is node_a

    def test_adjacent_wall_offers_mining(self):
        engine = CtxEngine()
        engine.game_map.tiles[3][2] = TILE_WALL  # north of the player

        actions = ContextMenuBuilder().build_actions(engine)

        assert len(actions) == 1
        assert actions[0].label == "隣の壁を掘る"
        assert actions[0].action_key == "mine"
        assert actions[0].handler_name == "mine_wall"

    def test_no_wall_no_mining(self):
        engine = CtxEngine()
        engine.game_map.tiles[3][2] = 0

        actions = ContextMenuBuilder().build_actions(engine)

        assert all(a.action_key != "mine" for a in actions)


# =============================================================================
# managers/faction_manager.FactionManager
# =============================================================================


class FactionPlayer:
    def __init__(self, reputation=None):
        if reputation is not None:
            self.faction_reputation = reputation


class FactionEngine:
    def __init__(self, turns, player=None):
        self.turns = turns
        self.player = player if player is not None else FactionPlayer()


class TestFactionManager:
    def test_kill_reputation_increments_from_scratch(self):
        player = FactionPlayer(reputation={})
        engine = FactionEngine(turns=1, player=player)

        FactionManager().update_kill_reputation(engine, KillEntity())

        assert player.faction_reputation == {"kingdom_garde": 1}

    def test_kill_reputation_increments_existing_value(self):
        player = FactionPlayer(reputation={"kingdom_garde": 4})
        engine = FactionEngine(turns=1, player=player)

        FactionManager().update_kill_reputation(engine, KillEntity())

        assert player.faction_reputation["kingdom_garde"] == 5

    def test_kill_reputation_noop_without_attribute(self):
        player = FactionPlayer()  # no faction_reputation attr
        engine = FactionEngine(turns=1, player=player)

        FactionManager().update_kill_reputation(engine, KillEntity())  # must not raise

        assert not hasattr(player, "faction_reputation")

    def test_update_influence_applies_change_per_faction(self):
        engine = FactionEngine(turns=200)  # 200 % FACTION_INFLUENCE_INTERVAL == 0
        engine.faction_war_registry = MagicMock()
        engine.faction_war_registry.all.return_value = ["f1", "f2"]
        engine.faction_war_manager = MagicMock()
        engine.faction_war_manager.calculate_influence_change.return_value = 5

        FactionManager().update_influence(engine)

        assert engine.faction_war_manager.calculate_influence_change.call_count == 2
        engine.faction_war_manager.calculate_influence_change.assert_any_call("f1", engine)
        engine.faction_war_manager.calculate_influence_change.assert_any_call("f2", engine)
        engine.faction_war_manager.apply_influence_effects.assert_any_call("f1", 5)
        engine.faction_war_manager.apply_influence_effects.assert_any_call("f2", 5)

    def test_update_influence_skipped_off_interval(self):
        engine = FactionEngine(turns=201)
        engine.faction_war_registry = MagicMock()
        engine.faction_war_manager = MagicMock()

        FactionManager().update_influence(engine)

        engine.faction_war_registry.all.assert_not_called()
        engine.faction_war_manager.calculate_influence_change.assert_not_called()

    def test_update_influence_noop_without_war_systems(self):
        engine = FactionEngine(turns=200)  # no faction_war_* attributes at all

        FactionManager().update_influence(engine)  # must not raise


# =============================================================================
# event_scheduler.EventScheduler
# =============================================================================


class StubEventRegistry:
    def __init__(self, events=None):
        self._events = {e.name: e for e in (events or [])}

    def all_events(self):
        return self._events


def make_event(name="festival", quarter=None, start_turn=None, end_turn=None,
               announcement_period=0):
    return SimpleNamespace(
        name=name,
        quarter=quarter,
        start_turn=start_turn,
        end_turn=end_turn,
        announcement_period=announcement_period,
    )


class TestEventScheduler:
    def test_no_registry_returns_none(self):
        scheduler = EventScheduler(registry=None)
        assert scheduler.get_current_seasonal_event(100) is None
        assert scheduler.get_announcement_event(100) is None

    def test_quarter_event_active_when_quarter_matches(self):
        event = make_event(quarter=2)
        scheduler = EventScheduler(StubEventRegistry([event]))

        assert scheduler.get_current_seasonal_event(100) is event  # turn 100 -> quarter 2
        assert scheduler.get_current_seasonal_event(100, current_quarter=1) is None

    def test_quarter_derivation_from_turn(self):
        q1 = make_event(name="spring", quarter=1)
        q4 = make_event(name="winter", quarter=4)
        registry = StubEventRegistry([q1, q4])
        scheduler = EventScheduler(registry)

        assert scheduler.get_current_seasonal_event(0) is q1  # (0//90 % 4)+1 == 1
        assert scheduler.get_current_seasonal_event(300) is q4  # (300//90 % 4)+1 == 4

    def test_scheduled_turn_window(self):
        event = make_event(start_turn=95, end_turn=105)
        scheduler = EventScheduler(StubEventRegistry([event]))

        assert scheduler.get_current_seasonal_event(95) is event
        assert scheduler.get_current_seasonal_event(100) is event
        assert scheduler.get_current_seasonal_event(105) is event
        assert scheduler.get_current_seasonal_event(94) is None
        assert scheduler.get_current_seasonal_event(106) is None

    def test_scheduled_window_takes_priority_over_quarter(self):
        event = make_event(quarter=4, start_turn=95, end_turn=105)
        scheduler = EventScheduler(StubEventRegistry([event]))

        # Turn 100 resolves to quarter 2, but the scheduled window wins.
        assert scheduler.get_current_seasonal_event(100) is event

    def test_no_events_returns_none(self):
        scheduler = EventScheduler(StubEventRegistry([]))
        assert scheduler.get_current_seasonal_event(100) is None
        assert scheduler.get_announcement_event(100) is None

    def test_announcement_for_scheduled_event(self):
        event = make_event(start_turn=100, end_turn=200, announcement_period=10)
        scheduler = EventScheduler(StubEventRegistry([event]))

        assert scheduler.get_announcement_event(90) is event
        assert scheduler.get_announcement_event(99) is event
        assert scheduler.get_announcement_event(89) is None
        assert scheduler.get_announcement_event(100) is None  # event itself started

    def test_announcement_for_quarter_event(self):
        event = make_event(quarter=2, announcement_period=10)
        scheduler = EventScheduler(StubEventRegistry([event]))

        # Quarter 2 starts at turn 90; with quarter=2 explicit the announcement
        # window is [80, 90). The derived quarter at turn 85 would still be 1,
        # so an explicit current_quarter is required to see the announcement.
        assert scheduler.get_announcement_event(80, current_quarter=2) is event
        assert scheduler.get_announcement_event(85, current_quarter=2) is event
        assert scheduler.get_announcement_event(75, current_quarter=2) is None
        assert scheduler.get_announcement_event(90, current_quarter=2) is None

    def test_zero_announcement_period_never_announces(self):
        event = make_event(quarter=2, announcement_period=0)
        scheduler = EventScheduler(StubEventRegistry([event]))

        assert scheduler.get_announcement_event(85) is None

    def test_async_wrappers_delegate(self):
        event = make_event(quarter=2, start_turn=100, end_turn=200, announcement_period=10)
        scheduler = EventScheduler(StubEventRegistry([event]))

        assert asyncio.run(scheduler.async_get_current_seasonal_event(150)) is event
        assert asyncio.run(scheduler.async_get_announcement_event(95)) is event

# =============================================================================
# karma_system
# =============================================================================


class KarmaPlayer:
    def __init__(self, law_chaos=0, good_evil=0, exposure=None):
        self.karma_law_chaos = law_chaos
        self.karma_good_evil = good_evil
        if exposure is not None:
            self.template_exposure = exposure


class NullRegistry:
    """Stub registry whose get() never returns data (triggers fallback path)."""

    def get(self, karma_id="default"):
        return None


class TestKarmaSystem:
    @pytest.fixture(autouse=True)
    def _fresh_default_registry(self):
        REGISTRY.load()
        yield
        REGISTRY.load()

    def test_load_registers_default_karma(self):
        REGISTRY.load()

        data = REGISTRY.get("default")
        assert isinstance(data, KarmaData)
        assert data.id == "default"
        assert "help_innocent" in data.actions
        assert data.actions["help_innocent"] == {"law_chaos": 5, "good_evil": 10}
        assert "steal" in data.actions
        assert data.reincarnation_effects == {"stat_bonus": 5}

    def test_load_reads_project_yaml_alignment(self):
        REGISTRY.load("data/karma.yaml")

        ranges = REGISTRY.get("default").alignment_ranges
        assert ranges["law_chaos"]["range"] == [-100, 100]
        assert "good_evil" in ranges
        # data/karma.yaml has no exposure section, so it is absent after load
        assert "exposure" not in ranges

    def test_get_defaults_to_default_id(self):
        REGISTRY.load()
        assert REGISTRY.get(None) is REGISTRY.get("default")
        assert REGISTRY.all() == {"default": REGISTRY.get("default")}

    def test_load_custom_path_merges_over_defaults(self, tmp_path):
        custom = tmp_path / "karma_custom.yaml"
        custom.write_text(
            "karma:\n"
            "  alignment:\n"
            "    law_chaos:\n"
            "      range: [-50, 50]\n"
            "      neutral: 0\n"
            "  actions:\n"
            "    custom_act:\n"
            "      law_chaos: 7\n"
            "      good_evil: -7\n"
            "      exposure: 4\n",
            encoding="utf-8",
        )

        REGISTRY.load(str(custom))
        data = REGISTRY.get("default")

        assert data.alignment_ranges["law_chaos"]["range"] == [-50, 50]
        assert data.alignment_ranges["law_chaos"]["neutral"] == 0
        assert data.actions["custom_act"] == {"law_chaos": 7, "good_evil": -7, "exposure": 4}
        assert "help_innocent" in data.actions  # built-in actions survive the merge

    def test_load_missing_file_keeps_defaults(self, tmp_path):
        REGISTRY.load(str(tmp_path / "does_not_exist.yaml"))

        data = REGISTRY.get("default")
        assert data.actions["help_innocent"] == {"law_chaos": 5, "good_evil": 10}
        assert data.alignment_ranges["exposure"]["range"] == [0, 100]

    def test_registry_is_singleton(self):
        assert KarmaRegistry() is REGISTRY

    def test_update_karma_positive_action(self):
        player = KarmaPlayer()
        result = KarmaManager().update_karma(player, "help_innocent")

        assert result == (5, 10, 0)
        assert player.karma_law_chaos == 5
        assert player.karma_good_evil == 10
        assert player.template_exposure == 0

    def test_update_karma_negative_action_with_amount(self):
        player = KarmaPlayer(law_chaos=10, good_evil=10)

        result = KarmaManager().update_karma(player, "steal", amount=3)

        assert result == (10 - 3, 10 - 6, 0)

    def test_update_karma_unknown_action_is_neutral(self):
        player = KarmaPlayer(law_chaos=3, good_evil=4)

        result = KarmaManager().update_karma(player, "nonexistent_action")

        assert result == (3, 4, 0)

    def test_update_karma_clamps_to_upper_bound(self):
        player = KarmaPlayer(law_chaos=98, good_evil=99)

        law, good, _ = KarmaManager().update_karma(player, "donate_to_temple")

        assert law == 99  # 98 + 1
        assert good == 100  # 99 + 2, clamped

    def test_update_karma_clamps_to_lower_bound(self):
        player = KarmaPlayer(law_chaos=-100, good_evil=0)

        law, good, _ = KarmaManager().update_karma(player, "murder_innocent", amount=10)

        assert law == -100  # -100 + (-20) clamped
        assert good == -50

    def test_update_karma_exposure_accumulates(self):
        player = KarmaPlayer()  # no template_exposure attr yet

        law, good, exposure = KarmaManager().update_karma(player, "template_deep_read")

        assert (law, good, exposure) == (-1, 0, 1)
        assert player.template_exposure == 1

        _, _, exposure = KarmaManager().update_karma(player, "template_intervene_t2")
        assert exposure == 4  # 1 + 3

    def test_update_karma_exposure_clamped(self):
        player = KarmaPlayer(exposure=99)

        _, _, exposure = KarmaManager().update_karma(player, "template_intervene_t3")

        assert exposure == 100  # 99 + 10 clamped

    def test_get_karma_bonuses(self):
        assert KarmaManager().get_karma_bonuses(KarmaPlayer()) == {"stat_bonus": 5}

    def test_manager_with_empty_registry_returns_untouched_values(self):
        player = KarmaPlayer(law_chaos=7, good_evil=-3)

        result = KarmaManager(registry=NullRegistry()).update_karma(player, "steal", amount=5)

        assert result == (7, -3, 0)
        assert player.karma_law_chaos == 7
        assert player.karma_good_evil == -3
        assert not hasattr(player, "template_exposure")


# =============================================================================
# god_system.GodInfo
# =============================================================================


class TestGodSystem:
    def test_get_all_loads_project_gods_yaml(self):
        gods = GodInfo.get_all()

        assert set(gods) == {"eyth", "jure", "lulwy", "mani", "itzpalt", "kumiromi"}
        for god in gods.values():
            assert isinstance(god, dict)
            assert isinstance(god["name"], str)
            assert isinstance(god["domain"], str)
            assert isinstance(god["favored_offer"], list)

    def test_lulwy_offering_data(self):
        lulwy = GodInfo.get_all()["lulwy"]

        assert lulwy["name"] == "風のルルウィ"
        assert "bow" in lulwy["favored_offer"]
        assert "corpse" in lulwy["favored_offer"]

    def test_gods_dict_item_access(self):
        jure = GodInfo.GODS["jure"]
        assert jure["domain"] == "治癒・愛・鉱石"
        assert GodInfo.GODS["missing_god_key"] is None

    def test_gods_dict_get_with_default(self):
        assert GodInfo.GODS.get("lulwy") is not None
        assert GodInfo.GODS.get("missing_god_key") is None
        assert GodInfo.GODS.get("missing_god_key", "fallback") == "fallback"

    def test_gods_dict_contains(self):
        assert "eyth" in GodInfo.GODS
        assert "missing_god_key" not in GodInfo.GODS

    def test_gods_dict_keys_values_items_agree(self):
        gods = GodInfo.get_all()
        assert list(GodInfo.GODS.keys()) == list(gods.keys())
        assert len(list(GodInfo.GODS.values())) == len(gods)
        assert dict(GodInfo.GODS.items()) == gods

    def test_fallback_gods_cached(self):
        first = GodInfo.get_fallback_gods()
        second = GodInfo.get_fallback_gods()

        assert first is second
        assert len(first) > 0
        assert "eyth" in first

    def test_get_all_falls_back_when_yaml_missing(self):
        with patch("data_validation.load_yaml_validated",
                   side_effect=FileNotFoundError("no gods.yaml")):
            gods = GodInfo.get_all()

        fallback = GodInfo.get_fallback_gods()
        assert set(gods) == set(fallback)


# =============================================================================
# scaling
# =============================================================================


class TestScaling:
    def test_scale_horizontal(self, capsys):
        assert scaling.scale_horizontal(replicas=5) is True
        out = capsys.readouterr().out
        assert "Target replicas: 5" in out

    def test_scale_vertical_with_resources(self, capsys):
        assert scaling.scale_vertical(resources="cpu=4,memory=8Gi") is True
        assert "Target resources: cpu=4,memory=8Gi" in capsys.readouterr().out

    def test_scale_vertical_without_resources(self, capsys):
        assert scaling.scale_vertical() is True
        assert "Increasing CPU/Memory allocation" in capsys.readouterr().out

    def test_auto_scale(self, capsys):
        assert scaling.auto_scale(min_replicas=2, max_replicas=9, target_cpu=60) is True
        out = capsys.readouterr().out
        assert "Min replicas: 2" in out
        assert "Max replicas: 9" in out
        assert "Target CPU: 60%" in out

    def test_scale_database(self, capsys):
        assert scaling.scale_database(read_replicas=4) is True
        assert "4 read replicas" in capsys.readouterr().out

    def test_scale_cache(self, capsys):
        assert scaling.scale_cache(nodes=7) is True
        assert "7 nodes" in capsys.readouterr().out

    def test_get_scale_status_returns_structured_status(self, capsys):
        status = scaling.get_scale_status()

        assert set(status) == {"horizontal", "vertical", "database", "cache"}
        assert status["horizontal"]["desired"] == 3
        assert status["cache"]["nodes"] == 3
        assert '"cache"' in capsys.readouterr().out  # printed as JSON

    def test_run_command_splits_string_and_reports_success(self, capsys):
        with patch("scaling.subprocess.run") as mock_run:
            mock_run.return_value = SimpleNamespace(
                returncode=0, stdout="command output", stderr=""
            )
            ok = scaling.run_command("kubectl get pods")

        assert ok is True
        mock_run.assert_called_once_with(["kubectl", "get", "pods"], cwd=None,
                                         capture_output=True, text=True)
        captured = capsys.readouterr()
        assert "Running: kubectl get pods" in captured.out
        assert "command output" in captured.out

    def test_run_command_accepts_list_and_reports_failure(self):
        with patch("scaling.subprocess.run") as mock_run:
            mock_run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="boom")
            ok = scaling.run_command(["false"])

        assert ok is False
        mock_run.assert_called_once_with(["false"], cwd=None,
                                         capture_output=True, text=True)


# =============================================================================
# job_queue.JobQueue
# =============================================================================


class TestJobQueue:
    def test_new_queue_is_empty(self):
        queue = JobQueue()
        assert len(queue) == 0

    def test_run_next_executes_job_and_returns_result(self):
        queue = JobQueue()
        queue.add_job(lambda: 42)
        assert queue.run_next() == 42
        assert len(queue) == 0

    def test_run_next_empty_raises_index_error(self):
        queue = JobQueue()
        with pytest.raises(IndexError):
            queue.run_next()

    def test_lower_priority_runs_first(self):
        queue = JobQueue()
        order = []
        queue.add_job(lambda: order.append("low-priority"), priority=20)
        queue.add_job(lambda: order.append("high-priority"), priority=1)

        queue.run_next()
        queue.run_next()

        assert order == ["high-priority", "low-priority"]

    def test_same_priority_preserves_insertion_order(self):
        queue = JobQueue()
        order = []
        for tag in ("first", "second", "third"):
            queue.add_job(lambda tag=tag: order.append(tag), priority=10)

        while len(queue):
            queue.run_next()

        assert order == ["first", "second", "third"]

    def test_args_and_kwargs_forwarded(self):
        queue = JobQueue()
        queue.add_job(lambda a, b, *, c: (a, b, c), args=(1, 2), kwargs={"c": 3})
        assert queue.run_next() == (1, 2, 3)

    def test_default_priority_is_ten(self):
        queue = JobQueue()
        order = []
        queue.add_job(lambda: order.append("default"))  # priority 10
        queue.add_job(lambda: order.append("urgent"), priority=5)

        queue.run_next()
        queue.run_next()

        assert order == ["urgent", "default"]

    def test_len_tracks_pending_jobs(self):
        queue = JobQueue()
        queue.add_job(lambda: None)
        queue.add_job(lambda: None)
        assert len(queue) == 2
        queue.run_next()
        assert len(queue) == 1
        queue.run_next()
        assert len(queue) == 0
