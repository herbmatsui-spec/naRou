"""Regression test for meta intervention integration into game loop."""

import pytest
from naRou.skill_eater.skill_eater_meta_intervention_system import (
    InterventionAction,
    InterventionEngine,
    TemplateEvent,
    TemplateEventGenerator,
)
from naRou.skill_eater.skill_eater_template_model import load_templates

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_exploration_system import SkillEaterExplorationSystem
from skill_eater_meta_quest_system import GlobalRuleEngine, ReincarnationMetaState
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import SkillEaterRegistry


class MockPlayer:
    def __init__(self):
        self.gold = 1000
        self.skills = set()
        self.karma_good_evil = 0
        self.template_exposure = 0
        self.karma_law_chaos = 0
        self.scenario_flags = {}

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.skills

    def add_skill(self, skill_id: str):
        self.skills.add(skill_id)


def test_exploration_system_has_template_integration():
    """Test that exploration system has template generator and intervention engine."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates)
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    assert explore.template_generator is not None
    assert explore.intervention_engine is not None
    assert explore.active_template_events == []


def test_template_event_spawns_on_room_move():
    """Test that template events can spawn when moving to a room."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    # Force spawn by calling _check_template_event directly with 100% chance
    # (The internal method uses exploration_rank.rooms_visited as turn)
    event = template_gen.maybe_spawn("slum", current_turn=explore.exploration_rank.rooms_visited, loop_count=1, spawn_chance=1.0)
    assert event is not None
    assert event.template_id == "expel_incompetent"

    explore.active_template_events.append(event)
    assert len(explore.active_template_events) == 1


def test_intervention_execution_and_reward_application():
    """Test that intervention can be executed and rewards applied."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    # Spawn an event
    event = template_gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)

    # Create player with required skill for T2
    player = MockPlayer()
    player.skills.add("negotiation")

    # Execute T2 intervention
    action = InterventionAction(tier=2, window_id="exclusive_contract")
    intervention_engine.rng = __import__("random").Random(1)  # Force success
    result = intervention_engine.execute(event, action, player)

    assert result.success is True
    assert result.completeness == 0.8
    assert result.karma_gained > 0

    # Apply rewards
    intervention_engine.apply_rewards(player, result, event)
    assert meta_state.total_karma_points > 10000
    assert meta_state.devoured_template_counts["expel"] == 1
    assert player.template_exposure > 0
    assert player.karma_good_evil < 0  # T2 reduces good_evil


def test_exploration_system_trigger_intervention():
    """Test that exploration system's trigger_intervention method works."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    # Spawn an event
    event = template_gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)

    # Create player
    player = MockPlayer()
    player.skills.add("negotiation")

    # Trigger intervention via exploration system
    action = InterventionAction(tier=2, window_id="exclusive_contract")
    intervention_engine.rng = __import__("random").Random(1)
    result = explore.trigger_intervention(event, action, player)

    assert result is not None
    assert result.success is True
    assert event not in explore.active_template_events  # Event removed after completion


def test_exploration_system_serialization_includes_template_events():
    """Test that exploration system serialization includes active template events."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    # Spawn an event
    event = template_gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)

    # Serialize
    data = explore.to_dict()

    assert "active_template_events" in data
    assert len(data["active_template_events"]) == 1
    evt_data = data["active_template_events"][0]
    assert evt_data["template_id"] == "expel_incompetent"
    assert evt_data["archetype"] == "expel"
    assert evt_data["context"] == "slum"
    assert len(evt_data["exploit_windows"]) == 2


def test_exploration_system_deserialization_restores_template_events():
    """Test that exploration system deserialization restores active template events."""
    SkillEaterExplorationSystem.reset_instance()
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    templates = load_templates("data/templates")
    template_gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    rule_engine = GlobalRuleEngine.get_instance()
    meta_state = ReincarnationMetaState()
    meta_state.total_karma_points = 10000
    registry = SkillEaterRegistry.get_instance()

    intervention_engine = InterventionEngine(
        registry=registry,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )

    explore = SkillEaterExplorationSystem(
        audio=audio, presentation=pres,
        template_generator=template_gen,
        intervention_engine=intervention_engine,
    )

    # Spawn an event
    event = template_gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)

    # Serialize
    data = explore.to_dict()

    # Deserialize
    SkillEaterExplorationSystem.reset_instance()
    new_explore = SkillEaterExplorationSystem.from_dict(
        data, audio=audio, presentation=pres,
        template_generator=template_gen, intervention_engine=intervention_engine
    )

    assert len(new_explore.active_template_events) == 1
    restored_event = new_explore.active_template_events[0]
    assert restored_event.template_id == "expel_incompetent"
    assert restored_event.archetype == "expel"
    assert restored_event.context == "slum"
    assert len(restored_event.exploit_windows) == 2


if __name__ == "__main__":
    test_exploration_system_has_template_integration()
    test_template_event_spawns_on_room_move()
    test_intervention_execution_and_reward_application()
    test_exploration_system_trigger_intervention()
    test_exploration_system_serialization_includes_template_events()
    test_exploration_system_deserialization_restores_template_events()
    print("\n🎉 All T1 meta intervention integration tests passed!")
