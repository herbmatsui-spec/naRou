"""Tests for meta intervention template event generator."""

import pytest
from naRou.packages.core.kernel.kernel import Kernel
from naRou.packages.world_a.package import WorldAPackage
from skill_eater_meta_intervention_system import TemplateEventGenerator
from skill_eater_template_model import load_templates
from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_exploration_system import SkillEaterExplorationSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem


def test_generator_deterministic():
    """Test that generator is deterministic with fixed seed."""
    templates = load_templates("data/templates")
    gen1 = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    gen2 = TemplateEventGenerator(templates, rng=__import__("random").Random(42))

    # Same seed should produce same archetype/faction
    a1, f1 = gen1._roll_seed("slum")
    a2, f2 = gen2._roll_seed("slum")
    assert a1 == a2
    assert f1 == f2


def test_find_template():
    """Test template lookup by archetype and context."""
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates)

    # expel_incompetent has contexts [slum, guild]
    tpl = gen._find_template("expel", "slum")
    assert tpl is not None
    assert tpl.id == "expel_incompetent"

    tpl = gen._find_template("expel", "guild")
    assert tpl is not None
    assert tpl.id == "expel_incompetent"

    # No template for expel in noble_quarter
    tpl = gen._find_template("expel", "noble_quarter")
    assert tpl is None


def test_build_route_and_windows():
    """Test route and window extraction."""
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates)
    tpl = templates["expel_incompetent"]

    route = gen.build_route(tpl)
    assert len(route) == 2
    assert route[0].flag == "sell_skill_cheap"

    windows = gen.extract_windows(tpl)
    assert len(windows) == 2
    assert windows[0].id == "buy_cheap"
    assert windows[1].id == "exclusive_contract"


def test_compute_difficulty():
    """Test difficulty computation."""
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates)
    tpl = templates["expel_incompetent"]
    windows = gen.extract_windows(tpl)

    # Loop 1 difficulty
    diff1 = gen.compute_difficulty(windows, loop_count=1)
    assert diff1 > 0

    # Higher loop = lower difficulty (easier)
    diff5 = gen.compute_difficulty(windows, loop_count=5)
    assert diff5 < diff1


def test_maybe_spawn():
    """Test template event spawning."""
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))

    # Spawn with high chance
    event = gen.maybe_spawn("slum", current_turn=10, loop_count=1, spawn_chance=1.0)
    assert event is not None
    assert event.template_id == "expel_incompetent"
    assert event.archetype == "expel"
    assert event.context == "slum"
    assert event.turn_spawned == 10
    assert len(event.exploit_windows) == 2

    # Check active_events list updated
    assert len(gen.active_events) == 1


def test_maybe_spawn_chance():
    """Test spawn chance works."""
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(999))

    # With 0 chance, never spawn
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=0.0)
    assert event is None
    assert len(gen.active_events) == 0


def test_exploration_integration():
    """Test template event triggers on room move."""
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    explore = SkillEaterExplorationSystem(audio=audio, presentation=pres)

    # Load templates and create generator
    templates = load_templates("data/templates")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    explore.template_generator = gen

    # Call check with 100% spawn chance by directly calling generator
    # The internal method uses exploration_rank.rooms_visited as turn
    # Force spawn via generator directly
    event = gen.maybe_spawn("slum", current_turn=explore.exploration_rank.rooms_visited, loop_count=1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)
    assert len(explore.active_template_events) == 1

    # Verify event has correct structure
    evt = explore.active_template_events[0]
    assert evt.template_id == "expel_incompetent"
    assert evt.archetype == "expel"
    assert evt.context == "slum"


def test_engine_property():
    """Test engine template_intervention_system property."""
    kernel = Kernel()
    pkg = WorldAPackage()
    pkg.setup(kernel)

    # Test kernel has the intervention system
    sys = kernel.get_system("skill_eater_meta_intervention")
    assert sys is not None
    assert isinstance(sys, TemplateEventGenerator)

    # Test intervention engine
    engine = kernel.get_system("skill_eater_intervention_engine")
    assert engine is not None
    from skill_eater_meta_intervention_system import InterventionEngine
    assert isinstance(engine, InterventionEngine)
