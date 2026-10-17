"""Core systems test suite.

Covers the systems that existing tests leave thin:
- systems.py: StatusEffect / ResistanceSet / AggroList / Quest / spell data /
  unified cast() / SurvivalSystem eat-drink / MonsterPreset
  (CombatSystem, resolve_action, aimed_tile, SurvivalSystem.turn flow は
  tests/test_ap_system.py, tests/test_survival_balance.py 等が既に担保)
- save_system.py: pickle save/load, backup rotation, corruption recovery,
  JSON serialize/deserialize, clear_run
- data_manager.py: YAML cache, localization, item/monster generation
  (repository queries are covered by tests/test_repositories.py)
- achievement_system.py: condition types / rewards (tests/test_achievements.py
  covers run-end wiring with the shipped YAML)
- title_system.py: conditions, grant, equip/unequip effects
- seasonal_systems.py: announcer / feedback / analytics / resource manager
"""

from __future__ import annotations

import json
import os
import random
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pathlib import Path

_REPO = Path(_ROOT)

import pytest
import yaml
from naRou.engine.game_state import GameStateMachine

import systems
from achievement_system import REGISTRY, AchievementData, AchievementManager, AchievementRegistry
from constants import (
    KITER_PREFERRED_RANGE,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
    Element,
)
from data_manager import _YAML_CACHE, DataManager, _cached_load_yaml, clear_yaml_cache
from ecs.entity import Entity, Skill
from item_system import Item
from run_history import RunHistory
from save_system import SaveSystem
from seasonal_systems import (
    EventAction,
    EventAnalyticsManager,
    EventAnnouncer,
    EventFeedbackManager,
    EventResourceManager,
)
from title_system import (
    MANAGER as TITLE_MANAGER,
)
from title_system import (
    REGISTRY as TITLE_REGISTRY,
)
from title_system import (
    TitleCondition,
    TitleData,
    TitleEffect,
    TitleManager,
    TitleRegistry,
)

# ============================================================
# helpers
# ============================================================


def _caster(hp=100, max_hp=100, mp=50, magic=10, x=5, y=5, speed=100):
    """Minimal spell-caster stand-in with the attributes cast() touches."""
    return SimpleNamespace(
        name="詠唱者",
        hp=hp,
        max_hp=max_hp,
        mp=mp,
        x=x,
        y=y,
        skills={},
        attributes=SimpleNamespace(magic=magic),
        status_effects=[],
        speed=speed,
    )


def _victim(x=10, y=10, hp=100):
    return SimpleNamespace(name="スライム", hp=hp, max_hp=100, x=x, y=y)


def _ap_actor(ap=10, max_ap=10):
    a = SimpleNamespace(
        ap=ap,
        max_ap=max_ap,
        name="俳優",
        hp=10,
        mp=10,
        x=1,
        y=1,
        skills={},
        attributes=SimpleNamespace(magic=10),
        status_effects=[],
    )

    def can_act(cost):
        return a.ap >= cost

    def spend_ap(cost):
        a.ap -= cost

    a.can_act = can_act
    a.spend_ap = spend_ap
    return a


def _player(**overrides) -> Entity:
    p = Entity(0, 0, "@", name="テスト冒険者", is_player=True)
    for key, value in overrides.items():
        setattr(p, key, value)
    return p


def _title_player(**overrides) -> Entity:
    """Player whose recalculate_stats() does not restore base attributes,
    so title effect application is observable."""
    p = _player(**overrides)
    p._base_attributes = None
    return p


@pytest.fixture
def restored_randint():
    """Guard against accidental global randint leakage between tests."""
    original = random.randint
    yield
    random.randint = original


# ============================================================
# systems.py — StatusEffect / ResistanceSet / AggroList / Quest
# ============================================================


class TestStatusEffect:
    def test_defaults(self):
        eff = systems.StatusEffect("毒", 12)
        assert eff.name == "毒"
        assert eff.remaining_ticks == 12
        assert eff.power == 1
        assert eff.source is None

    def test_full_construction(self):
        eff = systems.StatusEffect("出血", 5, power=3, source="trap")
        assert (eff.name, eff.remaining_ticks, eff.power, eff.source) == ("出血", 5, 3, "trap")

    def test_remaining_ticks_decrementable(self):
        eff = systems.StatusEffect("麻痺", 7)
        eff.remaining_ticks -= 3
        assert eff.remaining_ticks == 4


class TestResistanceSet:
    def test_all_elements_default_zero(self):
        rs = systems.ResistanceSet()
        for element in (Element.FIRE, Element.COLD, Element.LIGHTNING, Element.DARKNESS, Element.CHAOS, Element.MAGIC):
            assert rs.get(element) == 0

    def test_unknown_element_maps_to_zero(self):
        rs = systems.ResistanceSet()
        assert rs.get("not-an-element") == 0

    def test_set_values_are_reflected(self):
        rs = systems.ResistanceSet()
        rs.fire = 100
        rs.cold = -50
        rs.chaos = 25
        assert rs.get(Element.FIRE) == 100
        assert rs.get(Element.COLD) == -50
        assert rs.get(Element.CHAOS) == 25
        assert rs.get(Element.MAGIC) == 0

    def test_attributes_are_independent(self):
        rs = systems.ResistanceSet()
        rs.lightning = 10
        assert rs.fire == 0
        assert rs.darkness == 0


class TestAggroList:
    def test_empty_table_has_no_target(self):
        assert systems.AggroList().top_target() is None

    def test_single_entry_wins(self):
        aggro = systems.AggroList()
        aggro.add_hate("goblin", 5)
        assert aggro.top_target() == "goblin"

    def test_hate_accumulates(self):
        aggro = systems.AggroList()
        aggro.add_hate("orc", 3)
        aggro.add_hate("orc", 4)
        aggro.add_hate("slime", 6)
        assert aggro.top_target() == "orc"

    def test_tie_keeps_first_inserted(self):
        aggro = systems.AggroList()
        aggro.add_hate("first", 5)
        aggro.add_hate("second", 5)
        assert aggro.top_target() == "first"

    def test_leading_target_can_be_overtaken(self):
        aggro = systems.AggroList()
        aggro.add_hate("first", 5)
        aggro.add_hate("second", 6)
        assert aggro.top_target() == "second"


class TestQuest:
    def test_defaults(self):
        q = systems.Quest(title="討伐", target_monster="slime", target_count=5)
        assert q.current_count == 0
        assert q.reward_gold == 200
        assert q.reward_platinum == 2
        assert q.completed is False

    def test_custom_values(self):
        q = systems.Quest(
            title="収集", target_monster="bat", target_count=3,
            reward_gold=500, reward_platinum=0, completed=True,
        )
        assert q.reward_gold == 500
        assert q.reward_platinum == 0
        assert q.completed is True

    def test_progression_state_transition(self):
        q = systems.Quest(title="討伐", target_monster="orc", target_count=2)
        q.current_count += 1
        assert not q.completed
        q.current_count += 1
        q.completed = True
        assert q.current_count == 2 and q.completed


# ============================================================
# systems.py — spell data loading & unified cast()
# ============================================================


class TestSpellData:
    def test_load_spell_data_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert systems.load_spell_data() == {}

    def test_load_spell_data_invalid_yaml_returns_empty(self, tmp_path, monkeypatch):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "spells.yaml").write_text("a: [unclosed", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert systems.load_spell_data() == {}

    def test_get_spell_ids_reads_real_data(self):
        ids = systems.get_spell_ids()
        assert "fireball" in ids
        assert "heal_light" in ids

    def test_get_spell_data_is_cached(self, monkeypatch):
        monkeypatch.setattr(systems, "_SPELL_DATA_CACHE", None)
        first = systems.get_spell_data()
        second = systems.get_spell_data()
        assert first is second
        assert "fireball" in first

    def test_cast_unknown_spell(self):
        ok, msg = systems.cast("no_such_spell_xyz", _caster())
        assert ok is False
        assert "未知の呪文" in msg

    def test_cast_insufficient_mp_leaves_mp_untouched(self):
        caster = _caster(mp=1)
        ok, msg = systems.cast("fireball", caster)
        assert ok is False
        assert caster.mp == 1
        assert "MP" in msg

    def test_cast_heal_light_self_target(self, restored_randint):
        random.randint = lambda a, b: a  # always minimal roll => success path
        caster = _caster(hp=50, mp=50)
        ok, msg = systems.cast("heal_light", caster)
        assert ok is True
        assert caster.mp == 50 - 6  # heal_light mp_cost
        assert caster.hp == 50 + (2 * 1 + 10)  # 2d1 + dmg_bonus(10)
        assert "癒えた" in msg

    def test_cast_heal_clamps_to_max_hp(self, restored_randint):
        # success roll (b == 100) must land low, heal dice roll at maximum
        random.randint = lambda a, b: a if b >= 100 else b
        caster = _caster(hp=95, mp=50)
        systems.cast("heal_heavy", caster)  # 4d12 + 30 would overheal
        assert caster.hp == caster.max_hp

    def test_cast_failure_applies_backlash(self, restored_randint):
        random.randint = lambda a, b: b  # roll 100 > success_rate => fail
        caster = _caster(hp=100, mp=50, magic=10)
        ok, msg = systems.cast("fireball", caster)
        assert ok is False
        # MP is consumed even on failure
        assert caster.mp == 50 - 12
        # backlash = randint(3, 10 + magic) -> returns upper bound 20
        assert caster.hp == 100 - 20
        assert "詠唱失敗" in msg

    def _with_custom_spells(self, monkeypatch, spells):
        monkeypatch.setattr(systems, "_SPELL_DATA_CACHE", spells)

    def test_cast_single_target_attack(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "test_bolt": {
                "name": "テストボルト", "mp_cost": 2, "element": "fire",
                "target_type": "single", "dice_num": 1, "dice_side": 6,
                "dmg_bonus": 0,
            }
        })
        random.randint = lambda a, b: a
        caster, target = _caster(magic=10), _victim(hp=100)
        ok, msg = systems.cast("test_bolt", caster, target)
        assert ok is True
        # dmg = 1d1 + int(magic/2) = 1 + 5 = 6, no resistance attr => full damage
        assert target.hp == 100 - 6
        assert caster.mp == 48
        assert "6ダメージ" in msg

    def test_cast_single_target_attack_clamps_hp_at_zero(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "nuke": {
                "name": "核", "mp_cost": 1, "element": "fire",
                "target_type": "single", "dice_num": 1, "dice_side": 6,
                "dmg_bonus": 0,
            }
        })
        random.randint = lambda a, b: a if b >= 100 else b  # succeed roll, max dice
        caster, target = _caster(magic=99), _victim(hp=3)
        ok, _ = systems.cast("nuke", caster, target)
        assert ok is True
        assert target.hp == 0

    def test_beam_spell_hits_target_on_the_line(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "test_beam": {
                "name": "テストビーム", "mp_cost": 4, "element": "fire",
                "target_type": "beam", "range": 5, "dice_num": 1,
                "dice_side": 6, "dmg_bonus": 0,
            }
        })
        random.randint = lambda a, b: a
        caster = _caster(x=10, y=10, magic=10)
        target = _victim(x=13, y=10, hp=100)  # 3 tiles east
        ok, msg = systems.cast("test_beam", caster, target)
        assert ok is True
        assert target.hp == 100 - 6
        assert "貫いた" in msg

    def test_beam_spell_same_position_fails(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "test_beam": {
                "name": "テストビーム", "mp_cost": 4, "element": "fire",
                "target_type": "beam", "range": 5,
            }
        })
        random.randint = lambda a, b: a
        caster = _caster(x=7, y=7)
        ok, msg = systems.cast("test_beam", caster, _victim(x=7, y=7))
        assert ok is False
        assert "同じ位置" in msg

    def test_area_spell_damages_everyone_in_radius(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "test_burst": {
                "name": "テスト爆発", "mp_cost": 5, "element": "fire",
                "target_type": "area", "radius": 1, "dice_num": 1,
                "dice_side": 6, "dmg_bonus": 0,
            }
        })
        random.randint = lambda a, b: a
        caster = _caster(x=10, y=10, magic=10)
        near = _victim(x=12, y=10, hp=100)   # distance 0 from center
        edge = _victim(x=13, y=10, hp=100)   # distance 1 from center
        far = _victim(x=20, y=10, hp=100)    # outside radius
        engine = SimpleNamespace(
            entity_manager=SimpleNamespace(
                get_living_entities=lambda: [caster, near, edge, far]
            )
        )
        ok, msg = systems.cast("test_burst", caster, _victim(x=12, y=10), engine=engine)
        assert ok is True
        assert near.hp == 94
        assert edge.hp == 94
        assert far.hp == 100
        assert near.name in msg

    def test_area_spell_without_engine_fails(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "test_burst": {
                "name": "テスト爆発", "target_type": "area", "radius": 1,
            }
        })
        random.randint = lambda a, b: a  # guarantee the cast roll succeeds
        ok, msg = systems.cast("test_burst", _caster(), _victim())
        assert ok is False
        assert "Engine" in msg

    def test_haste_self_buff(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "haste": {"name": "ヘイスト", "mp_cost": 5, "duration": 30, "target_type": "self"}
        })
        random.randint = lambda a, b: a
        caster = _caster(speed=100, mp=50)
        ok, msg = systems.cast("haste", caster)
        assert ok is True
        assert caster.mp == 45
        assert caster.speed == 150
        assert len(caster.status_effects) == 1
        buff = caster.status_effects[0]
        assert buff.name == "Haste"
        assert buff.remaining_ticks == 300  # duration * 10
        assert buff.power == 2

    def test_haste_replaces_existing_buff(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "haste": {"name": "ヘイスト", "mp_cost": 5, "duration": 30, "target_type": "self"}
        })
        random.randint = lambda a, b: a
        caster = _caster(speed=100)
        caster.status_effects = [systems.StatusEffect("Haste", 10, power=1)]
        systems.cast("haste", caster)
        assert len(caster.status_effects) == 1
        assert caster.status_effects[0].remaining_ticks == 300

    def test_teleport_moves_to_free_tile(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "teleport": {"name": "テレポート", "mp_cost": 8, "target_type": "self"}
        })
        random.randint = lambda a, b: a  # candidate tile is always (0, 0)
        caster = _caster(x=5, y=5)
        engine = SimpleNamespace(
            is_tile_free=lambda x, y: True,
            get_entity_at=lambda x, y: None,
        )
        ok, msg = systems.cast("teleport", caster, engine=engine)
        assert ok is True
        assert (caster.x, caster.y) == (0, 0)
        assert "テレポート" in msg

    def test_teleport_never_lands_on_current_tile(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "teleport": {"name": "テレポート", "mp_cost": 8, "target_type": "self"}
        })
        random.randint = lambda a, b: a  # only candidate is (0, 0)
        caster = _caster(x=0, y=0)
        engine = SimpleNamespace(
            is_tile_free=lambda x, y: True,
            get_entity_at=lambda x, y: None,
        )
        ok, msg = systems.cast("teleport", caster, engine=engine)
        assert ok is False
        assert "安全な場所が見つからない" in msg
        assert (caster.x, caster.y) == (0, 0)

    def test_teleport_blocked_tiles_fail(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "teleport": {"name": "テレポート", "mp_cost": 8, "target_type": "self"}
        })
        random.randint = lambda a, b: a
        caster = _caster(x=5, y=5)
        engine = SimpleNamespace(is_tile_free=lambda x, y: False)
        ok, _ = systems.cast("teleport", caster, engine=engine)
        assert ok is False
        assert (caster.x, caster.y) == (5, 5)

    def test_unimplemented_self_spell(self, monkeypatch, restored_randint):
        self._with_custom_spells(monkeypatch, {
            "future_spell": {"name": "未来", "target_type": "self"}
        })
        random.randint = lambda a, b: a  # guarantee the cast roll succeeds
        ok, msg = systems.cast("future_spell", _caster())
        assert ok is False
        assert "未実装" in msg


# ============================================================
# systems.py — resolve_action AP paths not covered elsewhere
# ============================================================


class TestResolveActionItemAndSkill:
    def test_item_action_is_unimplemented(self):
        actor = _ap_actor(ap=10)
        ok, msg = systems.resolve_action(actor, "item")
        assert ok is False
        assert "未実装" in msg
        assert actor.ap == 9  # AP still spent on the attempt

    def test_skill_action_is_unimplemented(self):
        actor = _ap_actor(ap=10)
        ok, msg = systems.resolve_action(actor, "skill")
        assert ok is False
        assert "未実装" in msg

    def test_move_without_engine_fails(self):
        actor = _ap_actor(ap=10)
        ok, msg = systems.resolve_action(actor, "move", dx=1, dy=0)
        assert ok is False
        assert "エンジン" in msg
        assert (actor.x, actor.y) == (1, 1)

    def test_move_on_blocked_tile_keeps_position(self):
        actor = _ap_actor(ap=10)
        engine = SimpleNamespace(is_tile_free=lambda x, y: False)
        ok, msg = systems.resolve_action(actor, "move", engine=engine, dx=1, dy=0)
        assert ok is False
        assert "進めない" in msg
        assert (actor.x, actor.y) == (1, 1)
        assert actor.ap == 9


# ============================================================
# systems.py — SurvivalSystem: eat / drink / regen edge paths
# ============================================================


class TestSurvivalSystemExtras:
    def test_initial_state(self):
        s = systems.SurvivalSystem()
        assert (s.hunger, s.thirst, s.fatigue, s.karma, s.gold, s.platinum, s.fame, s.turns) == (
            8000, 0, 0, 0, 0, 0, 0, 0
        )

    def test_hunger_decays_each_turn(self):
        s = systems.SurvivalSystem()
        s.pass_turn(_player())
        assert s.hunger == 7999
        assert s.turns == 1

    def test_eat_with_int_restores_hunger(self):
        s = systems.SurvivalSystem()
        s.hunger = 5000
        msg = s.eat(None, 300)
        assert s.hunger == 5300
        assert "食料" in msg

    def test_eat_with_food_object_uses_nutrition(self):
        s = systems.SurvivalSystem()
        s.hunger = 5000
        food = SimpleNamespace(name="パン", nutrition=250)
        msg = s.eat(None, food)
        assert s.hunger == 5250
        assert "パン" in msg

    def test_eat_caps_hunger_at_10000(self):
        s = systems.SurvivalSystem()
        s.hunger = 9990
        s.eat(None, 500)
        assert s.hunger == 10000

    def test_drink_with_int_reduces_thirst(self):
        s = systems.SurvivalSystem()
        s.thirst = 50
        s.drink(None, 30)
        assert s.thirst == 20

    def test_drink_with_object_uses_nutrition(self):
        s = systems.SurvivalSystem()
        s.thirst = 40
        s.drink(None, SimpleNamespace(name="水筒", nutrition=15))
        assert s.thirst == 25

    def test_drink_thirst_floors_at_zero(self):
        s = systems.SurvivalSystem()
        s.thirst = 5
        s.drink(None, 999)
        assert s.thirst == 0

    def test_tick_is_alias_for_pass_turn(self):
        s = systems.SurvivalSystem()
        logs = s.tick(_player())
        assert s.turns == 1
        assert s.hunger == 7999
        assert logs == []

    def test_natural_regen_on_tenth_turn(self):
        s = systems.SurvivalSystem()
        s.turns = 9
        entity = SimpleNamespace(hp=10, max_hp=20, mp=5, max_mp=10, status_effects=[])
        logs = s.pass_turn(entity, engine=object())
        assert s.turns == 10
        assert entity.hp == 11
        assert entity.mp == 6
        assert any("自然回復" in line for line in logs)

    def test_regen_clamps_at_max(self):
        s = systems.SurvivalSystem()
        s.turns = 9
        entity = SimpleNamespace(hp=20, max_hp=20, mp=10, max_mp=10, status_effects=[])
        s.pass_turn(entity, engine=object())
        assert entity.hp == 20 and entity.mp == 10

    def test_bleeding_blocks_natural_regen(self):
        s = systems.SurvivalSystem()
        s.turns = 9
        entity = SimpleNamespace(
            hp=10, max_hp=20, mp=5, max_mp=10,
            status_effects=[SimpleNamespace(effect_type="bleeding")],
        )
        logs = s.pass_turn(entity, engine=object())
        assert entity.hp == 10 and entity.mp == 5
        assert logs == []

    def test_regen_requires_engine(self):
        s = systems.SurvivalSystem()
        s.turns = 9
        entity = SimpleNamespace(hp=10, max_hp=20, mp=5, max_mp=10, status_effects=[])
        s.pass_turn(entity, engine=None)
        assert entity.hp == 10

    def test_regen_blocked_below_hunger_threshold(self):
        s = systems.SurvivalSystem()
        s.turns = 9
        s.hunger = 1000  # threshold is 1000; regen requires strictly greater
        entity = SimpleNamespace(hp=10, max_hp=20, mp=5, max_mp=10, status_effects=[])
        logs = s.pass_turn(entity, engine=object())
        assert entity.hp == 10
        assert logs == []

    def test_starvation_damage_at_zero_hunger(self):
        s = systems.SurvivalSystem()
        s.hunger = 1
        entity = SimpleNamespace(hp=10, max_hp=20, mp=5, max_mp=10, status_effects=[])
        logs = s.pass_turn(entity, engine=None)  # hunger hits 0 this turn
        assert entity.hp == 8
        assert any("飢餓ダメージ" in line for line in logs)

    def test_starvation_death_message(self):
        s = systems.SurvivalSystem()
        s.hunger = 0
        entity = SimpleNamespace(hp=1, max_hp=20, mp=5, max_mp=10, status_effects=[])
        logs = s.pass_turn(entity, engine=None)
        assert entity.hp <= 0
        assert any("力尽きた" in line for line in logs)


# ============================================================
# systems.py — MonsterPreset
# ============================================================


class TestMonsterPreset:
    def test_tile_map_known_entries(self):
        assert systems.MonsterPreset.MONSTER_TILE_MAP["slime"] == "TR_MONSTER_01"
        assert systems.MonsterPreset.MONSTER_TILE_MAP["orc"] == "TR_MONSTER_03"
        assert systems.MonsterPreset.PET_TILE_MAP["wolf"] == "TR_MONSTER_VAR_01"
        assert systems.MonsterPreset.PET_TILE_MAP["dragon"] == "TR_MONSTER_VAR_03"

    def test_create_from_yaml_data(self):
        e = systems.MonsterPreset.create("slime", 3, 4)
        assert (e.x, e.y) == (3, 4)
        assert e.name == "ぷち"
        assert e.max_hp == 14
        assert e.hp == 14
        assert e.faction == systems.FACTION_MONSTER
        assert isinstance(e.aggro, systems.AggroList)
        assert isinstance(e.resistances, systems.ResistanceSet)
        assert e.status_effects == []
        assert e.monster_type == "slime"

    def test_create_orc_uses_yaml_entry(self):
        e = systems.MonsterPreset.create("orc", 0, 0)
        assert e.name == "オーク"
        assert e.max_hp > 0
        assert e.monster_type == "orc"

    def test_create_unknown_falls_back_to_placeholder(self):
        e = systems.MonsterPreset.create("no_such_beast", 7, 8)
        assert e.name == "モンスター"
        assert (e.x, e.y) == (7, 8)

    def test_create_uses_fallback_presets_when_yaml_unavailable(self, monkeypatch):
        from config_manager import DataCache

        monkeypatch.setattr(DataCache, "get_data", lambda path: None)
        e = systems.MonsterPreset.create("goblin", 1, 2)
        assert e.name == "ゴブリン"
        assert e.max_hp == 24
        assert e.hp == 24
        assert e.faction == systems.FACTION_MONSTER
        assert e.monster_type == "goblin"

    def test_fallback_presets_cover_slime_and_orc(self, monkeypatch):
        from config_manager import DataCache

        monkeypatch.setattr(DataCache, "get_data", lambda path: None)
        assert systems.MonsterPreset.create("slime", 0, 0).max_hp == 14
        assert systems.MonsterPreset.create("orc", 0, 0).max_hp == 42


# ============================================================
# save_system.py — pickle save/load
# ============================================================


def _fake_engine(turns=7, dungeon_level=3, game_state="play"):
    player = SimpleNamespace(name="勇者", hp=100, max_hp=100, mp=50, max_mp=50)
    return SimpleNamespace(
        player=player, pet=None, turns=turns, dungeon_level=dungeon_level, game_state=game_state
    )


@pytest.fixture
def save_path(tmp_path, monkeypatch):
    path = tmp_path / "savegame.bin"
    monkeypatch.setattr(SaveSystem, "SAVE_PATH", str(path))
    return path


class TestPickleSaveLoad:
    def test_save_creates_file_and_reports_success(self, save_path):
        msg = SaveSystem.save(_fake_engine())
        assert "セーブ完了" in msg
        assert save_path.exists()
        assert save_path.stat().st_size >= 64  # checksum + hmac + payload

    def test_save_stamps_current_version_on_player(self, save_path):
        engine = _fake_engine()
        SaveSystem.save(engine)
        assert engine.player.save_version == SaveSystem.CURRENT_VERSION

    def test_file_layout_is_checksum_hmac_payload(self, save_path):
        import hashlib

        SaveSystem.save(_fake_engine())
        data = save_path.read_bytes()
        header_len = 64 + SaveSystem.SAVE_HEADER_EXTRA_LEN
        checksum, file_hmac = data[:32], data[32:64]
        version_header, payload = data[64:header_len], data[header_len:]
        assert checksum == hashlib.sha256(payload).digest()
        assert file_hmac == SaveSystem._compute_hmac(payload)
        assert version_header[:4] == SaveSystem.SAVE_HEADER_MAGIC
        assert int.from_bytes(version_header[4:], "big") == SaveSystem.SAVE_VERSION
        assert payload[:2] == b"\x1f\x8b"  # gzip magic

    def test_round_trip_preserves_engine_state(self, save_path):
        engine = _fake_engine(turns=42, dungeon_level=5, game_state="title")
        SaveSystem.save(engine)
        loaded, msg = SaveSystem.load()
        assert loaded is not None
        assert "ロード完了" in msg
        assert loaded.turns == 42
        assert loaded.dungeon_level == 5
        assert loaded.game_state == "title"
        assert loaded.player.name == "勇者"
        assert loaded.player.save_version == "2.0.0"

    def test_load_missing_file(self, save_path):
        loaded, msg = SaveSystem.load()
        assert loaded is None
        assert "見つかりません" in msg

    def test_second_save_rotates_previous_save_into_bak1(self, save_path):
        SaveSystem.save(_fake_engine(turns=1))
        assert not (tmp_bak(save_path, 1)).exists()
        SaveSystem.save(_fake_engine(turns=2))
        assert tmp_bak(save_path, 1).exists()

    def test_web_server_is_restored_after_pickle(self, save_path):
        sentinel = object()
        engine = _fake_engine()
        engine.web_server = sentinel
        SaveSystem.save(engine)
        assert engine.web_server is sentinel


def tmp_bak(save_path, generation: int):
    from pathlib import Path

    return Path(str(save_path) + f".bak{generation}")


class TestBackupRotation:
    def test_four_saves_keep_three_most_recent_generations(self, save_path):
        for turns in (1, 2, 3, 4):
            SaveSystem.save(_fake_engine(turns=turns))
        assert tmp_bak(save_path, 1).exists()
        assert tmp_bak(save_path, 2).exists()
        assert tmp_bak(save_path, 3).exists()
        # The backup is taken BEFORE overwriting, so bak1 = previous save,
        # bak2 = two saves ago, bak3 = three saves ago.
        assert _load_bak_turns(save_path, 1) == 3
        assert _load_bak_turns(save_path, 2) == 2
        assert _load_bak_turns(save_path, 3) == 1

    def _load_as_main(self, save_path, generation):
        import shutil

        shutil.copy2(tmp_bak(save_path, generation), save_path)
        return SaveSystem.load()

    def test_first_save_creates_no_backups(self, save_path):
        SaveSystem.save(_fake_engine())
        assert not tmp_bak(save_path, 1).exists()

    def test_create_backup_without_file_is_noop(self, save_path):
        SaveSystem._create_backup()
        assert not save_path.exists()


def _load_bak_turns(save_path, generation: int):
    import shutil

    shutil.copy2(tmp_bak(save_path, generation), save_path)
    loaded, _ = SaveSystem.load()
    return loaded.turns


class TestCorruptionAndRecovery:
    def test_truncated_file_fails_without_recovery(self, save_path):
        save_path.write_bytes(b"tiny")
        loaded, msg = SaveSystem.load()
        assert loaded is None
        assert "ロード失敗" in msg

    def test_tampered_payload_fails_without_backup(self, save_path):
        SaveSystem.save(_fake_engine())  # first save => no backups exist
        data = bytearray(save_path.read_bytes())
        data[100] ^= 0xFF
        save_path.write_bytes(bytes(data))
        loaded, msg = SaveSystem.load()
        assert loaded is None
        assert "ロード失敗" in msg

    def test_corrupted_main_file_recovers_from_backup(self, save_path):
        SaveSystem.save(_fake_engine(turns=5))
        SaveSystem.save(_fake_engine(turns=6))  # bak1 now holds turns=5
        data = bytearray(save_path.read_bytes())
        data[100] ^= 0xFF
        save_path.write_bytes(bytes(data))

        loaded, msg = SaveSystem.load()
        assert loaded is not None
        assert loaded.turns == 5
        assert "復旧" in msg

    def test_unsupported_player_version_rejected(self, save_path):
        import gzip
        import hashlib
        import pickle

        engine = SimpleNamespace(
            player=SimpleNamespace(save_version="0.5.0", hp=1), turns=1
        )
        payload = gzip.compress(pickle.dumps(engine))
        blob = hashlib.sha256(payload).digest() + SaveSystem._compute_hmac(payload) + payload
        save_path.write_bytes(blob)

        loaded, msg = SaveSystem.load(allow_backup_recovery=False)
        assert loaded is None
        assert "未対応" in msg

    def test_no_recovery_when_disabled(self, save_path):
        SaveSystem.save(_fake_engine())
        SaveSystem.save(_fake_engine())
        data = bytearray(save_path.read_bytes())
        data[100] ^= 0xFF
        save_path.write_bytes(bytes(data))

        loaded, msg = SaveSystem.load(allow_backup_recovery=False)
        assert loaded is None
        assert "ロード失敗" in msg


# ============================================================
# save_system.py — JSON serialize / deserialize
# ============================================================


def _json_fake_engine():
    player = SimpleNamespace(to_dict=lambda: {"name": "勇者", "hp": 100})
    pet = SimpleNamespace(to_dict=lambda: {"name": "犬", "hp": 30})
    return SimpleNamespace(
        player=player,
        pet=pet,
        dungeon_level=4,
        turns=12,
        game_state="play",
        survival=SimpleNamespace(
            gold=10, platinum=2, hunger=5000, sleepiness=1,
            karma=15, karma_law_chaos=3, legacy_skills=["skill_x"],
        ),
        inventory=SimpleNamespace(items=[SimpleNamespace(to_dict=lambda: {"name": "剣"})]),
        pet_inventory=SimpleNamespace(items=[]),
        items_on_ground=[],
        territory_state=None,
    )


class TestJsonSerialization:
    def test_serialize_engine_to_dict_shape(self):
        data = SaveSystem.serialize_engine_to_dict(_json_fake_engine())
        assert data["save_version"] == "2.0.0"
        assert data["dungeon_level"] == 4
        assert data["turns"] == 12
        assert data["game_state"] == "play"
        assert data["player"] == {"name": "勇者", "hp": 100}
        assert data["pet"] == {"name": "犬", "hp": 30}
        assert data["survival"]["gold"] == 10
        assert data["survival"]["legacy_skills"] == ["skill_x"]
        assert data["inventory"] == [{"name": "剣"}]
        assert data["territory"] is None

    def test_serialize_defaults_for_sparse_engine(self):
        data = SaveSystem.serialize_engine_to_dict(SimpleNamespace())
        assert data["dungeon_level"] == 1
        assert data["turns"] == 0
        assert data["game_state"] == "play"
        assert data["player"] is None
        assert data["survival"] == {}
        assert data["inventory"] == []

    def test_save_then_load_json_round_trip(self, tmp_path, monkeypatch):
        target = tmp_path / "save.json"
        msg = SaveSystem.save_json(_json_fake_engine(), str(target))
        assert "JSONセーブ完了" in msg
        assert target.exists()

        captured = {}
        sentinel = object()

        def fake_deserialize(data, target_engine=None):
            captured.update(data)
            return sentinel

        monkeypatch.setattr(SaveSystem, "deserialize_dict_to_engine", fake_deserialize)
        loaded, msg = SaveSystem.load_json(str(target))
        assert loaded is sentinel
        assert "JSONロード完了" in msg
        assert captured["turns"] == 12
        assert captured["player"]["name"] == "勇者"

    def test_save_json_failure_message(self, tmp_path, monkeypatch):
        engine = SimpleNamespace(
            player=SimpleNamespace(to_dict=lambda: 1 / 0),  # raises on to_dict
        )
        msg = SaveSystem.save_json(engine, str(tmp_path / "boom.json"))
        assert msg == "JSONセーブ失敗"

    def test_load_json_missing_file(self, tmp_path):
        loaded, msg = SaveSystem.load_json(str(tmp_path / "absent.json"))
        assert loaded is None
        assert "見つかりません" in msg

    def test_load_json_rejects_tampered_data(self, tmp_path):
        target = tmp_path / "save.json"
        SaveSystem.save_json(_json_fake_engine(), str(target))
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["data"]["turns"] = 99999  # invalidate checksum
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        loaded, msg = SaveSystem.load_json(str(target))
        assert loaded is None
        assert msg == "JSONロード失敗"

    def test_load_json_accepts_raw_dict_without_checksum(self, tmp_path, monkeypatch):
        target = tmp_path / "raw.json"
        target.write_text('{"turns": 3}', encoding="utf-8")
        sentinel = object()
        seen = {}

        def fake_deserialize(data, target_engine=None):
            seen["d"] = data
            return sentinel

        monkeypatch.setattr(SaveSystem, "deserialize_dict_to_engine", fake_deserialize)
        loaded, msg = SaveSystem.load_json(str(target))
        assert loaded is sentinel
        assert seen["d"] == {"turns": 3}
        assert "JSONロード完了" in msg

    def test_deserialize_into_existing_engine(self):
        from ecs.entity import Entity as _Entity

        base_player = _Entity(0, 0, "@", name="転送元", is_player=True)
        target = SimpleNamespace(
            survival=SimpleNamespace(
                gold=0, platinum=0, hunger=0, thirst=0, sleep=0,
                karma_law_chaos=0, legacy_skills=[],
            ),
            inventory=SimpleNamespace(items=["OLD"]),
            pet_inventory=SimpleNamespace(items=[]),
            items_on_ground=["STALE"],
            pet=None,
        )
        data = {
            "save_version": "2.0.0",
            "dungeon_level": 2,
            "turns": 9,
            "game_state": "play",
            "player": base_player.to_dict(),
            "pet": None,
            "survival": {"gold": 3},
            "inventory": [],
            "pet_inventory": [],
            "items_on_ground": [],
        }
        engine = SaveSystem.deserialize_dict_to_engine(data, target_engine=target)
        assert engine is target
        assert engine.dungeon_level == 2
        assert engine.turns == 9
        assert isinstance(engine.player, _Entity)
        assert engine.player.name == "転送元"
        assert engine.survival.gold == 3
        assert engine.inventory.items == []
        assert engine.items_on_ground == []

    def test_deserialize_applies_v1_migration(self):
        from ecs.entity import Entity as _Entity

        base_player = _Entity(0, 0, "@", name="旧形式", is_player=True)
        player_dict = base_player.to_dict()
        player_dict.pop("components", None)
        target = SimpleNamespace(
            survival=SimpleNamespace(
                gold=0, platinum=0, hunger=0, thirst=0, sleep=0,
                karma_law_chaos=0, legacy_skills=[],
            ),
            inventory=None, pet_inventory=None, pet=None,
        )
        data = {
            "save_version": "1.0.0",
            "dungeon_level": 1,
            "turns": 0,
            "game_state": "play",
            "player": player_dict,
        }
        engine = SaveSystem.deserialize_dict_to_engine(data, target_engine=target)
        assert isinstance(engine.player, _Entity)

    def test_convert_pickle_to_json_without_save(self, save_path):
        msg = SaveSystem.convert_pickle_to_json()
        assert "変換失敗" in msg

    def test_backwards_compat_alias(self):
        import migration_pipeline
        import save_system

        assert SaveSystem.DEFAULT_FIELD_FACTORIES is migration_pipeline.DEFAULT_FIELD_FACTORIES
        assert save_system.MigrationManager is migration_pipeline.MigrationPipeline


# ============================================================
# save_system.py — clear_run
# ============================================================


class TestClearRun:
    def _engine(self):
        engine = MagicMock()
        engine.player = SimpleNamespace(
            hp=0, max_hp=80, mp=0, max_mp=40, x=9, y=9, status_effects=["毒"]
        )
        engine.pet = SimpleNamespace(hp=0, max_hp=30, mp=0, max_mp=10, x=9, y=9, status_effects=["麻痺"])
        engine.survival = SimpleNamespace(hunger=100, sleepiness=99)
        engine.msg_log.history = MagicMock()
        return engine

    def test_clear_run_resets_run_state(self, monkeypatch):
        game_map = MagicMock()
        game_map.rooms = [SimpleNamespace(center=(3, 3))]
        game_map.start_pos = (1, 1)
        monkeypatch.setattr("map_engine.GameMap", lambda *a, **k: game_map)

        engine = self._engine()
        SaveSystem.clear_run(engine)

        assert isinstance(engine.game_state_machine, GameStateMachine)
        assert engine.game_state_machine.current == "playing"
        assert engine.run_summary is None
        assert engine.turns == 0
        assert engine.dungeon_level == 1
        assert engine.player.hp == 80
        assert engine.player.mp == 40
        assert engine.player.status_effects == []
        assert engine.pet.hp == 30
        assert engine.pet.status_effects == []
        assert engine.survival.hunger == 8000
        assert engine.survival.sleepiness == 0
        assert engine.altar_pos == (5, 3)
        assert (engine.player.x, engine.player.y) == (1, 1)
        assert (engine.pet.x, engine.pet.y) == (2, 1)
        game_map.generate_dungeon.assert_called_once()
        game_map.compute_fov.assert_called_once()
        engine._spawn_dungeon.assert_called_once()

    def test_clear_run_rebuilds_entity_manager(self, monkeypatch):
        game_map = MagicMock()
        game_map.rooms = [SimpleNamespace(center=(0, 0))]
        game_map.start_pos = (2, 2)
        monkeypatch.setattr("map_engine.GameMap", lambda *a, **k: game_map)

        engine = self._engine()
        SaveSystem.clear_run(engine)

        engine.entity_manager.clear.assert_called_once()
        added = [call.args[0] for call in engine.entity_manager.add_entity.call_args_list]
        assert added == [engine.player, engine.pet]
        engine.entity_manager.items_on_ground.clear.assert_called_once()
        engine.entity_manager.resource_nodes.clear.assert_called_once()
        engine.msg_log.history.clear.assert_called_once()
        engine.log.assert_called_once()


# ============================================================
# data_manager.py — YAML cache / localization / generation
# ============================================================


@pytest.fixture(scope="module")
def dm() -> DataManager:
    return DataManager()


@pytest.fixture
def dm_empty(tmp_path) -> DataManager:
    return DataManager(str(tmp_path))


class TestYamlCache:
    def test_cached_load_returns_same_object(self):
        path = _REPO / "data" / "items.yaml"
        first = _cached_load_yaml(path)
        second = _cached_load_yaml(path)
        assert first is second

    def test_clear_yaml_cache_empties_store(self):
        _cached_load_yaml(_REPO / "data" / "items.yaml")
        assert _YAML_CACHE
        clear_yaml_cache()
        assert not _YAML_CACHE

    def test_load_yaml_missing_file_returns_empty(self, dm_empty, tmp_path):
        assert dm_empty._load_yaml("no_such_file.yaml") == {}

    def test_data_manager_clear_cache_delegates(self, dm_empty):
        _cached_load_yaml(_REPO / "data" / "items.yaml")
        dm_empty.clear_cache()
        assert not _YAML_CACHE


class TestDataManagerEmptyDir:
    def test_missing_data_dir_yields_empty_repositories(self, dm_empty):
        assert dm_empty.items._data == {}
        assert dm_empty.monsters._data == {}
        assert dm_empty.quests._data == {}
        assert dm_empty.localization == {}

    def test_materials_still_available(self, dm_empty):
        assert dm_empty.materials_data  # MATERIALS is a code constant

    def test_validate_all_data_passes_on_empty(self, dm_empty):
        assert dm_empty.validate_all_data() == []

    def test_random_item_falls_back_to_sample(self, dm_empty):
        item = dm_empty.get_random_item_for_floor(1, 2, 3)
        assert isinstance(item, Item)
        assert (item.x, item.y) == (2, 3)

    def test_random_monster_falls_back_to_slime(self, dm_empty):
        mob = dm_empty.get_random_monster_for_floor(1, 1, 1)
        assert mob.name == "ぷち"


class TestLocalization:
    def test_loads_locale_files_and_get_text(self, tmp_path):
        text_dir = tmp_path / "text"
        text_dir.mkdir()
        (text_dir / "xx.yaml").write_text(
            yaml.dump({"greeting": "こんにちは", "farewell": "さようなら"}, allow_unicode=True),
            encoding="utf-8",
        )
        manager = DataManager(str(tmp_path))
        assert manager.get_text("greeting", "xx") == "こんにちは"
        assert manager.get_localization("xx") == {"greeting": "こんにちは", "farewell": "さようなら"}

    def test_unknown_key_returns_key(self, tmp_path):
        text_dir = tmp_path / "text"
        text_dir.mkdir()
        (text_dir / "xx.yaml").write_text("greeting: hi", encoding="utf-8")
        manager = DataManager(str(tmp_path))
        assert manager.get_text("missing_key", "xx") == "missing_key"

    def test_unknown_locale_returns_key(self, tmp_path):
        manager = DataManager(str(tmp_path))
        assert manager.get_text("anything", "no_locale") == "anything"


class TestCreateItem:
    def test_normal_quality_matches_definition(self, dm):
        item = dm.create_item("longsword")
        data = dm.items.get("longsword")
        assert isinstance(item, Item)
        assert item.name == data.name
        assert item.quality == QUALITY_NORMAL
        assert item.hit_bonus == int(data.hit_bonus)
        assert item.dmg_bonus == int(data.dmg_bonus)
        assert item.pv == int(data.pv)
        assert item.dv == int(data.dv)
        assert item.count == 1
        assert item.identified is True

    def test_bad_quality_reduces_bonuses_without_going_negative(self, dm):
        data = dm.items.get("longsword")
        item = dm.create_item("longsword", quality=QUALITY_BAD)
        assert item.quality == QUALITY_BAD
        assert item.hit_bonus == max(0, int(data.hit_bonus) - 2)
        assert item.dmg_bonus == max(0, int(data.dmg_bonus) - 1)

    def test_good_quality_adds_max_bonus_when_dice_roll_high(self, dm, monkeypatch):
        monkeypatch.setattr(random, "randint", lambda a, b: b)
        data = dm.items.get("longsword")
        item = dm.create_item("longsword", quality=QUALITY_GOOD)
        assert item.hit_bonus == int(data.hit_bonus) + 3
        assert item.dmg_bonus == int(data.dmg_bonus) + 2
        assert item.pv == int(data.pv) + 1

    def test_miracle_quality_adds_max_bonus_when_dice_roll_high(self, dm, monkeypatch):
        monkeypatch.setattr(random, "randint", lambda a, b: b)
        data = dm.items.get("longsword")
        item = dm.create_item("longsword", quality=QUALITY_MIRACLE)
        assert item.hit_bonus == int(data.hit_bonus) + 7
        assert item.dmg_bonus == int(data.dmg_bonus) + 5
        assert item.pv == int(data.pv) + 4
        assert item.dv == int(data.dv) + 3

    def test_god_quality_adds_max_bonus_when_dice_roll_high(self, dm, monkeypatch):
        monkeypatch.setattr(random, "randint", lambda a, b: b)
        data = dm.items.get("longsword")
        item = dm.create_item("longsword", quality=QUALITY_GOD)
        assert item.hit_bonus == int(data.hit_bonus) + 15
        assert item.dmg_bonus == int(data.dmg_bonus) + 12
        assert item.pv == int(data.pv) + 10
        assert item.dv == int(data.dv) + 8

    def test_count_cursed_and_material_are_honored(self, dm):
        item = dm.create_item("potion_heal", count=5, cursed=True, material="iron")
        assert item.count == 5
        assert item.cursed is True
        assert item.material == "iron"

    def test_unknown_id_falls_back_to_sample_item(self, dm):
        item = dm.create_item("mystery_item_xyz", 4, 5)
        assert isinstance(item, Item)
        assert (item.x, item.y) == (4, 5)


class TestRandomItemGeneration:
    def test_high_floor_low_roll_yields_god_quality_with_material(self, dm, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.0)
        item = dm.get_random_item_for_floor(10)
        assert item.quality == QUALITY_GOD
        assert item.material is not None

    def test_low_roll_distribution_gives_bad_quality(self, dm, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.93)
        item = dm.get_random_item_for_floor(1)
        assert item.quality == QUALITY_BAD
        assert item.cursed is True

    def test_mid_roll_yields_normal_quality(self, dm, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.5)
        item = dm.get_random_item_for_floor(1)
        assert item.quality == QUALITY_NORMAL
        assert item.cursed is False

    def test_returns_item_for_requested_position(self, dm, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.5)
        item = dm.get_random_item_for_floor(3, 7, 8)
        assert (item.x, item.y) == (7, 8)


class TestCreateMonster:
    def test_slime_from_yaml(self, dm):
        mob = dm.create_monster("slime", 2, 3)
        assert (mob.x, mob.y) == (2, 3)
        assert mob.name == "ぷち"
        assert mob.max_hp == 14
        assert mob.hp == 14
        assert mob.faction == "monster"
        assert mob.ai_type == "coward"
        assert mob.ai_role == "brute"
        assert mob.status_effects == []
        assert mob.skills == []

    def test_kiter_role_gets_preferred_range_and_resistances(self, dm):
        mob = dm.create_monster("hound_fire")
        assert mob.ai_role == "kiter"
        assert mob.preferred_range == KITER_PREFERRED_RANGE
        assert mob.resistances.fire == 80
        assert mob.resistances.cold == -20
        assert len(mob.abilities) == 1
        assert getattr(mob.abilities[0], "id", "") == "fire_breath"

    def test_level_scaling_increases_attributes(self, dm):
        data = dm.monsters.get("goblin")
        base_strength = int((data.attributes or {}).get("strength", 10))
        base = dm.create_monster("goblin", level_scale=1)
        scaled = dm.create_monster("goblin", level_scale=3)
        assert scaled.attributes.strength == int(base_strength * 1.3)
        assert scaled.attributes.strength > base.attributes.strength
        assert scaled.max_hp == int(data.max_hp * 1.3)

    def test_faction_override(self, dm):
        mob = dm.create_monster("slime", faction="guard")
        assert mob.faction == "guard"

    def test_unknown_id_falls_back_to_preset(self, dm):
        mob = dm.create_monster("mystery_beast", 1, 2)
        assert mob.name == "モンスター"
        assert (mob.x, mob.y) == (1, 2)


class TestRandomMonsterGeneration:
    def test_floor_one_picks_from_shallow_pool(self, dm):
        pool = [
            m_id
            for m_id, m in dm.monsters._data.items()
            if (m.min_floor or 1) <= 1 <= (m.max_floor or 999) + 3
        ]
        assert pool
        random.seed(0)
        mob = dm.get_random_monster_for_floor(1, 5, 5)
        random.seed(0)
        expected_id = random.choice(pool)
        assert mob.name == dm.monsters._data[expected_id].name

    def test_deep_floor_falls_back_to_closest_three(self, dm):
        # Beyond every monster's max_floor the tier pool empties; the fallback
        # picks from the 3 monsters closest by depth distance.
        candidates = []
        for m_id, m_val in dm.monsters._data.items():
            min_floor = m_val.min_floor or 1
            max_floor = m_val.max_floor or 999
            if 9999 < min_floor:
                dist = min_floor - 9999
            elif 9999 > max_floor:
                dist = 9999 - max_floor
            else:
                dist = 0
            candidates.append((dist, m_id))
        candidates.sort(key=lambda item: item[0])
        expected_names = {dm.monsters._data[m_id].name for _, m_id in candidates[:3]}

        mob = dm.get_random_monster_for_floor(9999, 0, 0)
        assert mob.name in expected_names

    def test_level_scale_uses_floor_depth(self, dm):
        pool = [
            m_id
            for m_id, m in dm.monsters._data.items()
            if (m.min_floor or 1) <= 5 <= (m.max_floor or 999) + 3
        ]
        random.seed(0)
        mob = dm.get_random_monster_for_floor(5, 0, 0)
        random.seed(0)
        chosen = random.choice(pool)
        expected_hp = int(dm.monsters._data[chosen].max_hp * (1.0 + (5 - 1) * 0.15))
        assert mob.max_hp == expected_hp


class TestValidateAllData:
    def test_real_data_has_no_errors(self, dm):
        errors = dm.validate_all_data()
        assert isinstance(errors, list)
        assert errors == []


# ============================================================
# achievement_system.py — condition checks & rewards
# ============================================================


@pytest.fixture
def ach_registry():
    reg = AchievementRegistry()
    saved = dict(reg._achievements)
    yield reg
    reg._achievements = saved


CONDITION_ACHIEVEMENTS = {
    "a_kill": {"condition": {"type": "kill_count", "target": 3}},
    "a_monster_type": {"condition": {"type": "monster_type_kill", "monster_key": "goblin", "target": 4}},
    "a_floors": {"condition": {"type": "dungeon_floors", "target": 2}},
    "a_speedrun": {"condition": {"type": "speedrun", "time_limit_seconds": 600}},
    "a_festival": {"condition": {"type": "festival_date"}, "available_dates": ["01-01", "12-24"]},
    "a_unique_monsters": {"condition": {"type": "unique_monsters_killed", "target": 2}},
    "a_unique_items": {"condition": {"type": "unique_items_obtained", "target": 2}},
    "a_weekly": {"condition": {"type": "weekly_time", "target": 100}},
    "a_friend": {"condition": {"type": "friend_helps", "target": 2}},
    "a_reincarnation": {"condition": {"type": "reincarnation", "reincarnation_count": 2, "total_level_earned": 50}},
    "a_meta": {"condition": {"type": "meta_progression_all"}},
    "a_combo": {"condition": {"type": "special_combo", "required_items": ["milk", "honey"]}},
}


@pytest.fixture
def cond_manager(ach_registry, tmp_path):
    payload = {"achievements": {}}
    for aid, spec in CONDITION_ACHIEVEMENTS.items():
        entry = {"name": aid, "description": "説明"}
        entry.update(spec)
        payload["achievements"][aid] = entry
    path = tmp_path / "conditions.yaml"
    path.write_text(yaml.dump(payload, allow_unicode=True), encoding="utf-8")
    ach_registry.load(str(path))
    return AchievementManager(ach_registry)


class TestAchievementRegistry:
    def test_singleton(self):
        assert AchievementRegistry() is REGISTRY

    def test_load_real_yaml(self, ach_registry):
        ach_registry.load(str(_REPO / "data" / "achievements.yaml"))
        assert len(ach_registry.all()) > 0
        some = next(iter(ach_registry.all().values()))
        assert isinstance(some, AchievementData)
        assert some.id == next(iter(ach_registry.all()))

    def test_get_unknown_returns_none(self, ach_registry):
        assert ach_registry.get("no_such_achievement") is None

    def test_all_returns_copy(self, ach_registry):
        ach_registry.load(str(_REPO / "data" / "achievements.yaml"))
        snapshot = ach_registry.all()
        snapshot.clear()
        assert ach_registry.all()  # original untouched

    def test_load_missing_file_creates_default(self, ach_registry, tmp_path):
        ach_registry.load(str(tmp_path / "absent.yaml"))
        default = ach_registry.get("first_blood")
        assert default is not None
        assert default.name == "最初の血"
        assert default.reward_gold == 100

    def test_ensure_loaded_respects_existing_data(self, ach_registry, tmp_path):
        custom = tmp_path / "custom.yaml"
        custom.write_text(
            yaml.dump({"achievements": {"custom_only": {"name": "独自", "description": "d"}}}, allow_unicode=True),
            encoding="utf-8",
        )
        ach_registry.load(str(custom))
        ach_registry.ensure_loaded()  # registry non-empty -> no reload
        assert ach_registry.get("custom_only") is not None

    def test_ensure_loaded_when_empty(self, ach_registry, monkeypatch):
        monkeypatch.chdir(_ROOT)
        ach_registry._achievements = {}
        ach_registry.ensure_loaded()
        assert ach_registry.all()

    def test_achievement_data_defaults(self):
        data = AchievementData(id="x", name="n", description="d")
        assert data.icon == "🏆"
        assert data.reward_gold == 0
        assert data.reward_item is None
        assert data.hidden is False
        assert data.prerequisites == []
        assert data.trigger_condition == {}
        assert data.auto_equip_title is False
        assert data.status_bonus == {}


class TestCheckAchievementConditions:
    def _player(self, **fields):
        return _player(**fields)

    def test_already_achieved_short_circuits(self, cond_manager):
        p = self._player(kill_counts={"goblin": 100})
        p.achievements.append("a_kill")
        assert cond_manager.check_achievement(p, "a_kill") is False

    def test_unknown_id(self, cond_manager):
        assert cond_manager.check_achievement(self._player(), "a_nope") is False

    def test_kill_count(self, cond_manager):
        p = self._player(kill_counts={"goblin": 2, "orc": 1})
        assert cond_manager.check_achievement(p, "a_kill") is True
        p2 = self._player(kill_counts={"goblin": 2})
        assert cond_manager.check_achievement(p2, "a_kill") is False

    def test_kill_count_empty_totals(self, cond_manager):
        p = _player()
        p.kill_counts = {}
        assert cond_manager.check_achievement(p, "a_kill") is False

    def test_monster_type_kill(self, cond_manager):
        p = self._player(monster_killed_types={"goblin": 4})
        assert cond_manager.check_achievement(p, "a_monster_type") is True
        p2 = self._player(monster_killed_types={"goblin": 3})
        assert cond_manager.check_achievement(p2, "a_monster_type") is False

    def test_dungeon_floors_by_visited_list(self, cond_manager):
        p = self._player(dungeon_floors_visited=["f1", "f2"], max_dungeon_depth=0)
        assert cond_manager.check_achievement(p, "a_floors") is True

    def test_dungeon_floors_by_max_depth(self, cond_manager):
        p = self._player(dungeon_floors_visited=[], max_dungeon_depth=2)
        assert cond_manager.check_achievement(p, "a_floors") is True
        p2 = self._player(dungeon_floors_visited=[], max_dungeon_depth=1)
        assert cond_manager.check_achievement(p2, "a_floors") is False

    def test_speedrun(self, cond_manager):
        p = self._player(play_time_seconds=500, max_dungeon_depth=5)
        assert cond_manager.check_achievement(p, "a_speedrun") is True
        slow = self._player(play_time_seconds=700, max_dungeon_depth=5)
        assert cond_manager.check_achievement(slow, "a_speedrun") is False
        shallow = self._player(play_time_seconds=10, max_dungeon_depth=4)
        assert cond_manager.check_achievement(shallow, "a_speedrun") is False

    def test_festival_date(self, cond_manager):
        p = self._player(last_festival_check="12-24")
        assert cond_manager.check_achievement(p, "a_festival") is True
        p2 = self._player(last_festival_check="08-01")
        assert cond_manager.check_achievement(p2, "a_festival") is False

    def test_unique_monsters_killed(self, cond_manager):
        p = self._player(monster_killed_types={"slime": 1, "orc": 2})
        assert cond_manager.check_achievement(p, "a_unique_monsters") is True
        p2 = self._player(monster_killed_types={"slime": 5})
        assert cond_manager.check_achievement(p2, "a_unique_monsters") is False

    def test_unique_items_obtained(self, cond_manager):
        p = self._player(unique_items_obtained={"sword", "shield"})
        assert cond_manager.check_achievement(p, "a_unique_items") is True
        p2 = self._player(unique_items_obtained={"sword"})
        assert cond_manager.check_achievement(p2, "a_unique_items") is False

    def test_weekly_time(self, cond_manager):
        assert cond_manager.check_achievement(self._player(weekly_play_time=100), "a_weekly") is True
        assert cond_manager.check_achievement(self._player(weekly_play_time=99), "a_weekly") is False

    def test_friend_helps(self, cond_manager):
        assert cond_manager.check_achievement(self._player(friend_helps=2), "a_friend") is True
        assert cond_manager.check_achievement(self._player(friend_helps=1), "a_friend") is False

    def test_reincarnation(self, cond_manager):
        p = self._player(reincarnation_count=2, total_level_earned=50)
        assert cond_manager.check_achievement(p, "a_reincarnation") is True
        p2 = self._player(reincarnation_count=2, total_level_earned=49)
        assert cond_manager.check_achievement(p2, "a_reincarnation") is False

    def test_meta_progression_all(self, cond_manager):
        assert cond_manager.check_achievement(self._player(meta_progression=["a", "b", "c"]), "a_meta") is True
        assert cond_manager.check_achievement(self._player(meta_progression=["a", "b"]), "a_meta") is False

    def test_special_combo(self, cond_manager):
        p = self._player(special_items_combo=["milk", "honey", "bread"])
        assert cond_manager.check_achievement(p, "a_combo") is True
        p2 = self._player(special_items_combo=["milk"])
        assert cond_manager.check_achievement(p2, "a_combo") is False

    def test_unknown_condition_type_fails(self, ach_registry, tmp_path):
        path = tmp_path / "weird.yaml"
        path.write_text(
            yaml.dump({"achievements": {"a_weird": {"name": "w", "description": "d", "condition": {"type": "quantum"}}}}, allow_unicode=True),
            encoding="utf-8",
        )
        ach_registry.load(str(path))
        assert AchievementManager(ach_registry).check_achievement(_player(), "a_weird") is False


REWARD_YAML = {
    "r_full": {
        "name": "完全報酬",
        "description": "全部載せ",
        "reward_gold": 120,
        "reward_skill_points": 2,
        "reward_title": "銀の剣士",
        "auto_equip_title": True,
        "status_bonus": {"strength": 3},
    },
    "r_plain": {"name": "報酬なし", "description": "なし"},
}


@pytest.fixture
def reward_manager(ach_registry, tmp_path):
    path = tmp_path / "rewards.yaml"
    path.write_text(
        yaml.dump({"achievements": REWARD_YAML}, allow_unicode=True), encoding="utf-8"
    )
    ach_registry.load(str(path))
    return AchievementManager(ach_registry)


class TestGrantAchievement:
    def test_full_rewards_applied(self, reward_manager):
        p = _player()
        base_strength = p.attributes.strength
        assert reward_manager.grant_achievement(p, "r_full") is True
        assert p.gold == 120
        assert p.skill_points == 2
        assert p.total_skill_points_earned == 2
        assert "銀の剣士" in p.titles
        assert p.equipped_title == "銀の剣士"
        assert p.attributes.strength == base_strength + 3
        assert p.achievements == ["r_full"]
        assert len(p.achievement_notifications) == 1
        assert "完全報酬" in p.achievement_notifications[0]

    def test_engine_gold_reward_and_log(self, reward_manager, monkeypatch):
        from sound_manager import SoundManager

        monkeypatch.setattr(SoundManager, "play_se", staticmethod(lambda *a, **k: None))
        engine = SimpleNamespace(survival=SimpleNamespace(gold=5), log=MagicMock())
        p = _player()
        assert reward_manager.grant_achievement(p, "r_full", engine=engine) is True
        assert engine.survival.gold == 125
        engine.log.assert_called_once()

    def test_plain_achievement_grants_nothing(self, reward_manager):
        p = _player()
        base_strength = p.attributes.strength
        assert reward_manager.grant_achievement(p, "r_plain") is True
        assert p.gold == 0
        assert p.skill_points == 0
        assert p.titles == []
        assert p.attributes.strength == base_strength

    def test_duplicate_grant_rejected(self, reward_manager):
        p = _player()
        assert reward_manager.grant_achievement(p, "r_plain") is True
        assert reward_manager.grant_achievement(p, "r_plain") is False
        assert len(p.achievement_notifications) == 1

    def test_unknown_id_rejected(self, reward_manager):
        assert reward_manager.grant_achievement(_player(), "a_nope") is False

    def test_title_not_duplicated(self, reward_manager):
        p = _player()
        p.titles.append("銀の剣士")
        reward_manager.grant_achievement(p, "r_full")
        assert p.titles.count("銀の剣士") == 1


class TestRunHistoryIntegration:
    def test_apply_run_history_updates_best_values(self):
        p = _player(max_dungeon_depth=2, total_turns=10)
        history = RunHistory(
            runs=1, last_depth=5, last_kills=0, last_turns=100,
            last_cause="戦闘", best_depth=5, best_kills=0,
        )
        AchievementManager().apply_run_history(p, history)
        assert p.max_dungeon_depth == 5
        assert p.total_turns == 100

    def test_apply_run_history_never_lowers_values(self):
        p = _player(max_dungeon_depth=9, total_turns=500)
        history = RunHistory(
            runs=1, last_depth=2, last_kills=0, last_turns=50,
            last_cause="戦闘", best_depth=3, best_kills=0,
        )
        AchievementManager().apply_run_history(p, history)
        assert p.max_dungeon_depth == 9
        assert p.total_turns == 500

    def test_check_run_end_grants_and_checks_titles(self, ach_registry, tmp_path, monkeypatch):
        path = tmp_path / "depth.yaml"
        path.write_text(
            yaml.dump({"achievements": {"a_depth": {"name": "深度", "description": "d", "condition": {"type": "dungeon_floors", "target": 5}}}}, allow_unicode=True),
            encoding="utf-8",
        )
        ach_registry.load(str(path))

        title_calls = []
        monkeypatch.setattr(TITLE_MANAGER, "check_all_titles", lambda player: title_calls.append(player))

        p = _player(max_dungeon_depth=1)
        history = RunHistory(
            runs=1, last_depth=5, last_kills=0, last_turns=10,
            last_cause="戦闘", best_depth=5, best_kills=0,
        )
        granted = AchievementManager(ach_registry).check_run_end(p, history)
        assert granted == ["a_depth"]
        assert title_calls == [p]

    def test_check_all_achievements_grants_every_eligible(self, cond_manager):
        p = _player(
            kill_counts={"goblin": 10},
            monster_killed_types={"goblin": 9, "orc": 1},
            weekly_play_time=200,
            friend_helps=5,
        )
        granted = cond_manager.check_all_achievements(p)
        assert set(granted) == {"a_kill", "a_monster_type", "a_unique_monsters", "a_weekly", "a_friend"}
        assert set(p.achievements) == set(granted)


# ============================================================
# title_system.py — registry, checks, grant, equip
# ============================================================


@pytest.fixture
def title_registry():
    reg = TitleRegistry()
    saved_titles = dict(reg._titles)
    saved_loaded = reg._loaded
    reg._titles = {}
    reg._loaded = False
    yield reg
    reg._titles = saved_titles
    reg._loaded = saved_loaded


TITLE_CONDITIONS_YAML = """
titles:
  t_depth:
    id: t_depth
    name: 探検家
    epithet: 深淵の目
    category: explore
    message: 深くまで降りた！
    condition: {type: dungeon_depth, min_depth: 3}
    effects: [{attr: strength, value: 2}]
  t_gold:
    id: t_gold
    name: 大富豪
    epithet: 黄金の
    category: wealth
    message: 金があふれる！
    condition: {type: gold_owned, value: 100}
    effects: []
  t_magic:
    id: t_magic
    name: 呪文使い
    epithet: 星読み
    category: skill
    message: 呪文を極めた！
    condition: {type: skill_level, skill: magic, level: 4}
    effects: []
"""


class TestTitleRegistry:
    def test_singleton(self):
        assert TitleRegistry() is TITLE_REGISTRY

    def test_load_real_yaml(self, title_registry):
        title_registry.load("data/titles.yaml")
        titles = title_registry.all()
        assert titles
        first = titles[0]
        assert isinstance(first, TitleData)
        assert title_registry.get(first.id) is first
        assert title_registry.get("no_such_title") is None

    def test_load_is_idempotent_when_loaded(self, title_registry):
        title_registry.load("data/titles.yaml")
        count = len(title_registry.all())
        title_registry.load("data/titles.yaml")
        assert len(title_registry.all()) == count

    def test_ensure_loaded_when_empty(self, title_registry, monkeypatch):
        monkeypatch.chdir(_ROOT)
        title_registry.ensure_loaded()
        assert title_registry.all()

    def test_by_category(self, title_registry):
        title_registry.load("data/titles.yaml")
        categories = {t.category for t in title_registry.all()}
        target = sorted(categories)[0]
        matches = title_registry.by_category(target)
        assert matches
        assert all(t.category == target for t in matches)

    def test_skill_condition_reads_yaml_skill_key(self, title_registry, tmp_path):
        path = tmp_path / "titles.yaml"
        path.write_text(TITLE_CONDITIONS_YAML, encoding="utf-8")
        title_registry.load(str(path))
        magic_title = title_registry.get("t_magic")
        assert magic_title.condition.target == "magic"
        assert magic_title.condition.level == 4

    def test_condition_defaults(self):
        cond = TitleCondition(type="kill_count")
        assert (cond.target, cond.count, cond.value, cond.level, cond.category, cond.min_depth, cond.max_turns) == ("", 0, 0, 0, "", 0, 0)


class TestTitleChecks:
    def setup_method(self):
        self.manager = TitleManager(registry=SimpleNamespace(
            get=lambda tid: None, all=lambda: [], ensure_loaded=lambda: None,
        ))

    def _player(self, **fields):
        return _player(**fields)

    def test_check_kill_count(self):
        p = self._player()
        p.kill_counts = {"goblin": 3}
        assert self.manager.check_kill_count(p, "goblin", 3) is True
        assert self.manager.check_kill_count(p, "goblin", 4) is False
        assert self.manager.check_kill_count(p, "orc", 1) is False

    def test_check_skill_level(self):
        p = self._player()
        p.skills = {"magic": Skill("magic")}
        p.skills["magic"].level = 5
        assert self.manager.check_skill_level(p, "magic", 5) is True
        assert self.manager.check_skill_level(p, "magic", 6) is False
        assert self.manager.check_skill_level(p, "absent_skill", 2) is False

    def test_check_dungeon_depth(self):
        p = self._player(max_dungeon_depth=7)
        assert self.manager.check_dungeon_depth(p, 7) is True
        assert self.manager.check_dungeon_depth(p, 8) is False

    def test_check_near_death(self):
        p = self._player(near_death_count=2)
        assert self.manager.check_near_death(p, 2) is True
        assert self.manager.check_near_death(p, 3) is False

    def test_check_piety(self):
        p = self._player(piety=50)
        assert self.manager.check_piety(p, 50) is True
        assert self.manager.check_piety(p, 51) is False

    def test_check_gold(self):
        p = self._player(gold=1000)
        assert self.manager.check_gold(p, 1000) is True
        assert self.manager.check_gold(p, 1001) is False

    def test_check_pet_count(self):
        p = self._player(pets=["a", "b"])
        assert self.manager.check_pet_count(p, 2) is True
        assert self.manager.check_pet_count(p, 3) is False

    def test_check_craft_count(self):
        p = self._player(craft_counts={"weapon": 4})
        assert self.manager.check_craft_count(p, "weapon", 4) is True
        assert self.manager.check_craft_count(p, "weapon", 5) is False
        assert self.manager.check_craft_count(p, "armor", 1) is False

    def test_check_level(self):
        p = self._player(level=10)
        assert self.manager.check_level(p, 10) is True
        assert self.manager.check_level(p, 11) is False

    def test_check_game_clear_time(self):
        fast = self._player(total_turns=900)
        assert self.manager.check_game_clear_time(fast, 1000) is True
        slow = self._player(total_turns=2000)
        assert self.manager.check_game_clear_time(slow, 1000) is False

    def test_check_condition_dispatch(self):
        p = self._player()
        p.kill_counts = {"goblin": 5}
        assert self.manager.check_condition(p, TitleCondition(type="kill_count", target="goblin", count=5)) is True
        assert self.manager.check_condition(p, TitleCondition(type="kill_count", target="orc", count=5)) is False

    def test_check_condition_other_routes(self):
        p = self._player(max_dungeon_depth=4, gold=500, level=8)
        assert self.manager.check_condition(p, TitleCondition(type="dungeon_depth", min_depth=4)) is True
        assert self.manager.check_condition(p, TitleCondition(type="gold_owned", value=500)) is True
        assert self.manager.check_condition(p, TitleCondition(type="level", value=8)) is True
        assert self.manager.check_condition(p, TitleCondition(type="dungeon_depth", min_depth=5)) is False

    def test_check_condition_unknown_type(self):
        p = self._player()
        assert self.manager.check_condition(p, TitleCondition(type="quantum_spin")) is False


def _stub_registry(*titles):
    by_id = {t.id: t for t in titles}
    return SimpleNamespace(
        get=lambda tid: by_id.get(tid),
        all=lambda: list(by_id.values()),
        ensure_loaded=lambda: None,
    )


def _title(title_id, attr="strength", value=2, hidden=False):
    return TitleData(
        id=title_id,
        name=f"称号{title_id}",
        epithet=f"二つ名{title_id}",
        category="kill",
        condition=TitleCondition(type="kill_count", target="goblin", count=1),
        effects=[TitleEffect(attr, value)],
        message=f"獲得！{title_id}",
        is_hidden=hidden,
    )


class TestGrantAndEffects:
    def _player(self):
        return _title_player()

    def test_grant_adds_title_notification_and_effects(self):
        manager = TitleManager(registry=_stub_registry(_title("t1")))
        p = self._player()
        base_strength = p.attributes.strength
        assert manager.grant_title(p, "t1") is True
        assert p.titles == ["t1"]
        assert p.title_notifications == ["獲得！t1"]
        assert p.attributes.strength == base_strength + 2

    def test_grant_all_attributes_effect(self):
        title = _title("t_all", attr="all_attributes", value=1)
        manager = TitleManager(registry=_stub_registry(title))
        p = self._player()
        base = {
            attr: getattr(p.attributes, attr)
            for attr in ("strength", "endurance", "dexterity", "perception",
                         "learning", "will", "magic", "charisma")
        }
        manager.grant_title(p, "t_all")
        for attr, value in base.items():
            assert getattr(p.attributes, attr) == value + 1

    def test_duplicate_grant_rejected(self):
        manager = TitleManager(registry=_stub_registry(_title("t1")))
        p = self._player()
        assert manager.grant_title(p, "t1") is True
        assert manager.grant_title(p, "t1") is False
        assert p.titles == ["t1"]
        assert len(p.title_notifications) == 1

    def test_grant_unknown_title_rejected(self):
        manager = TitleManager(registry=_stub_registry())
        assert manager.grant_title(_player(), "a_nope") is False

    def test_apply_then_remove_effects_restores_base(self):
        title = _title("t1")
        manager = TitleManager(registry=_stub_registry(title))
        p = self._player()
        base_strength = p.attributes.strength
        manager.apply_title_effects(p, title)
        assert p.attributes.strength == base_strength + 2
        manager.remove_title_effects(p, title)
        assert p.attributes.strength == base_strength

    def test_multiplier_effect_applied_as_addition(self):
        title = _title("t_mul", attr="strength", value=5)
        title.effects[0].is_multiplier = True
        manager = TitleManager(registry=_stub_registry(title))
        p = self._player()
        base_strength = p.attributes.strength
        manager.apply_title_effects(p, title)
        assert p.attributes.strength == base_strength + 5

    def test_effect_for_unknown_attribute_is_ignored(self):
        title = _title("t_special", attr="damage_vs_goblin", value=3)
        manager = TitleManager(registry=_stub_registry(title))
        p = self._player()
        manager.apply_title_effects(p, title)  # must not raise


class TestEquipUnequip:
    def test_equip_requires_ownership(self):
        manager = TitleManager(registry=_stub_registry(_title("t1")))
        p = _title_player()
        assert manager.equip_title(p, "t1") is False
        assert not p.equipped_title

    def test_equip_applies_effects(self):
        manager = TitleManager(registry=_stub_registry(_title("t1", value=2)))
        p = _title_player()
        p.titles.append("t1")
        base_strength = p.attributes.strength
        assert manager.equip_title(p, "t1") is True
        assert p.equipped_title == "t1"
        assert p.attributes.strength == base_strength + 2

    def test_switching_titles_swaps_effects(self):
        manager = TitleManager(registry=_stub_registry(_title("t1", value=2), _title("t2", value=5)))
        p = _title_player()
        p.titles.extend(["t1", "t2"])
        base_strength = p.attributes.strength
        manager.equip_title(p, "t1")
        assert p.attributes.strength == base_strength + 2
        manager.equip_title(p, "t2")
        assert p.attributes.strength == base_strength + 5
        assert p.equipped_title == "t2"

    def test_unequip_removes_effects(self):
        manager = TitleManager(registry=_stub_registry(_title("t1", value=2)))
        p = _title_player()
        p.titles.append("t1")
        base_strength = p.attributes.strength
        manager.equip_title(p, "t1")
        assert manager.unequip_title(p) is True
        assert p.attributes.strength == base_strength
        assert p.equipped_title == ""
        assert manager.unequip_title(p) is False

    def test_equip_title_missing_from_registry_still_sets_flag(self):
        manager = TitleManager(registry=_stub_registry())
        p = _player()
        p.titles.append("ghost_title")
        assert manager.equip_title(p, "ghost_title") is True
        assert p.equipped_title == "ghost_title"

    def test_display_name_with_and_without_title(self):
        manager = TitleManager(registry=_stub_registry(_title("t1")))
        p = _player()
        assert manager.get_display_name(p) == "テスト冒険者"
        p.titles.append("t1")
        manager.equip_title(p, "t1")
        assert manager.get_display_name(p) == "テスト冒険者《二つ名t1》"

    def test_ui_list_flags(self):
        manager = TitleManager(registry=_stub_registry(
            _title("t1"), _title("t_hidden", hidden=True),
        ))
        p = _player()
        p.titles.append("t1")
        p.equipped_title = "t1"
        entries = {e["id"]: e for e in manager.get_title_list_for_ui(p)}
        owned = entries["t1"]
        assert owned["owned"] is True
        assert owned["equipped"] is True
        assert owned["hidden"] is False
        assert owned["message"] == "獲得！t1"
        hidden = entries["t_hidden"]
        assert hidden["owned"] is False
        assert hidden["equipped"] is False
        assert hidden["hidden"] is True
        assert hidden["message"] == "???"


class TestCheckAllTitles:
    def test_grants_only_met_conditions(self, title_registry, tmp_path):
        path = tmp_path / "titles.yaml"
        path.write_text(TITLE_CONDITIONS_YAML, encoding="utf-8")
        title_registry.load(str(path))
        manager = TitleManager(title_registry)

        p = _player(max_dungeon_depth=3, gold=50)
        granted = manager.check_all_titles(p)
        assert granted == ["t_depth"]
        assert "t_depth" in p.titles

        # second run grants nothing new
        assert manager.check_all_titles(p) == []

        # reaching the remaining condition grants the second title
        p.gold = 150
        assert manager.check_all_titles(p) == ["t_gold"]

    def test_skill_title_granted_at_level(self, title_registry, tmp_path):
        path = tmp_path / "titles.yaml"
        path.write_text(TITLE_CONDITIONS_YAML, encoding="utf-8")
        title_registry.load(str(path))
        manager = TitleManager(title_registry)

        p = _player()
        p.skills = {"magic": Skill("magic")}
        p.skills["magic"].level = 3
        assert manager.check_all_titles(p) == []
        p.skills["magic"].level = 4
        assert manager.check_all_titles(p) == ["t_magic"]


# ============================================================
# seasonal_systems.py — announcement / feedback / analytics / resources
# ============================================================


class TestEventAnnouncer:
    def test_outside_announcement_window(self):
        announcer = EventAnnouncer(announcement_period=100)
        result = announcer.build_announcement(
            {"id": "e1", "name": "夏祭り", "description": "説明"}, start_time=200, now=50
        )
        assert result == {
            "event_id": "e1",
            "name": "夏祭り",
            "teaser": "説明",
            "announced": False,
            "countdown_sec": 150,
            "theme": "夏祭り",
        }

    def test_within_announcement_window(self):
        announcer = EventAnnouncer(announcement_period=100)
        result = announcer.build_announcement({"id": "e1", "name": "n"}, start_time=200, now=150)
        assert result["announced"] is True
        assert result["countdown_sec"] == 50

    def test_after_start_countdown_zero(self):
        announcer = EventAnnouncer(announcement_period=100)
        result = announcer.build_announcement({"id": "e1", "name": "n"}, start_time=200, now=300)
        assert result["announced"] is True
        assert result["countdown_sec"] == 0

    def test_theme_falls_back_to_name(self):
        announcer = EventAnnouncer()
        themed = announcer.build_announcement(
            {"id": "e1", "name": "n", "theme": "冬"}, start_time=1000, now=0
        )
        assert themed["theme"] == "冬"

    def test_now_defaults_to_wall_clock(self):
        import time as _time

        announcer = EventAnnouncer(announcement_period=3600)
        result = announcer.build_announcement(
            {"id": "e1", "name": "n"}, start_time=_time.time() + 10
        )
        assert 0 <= result["countdown_sec"] <= 10
        assert result["announced"] is True

    def test_active_countdowns_skip_events_without_start(self):
        announcer = EventAnnouncer()
        events = {"with_start": {"id": "with_start", "name": "a"}, "no_start": {"id": "no_start", "name": "b"}}
        out = announcer.active_countdowns(events, {"with_start": 1000}, now=0)
        assert [item["event_id"] for item in out] == ["with_start"]


class TestEventFeedbackManager:
    def test_average_satisfaction_empty(self):
        assert EventFeedbackManager().average_satisfaction("e1") == 0.0

    def test_average_is_per_event(self):
        manager = EventFeedbackManager()
        manager.submit_survey("e1", 3, ["もっと敵を"])
        manager.submit_survey("e1", 5, [])
        manager.submit_survey("e2", 1, [])
        assert manager.average_satisfaction("e1") == 4.0
        assert manager.average_satisfaction("e2") == 1.0
        assert manager.average_satisfaction("e3") == 0.0

    def test_record_legend(self):
        manager = EventFeedbackManager()
        manager.record_legend("e1", "無双の勇者", "100体を倒した")
        assert manager._legends == [
            {"event_id": "e1", "title": "無双の勇者", "story": "100体を倒した"}
        ]


class TestEventAnalyticsManager:
    def test_participation_rate_counts_unique_players(self):
        manager = EventAnalyticsManager()
        manager.record(EventAction("e1", "alice", "kill"))
        manager.record(EventAction("e1", "alice", "kill"))
        manager.record(EventAction("e1", "bob", "kill"))
        manager.record(EventAction("e2", "alice", "kill"))
        assert manager.participation_rate("e1", 4) == 0.5
        assert manager.participation_rate("e2", 4) == 0.25
        assert manager.participation_rate("e_none", 4) == 0.0

    def test_participation_rate_zero_players(self):
        assert EventAnalyticsManager().participation_rate("e1", 0) == 0.0

    def test_reward_balance_empty(self):
        assert EventAnalyticsManager().reward_balance("e1") == {"avg": 0.0, "count": 0.0, "max": 0.0}

    def test_reward_balance_aggregates_only_rewards(self):
        manager = EventAnalyticsManager()
        manager.record(EventAction("e1", "a", "reward", value=1.0))
        manager.record(EventAction("e1", "b", "reward", value=3.0))
        manager.record(EventAction("e1", "c", "kill", value=99.0))
        manager.record(EventAction("e2", "d", "reward", value=100.0))
        assert manager.reward_balance("e1") == {"avg": 2.0, "count": 2.0, "max": 3.0}

    def test_event_action_defaults(self):
        action = EventAction("e1", "p", "join")
        assert action.value == 1.0


class TestEventResourceManager:
    def test_missing_file_yields_empty_manager(self, tmp_path):
        manager = EventResourceManager(str(tmp_path / "absent.yaml"))
        assert manager.get_events() == {}
        assert manager.validate_all() == []
        assert manager.reusable_assets("whatever") == {
            "id": "whatever", "story_triggers": [], "effects": {}, "modules": ["story", "effects", "rewards"],
        }

    def _manager_with_events(self, tmp_path):
        path = tmp_path / "world_events.yaml"
        path.write_text(
            yaml.dump(
                {
                    "world_events": {
                        "summer": {
                            "id": "summer",
                            "name": "夏祭り",
                            "description": "年に一度の祭り",
                            "story_triggers": ["arrival"],
                            "effects": {"gold": 10},
                        },
                        "broken": {"description": "id も name も無い"},
                    }
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        return EventResourceManager(str(path))

    def test_get_events(self, tmp_path):
        manager = self._manager_with_events(tmp_path)
        assert set(manager.get_events()) == {"summer", "broken"}

    def test_schema_compatible(self, tmp_path):
        manager = self._manager_with_events(tmp_path)
        events = manager.get_events()
        assert manager.schema_compatible(events["summer"]) is True
        assert manager.schema_compatible(events["broken"]) is False

    def test_validate_all_reports_incompatible(self, tmp_path):
        manager = self._manager_with_events(tmp_path)
        assert manager.validate_all() == ["broken: missing id/name"]

    def test_reusable_assets(self, tmp_path):
        manager = self._manager_with_events(tmp_path)
        assets = manager.reusable_assets("summer")
        assert assets["id"] == "summer"
        assert assets["story_triggers"] == ["arrival"]
        assert assets["effects"] == {"gold": 10}
        assert assets["modules"] == ["story", "effects", "rewards"]

    def test_load_replaces_previous_data(self, tmp_path):
        manager = self._manager_with_events(tmp_path)
        other = tmp_path / "other.yaml"
        other.write_text(yaml.dump({"world_events": {"winter": {"id": "winter", "name": "冬"}}}, allow_unicode=True), encoding="utf-8")
        manager.load(str(other))
        assert set(manager.get_events()) == {"winter"}
