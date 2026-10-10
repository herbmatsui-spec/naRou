"""Integration test for full meta intervention loop: scan -> intervene -> reward -> reincarnate."""

from typing import Any

import pytest
from naRou.skill_eater.skill_eater_template_model import load_templates
from naRou.skill_eater.skill_eater_meta_intervention_system import (
    TemplateEventGenerator,
    InterventionEngine,
    InterventionAction,
    TemplateEvent,
)
from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
from naRou.skill_eater_audio_system import SkillEaterAudioSystem
from naRou.skill_eater_meta_quest_system import (
    SkillEaterReincarnationSystem,
    SkillEaterQuestSystem,
    GlobalRuleEngine,
    ReincarnationMetaState,
)
from naRou.meta_awareness_system import MetaAwarenessSystem


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


class MockRuleEngine:
    def __init__(self):
        self.rules = {}

    def override_rule(self, rule_name: str, value: Any, cost_type: str = "KARMA", available_karma: int = 10000) -> tuple[bool, str, int]:
        self.rules[rule_name] = value
        return True, f"Rule {rule_name} set to {value}", 0


class MockMetaState:
    def __init__(self):
        self.total_karma_points = 10000
        self.devoured_template_counts = {}
        self.devoured_element_counts = {}
        self.dominant_element_last_life = None
        self.unlocked_secrets = []
        self.loop_count = 1


def test_full_intervention_loop():
    """Test complete loop: template spawn -> scan -> intervene -> reward -> reincarnate."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    # 1. Create generator and spawn template event
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", current_turn=10, loop_count=1, spawn_chance=1.0)
    assert event is not None
    assert event.template_id == "expel_incompetent"

    # 2. Create intervention engine
    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    # 3. Create player with required skills for T2
    player = MockPlayer()
    player.skills.add("negotiation")

    # 4. Scan with awareness (simulates original text view)
    awareness = MetaAwarenessSystem.get_instance()
    awareness.awareness_level = 6  # Max level for full reading
    target = type("Target", (), {"scenario_flags": {"expel": 0.8}})()
    detected = awareness.trigger_template_scan(target, presentation=pres)
    assert len(detected) == 1
    assert detected[0]["archetype"] == "expel"

    # 5. Execute T2 intervention (structural hijack)
    action = InterventionAction(tier=2, window_id="exclusive_contract")
    engine.rng = __import__("random").Random(1)  # Force success
    result = engine.execute(event, action, player)

    assert result.success is True
    assert result.completeness == 0.8
    assert result.karma_gained > 0
    # T2 doesn't grant stolen skill, only T1 does

    # 6. Apply rewards
    engine.apply_rewards(player, result, event)
    assert meta_state.total_karma_points > 10000
    assert meta_state.devoured_template_counts["expel"] == 1
    assert player.template_exposure > 0
    assert player.karma_good_evil < 0  # T2 reduces good_evil

    # 7. Reincarnation with template count carry-over
    from naRou.skill_eater_meta_quest_system import SkillEaterReincarnationSystem
    reincarnation_sys = SkillEaterReincarnationSystem()
    reincarnation_sys.meta_state = meta_state
    reincarnation_sys.registry = None
    reincarnation_sys.presentation = pres
    reincarnation_sys.audio = audio

    class MockPlayerState:
        def get_skill_ids(self):
            return []
        def has_skill(self, sid):
            return False

    player_state = MockPlayerState()
    new_player, msg = reincarnation_sys.process_reincarnation(player_state, [])

    # Verify carry-over with decay
    assert meta_state.loop_count == 2
    assert meta_state.devoured_template_counts["expel"] == 1  # 1 -> 1 (min 1)
    assert "テンプレ枯渇" not in msg  # Only 1, not >= 3

    print("✓ Full intervention loop test passed!")


def test_t3_ontological_intervention():
    """Test T3 ontological intervention erases template from world."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()
    meta_state.total_karma_points = 10000

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)

    player = MockPlayer()

    # T3 requires massive karma
    action = InterventionAction(tier=3, window_id="buy_cheap")
    engine.rng = __import__("random").Random(1)
    result = engine.execute(event, action, player)

    assert result.success is True
    assert result.completeness == 1.0
    assert "template_weight_expel_incompetent" in rule_engine.rules
    assert rule_engine.rules["template_weight_expel_incompetent"] == 0.0

    engine.apply_rewards(player, result, event)
    assert meta_state.total_karma_points > 10000
    assert player.template_exposure >= 10

    print("✓ T3 ontological intervention test passed!")


def test_exposure_penalty():
    """Test that high exposure increases difficulty and risk."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    player.template_exposure = 80  # High exposure

    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)

    # High exposure should make intervention riskier (via karma system)
    action = InterventionAction(tier=1, window_id="buy_cheap")
    engine.rng = __import__("random").Random(1)
    result = engine.execute(event, action, player)

    assert result.success is True
    # Exposure increases in apply_rewards
    engine.apply_rewards(player, result, event)
    assert player.template_exposure > 80

    print("✓ Exposure penalty test passed!")


if __name__ == "__main__":
    test_full_intervention_loop()
    test_t3_ontological_intervention()
    test_exposure_penalty()
    print("\n🎉 All integration tests passed!")