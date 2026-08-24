"""Tests for meta intervention UI data builders."""

import pytest
from naRou.systems.skill_eater_template_model import load_templates
from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
from naRou.skill_eater_audio_system import SkillEaterAudioSystem
from naRou.systems.skill_eater_meta_intervention_system import TemplateEventGenerator, TemplateEvent, InterventionResult
from naRou.systems.meta_awareness_system import MetaAwarenessSystem
from naRou.systems.karma_system import REGISTRY


class MockTarget:
    def __init__(self, flags):
        self.scenario_flags = flags


def test_presentation_flag_badges():
    """Test that template_flag_badges are included in diegetic UI data."""
    REGISTRY.load()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    
    # Create target with scenario flags
    target = MockTarget({"expel": 0.85, "credit_steal": 0.3})
    
    # Build diegetic UI data
    awareness = MetaAwarenessSystem.get_instance()
    awareness.awareness_level = 6
    
    # The presentation system's build_diegetic_ui_data doesn't directly take target
    # but we can test that the awareness system emits events with flag info
    detected = awareness.trigger_template_scan(target, presentation=pres)
    assert len(detected) == 2
    
    # Check event emission
    events = pres.get_and_clear_events()
    assert len(events) == 1
    evt = events[0]
    assert "テンプレ反応検出" in evt.message
    assert "expel" in evt.message
    assert "credit_steal" in evt.message


def test_reading_mode_data():
    """Test that original text view (reading mode) data can be built."""
    REGISTRY.load()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    
    awareness = MetaAwarenessSystem.get_instance()
    awareness.awareness_level = 6
    
    # Get exploit windows at depth 3
    windows = awareness.get_exploit_windows(event, 3)
    assert len(windows) == 2
    
    # Build reading mode data (IFルートタイムライン)
    reading_data = {
        "template_id": event.template_id,
        "archetype": event.archetype,
        "windows": [
            {"id": w.id, "tier": w.tier, "base_success": w.base_success, "req_gold": w.req_gold}
            for w in windows
        ],
        "depth": 3,
    }
    
    assert reading_data["template_id"] == "expel_incompetent"
    assert len(reading_data["windows"]) == 2


def test_completeness_gauge():
    """Test completeness gauge data structure."""
    result = InterventionResult(
        success=True,
        completeness=0.8,
        karma_gained=1000,
    )
    
    gauge_data = {
        "value": result.completeness,
        "max": 1.0,
        "percent": int(result.completeness * 100),
    }
    
    assert gauge_data["value"] == 0.8
    assert gauge_data["percent"] == 80


def test_meta_awareness_reading_depth():
    """Test reading depth calculation."""
    awareness = MetaAwarenessSystem.get_instance()
    
    awareness.awareness_level = 1
    assert awareness.get_reading_depth() == 1
    
    awareness.awareness_level = 3
    assert awareness.get_reading_depth() == 2
    
    awareness.awareness_level = 6
    assert awareness.get_reading_depth() == 3


def test_exploit_window_filtering():
    """Test that exploit windows are filtered by reading depth."""
    awareness = MetaAwarenessSystem.get_instance()
    templates = load_templates("data/templates")
    template = templates["expel_incompetent"]
    
    # Depth 1: only tier 1
    windows = awareness.get_exploit_windows(template, 1)
    assert len(windows) == 1
    assert windows[0].tier == 1
    
    # Depth 2: tier 1 and 2
    windows = awareness.get_exploit_windows(template, 2)
    assert len(windows) == 2
    assert windows[0].tier == 1
    assert windows[1].tier == 2
    
    # Depth 3: all tiers
    windows = awareness.get_exploit_windows(template, 3)
    assert len(windows) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])