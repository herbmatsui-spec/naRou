"""
Test suite for Elona Masterpiece Edition (v2.0)
Validates DataManager, AdvancedAISystem, and Canvas Web API data serialization.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ai_system import TACTIC_AGGRESSIVE, AdvancedAISystem
from constants import QUALITY_GOD
from data_manager import DataManager
from game import Engine


def test_data_manager_item_generation():
    dm = DataManager()
    item = dm.create_item("longsword", quality=QUALITY_GOD, material="rubynus")
    assert item.name == "長剣"
    assert item.quality == QUALITY_GOD
    assert item.material == "rubynus"
    assert item.hit_bonus >= 8  # God quality bonus


def test_data_manager_monster_generation():
    dm = DataManager()
    mob = dm.create_monster("minotaur", level_scale=3)
    assert "ミノタウロス" in mob.name
    assert mob.max_hp > 95  # Scaled with level_scale
    assert mob.ai_type == "aggressive"


def test_data_manager_schema_validation():
    dm = DataManager()
    errors = dm.validate_all_data()
    assert len(errors) == 0, f"Data validation errors: {errors}"


def test_advanced_ai_system_integration():
    engine = Engine()
    ai_sys = engine.ai_system
    assert isinstance(ai_sys, AdvancedAISystem)

    # Test pet AI tactic change
    engine.pet.tactic = TACTIC_AGGRESSIVE
    ai_sys.process_ai(engine.pet, engine)
    assert engine.pet.tactic == TACTIC_AGGRESSIVE


def test_web_server_canvas_state_serialization():
    from web_server import GameHTTPRequestHandler

    engine = Engine()
    handler = GameHTTPRequestHandler.__new__(GameHTTPRequestHandler)
    state = handler._serialize_engine_state(engine)

    assert "player" in state
    assert "light_sources" in state
    assert len(state["light_sources"]) >= 1
    assert "light_map" in state
    assert "quests" in state
    assert "inventory" in state
    assert len(state["inventory"]) > 0
