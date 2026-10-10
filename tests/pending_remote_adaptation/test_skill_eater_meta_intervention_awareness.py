"""Tests for meta intervention awareness system."""

import pytest
from naRou.meta_awareness_system import MetaAwarenessSystem
from naRou.karma_system import REGISTRY
from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
from naRou.skill_eater.skill_eater_template_model import load_templates
from dataclasses import dataclass


@dataclass
class MockEntity:
    karma_law_chaos: int = 0
    karma_good_evil: int = 0
    template_exposure: int = 0


class DummyTarget:
    def __init__(self, flags):
        self.scenario_flags = flags


def test_awareness_singleton():
    """Test singleton behavior."""
    a1 = MetaAwarenessSystem.get_instance()
    a2 = MetaAwarenessSystem.get_instance()
    assert a1 is a2


def test_get_reading_depth():
    """Test reading depth calculation."""
    ms = MetaAwarenessSystem.get_instance()
    ms.awareness_level = 1
    assert ms.get_reading_depth() == 1
    ms.awareness_level = 3
    assert ms.get_reading_depth() == 2
    ms.awareness_level = 6
    assert ms.get_reading_depth() == 3


def test_trigger_template_scan():
    """Test template flag detection."""
    ms = MetaAwarenessSystem.get_instance()
    target = DummyTarget({"expel": 0.7, "betray": 0.2, "credit_steal": 0.5})
    detected = ms.trigger_template_scan(target)
    assert len(detected) == 2
    archetypes = {d["archetype"] for d in detected}
    assert "expel" in archetypes
    assert "credit_steal" in archetypes
    assert "betray" not in archetypes  # below threshold


def test_get_exploit_windows():
    """Test exploit window filtering by depth."""
    ms = MetaAwarenessSystem.get_instance()

    class MockWindow:
        def __init__(self, tier):
            self.tier = tier

    template = type("T", (), {"exploit_windows": [MockWindow(1), MockWindow(2), MockWindow(3)]})()

    assert len(ms.get_exploit_windows(template, 1)) == 1
    assert len(ms.get_exploit_windows(template, 2)) == 2
    assert len(ms.get_exploit_windows(template, 3)) == 3


def test_apply_deep_read_cost():
    """Test deep read applies karma/exposure cost."""
    REGISTRY.load()  # ensure actions exist
    ms = MetaAwarenessSystem.get_instance()
    player = MockEntity()
    initial_lc = player.karma_law_chaos
    initial_exp = player.template_exposure

    ms.apply_deep_read_cost(player, 3)
    assert player.karma_law_chaos == initial_lc - 1
    assert player.template_exposure == initial_exp + 1

    # Depth < 3 should not apply cost
    player2 = MockEntity()
    ms.apply_deep_read_cost(player2, 2)
    assert player2.karma_law_chaos == 0
    assert player2.template_exposure == 0


def test_trigger_template_scan_emits_event():
    """Test that scan emits presentation event."""
    REGISTRY.load()
    ms = MetaAwarenessSystem.get_instance()
    pres = SkillEaterPresentationSystem(is_mock_only=True)
    target = DummyTarget({"expel": 0.8})

    detected = ms.trigger_template_scan(target, presentation=pres)
    assert len(detected) == 1

    events = pres.get_and_clear_events()
    assert len(events) == 1
    evt = events[0]
    assert evt.event_type == "secret_discover"
    assert "テンプレ反応検出" in evt.message
    assert "expel" in evt.message


def test_trigger_template_scan_no_event_when_no_flags():
    """Test no event emitted when no flags detected."""
    ms = MetaAwarenessSystem.get_instance()
    pres = SkillEaterPresentationSystem(is_mock_only=True)
    target = DummyTarget({"betray": 0.2})  # below threshold

    detected = ms.trigger_template_scan(target, presentation=pres)
    assert len(detected) == 0

    events = pres.get_and_clear_events()
    assert len(events) == 0


def test_awareness_template_integration():
    """Test awareness works with real template data."""
    REGISTRY.load()
    ms = MetaAwarenessSystem.get_instance()
    templates = load_templates("data/templates")
    assert "expel_incompetent" in templates

    template = templates["expel_incompetent"]
    # Mock target with the template's archetype flag
    target = DummyTarget({"expel": 0.7})

    detected = ms.trigger_template_scan(target)
    assert len(detected) == 1
    assert detected[0]["archetype"] == "expel"

    # Check exploit windows at different depths
    windows_1 = ms.get_exploit_windows(template, 1)
    windows_2 = ms.get_exploit_windows(template, 2)
    assert len(windows_1) == 1
    assert len(windows_2) == 2
    assert windows_1[0].id == "buy_cheap"
    assert windows_2[1].id == "exclusive_contract"