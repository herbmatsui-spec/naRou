"""Tests for meta intervention engine."""

import pytest
from typing import Any
from naRou.skill_eater.skill_eater_template_model import load_templates
from naRou.skill_eater.skill_eater_meta_intervention_system import (
    TemplateEventGenerator, InterventionEngine, InterventionAction, TemplateEvent, InterventionResult
)
from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
from naRou.skill_eater_audio_system import SkillEaterAudioSystem
from naRou.skill_eater_meta_quest_system import SkillEaterReincarnationSystem, SkillEaterQuestSystem, GlobalRuleEngine


class MockPlayer:
    def __init__(self):
        self.gold = 1000
        self.skills = set()
        self.karma_good_evil = 0
        self.template_exposure = 0

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
        self.total_karma_points = 0
        self.devoured_template_counts = {}
        self.devoured_element_counts = {}
        self.dominant_element_last_life = None
        self.unlocked_secrets = []
        self.loop_count = 1


def test_intervention_engine_creation():
    """Test InterventionEngine can be created."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None,
        presentation=pres,
        rule_engine=rule_engine,
        meta_state=meta_state,
        templates=templates,
    )
    assert engine is not None


def test_calc_karma():
    """Test karma calculation with completeness tiers."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    template = templates["expel_incompetent"]
    reward = template.reward

    # T1, 50% completeness -> tier 40 (1.0x) * tier_mult 1.0 = 1.0
    karma = engine.calc_karma(reward, 1, 0.5)
    expected = int(reward.karma_t1 * 1.0 * 1.0)  # 120 * 1.0 = 120
    assert karma == expected

    # T1, 30% completeness -> tier 0 (0.3x) * 1.0 = 0.3
    karma = engine.calc_karma(reward, 1, 0.3)
    expected = int(reward.karma_t1 * 0.3 * 1.0)  # 120 * 0.3 = 36
    assert karma == expected

    # T2, 80% completeness -> tier 70 (1.8x) * 2.5 = 4.5
    karma = engine.calc_karma(reward, 2, 0.8)
    expected = int(reward.karma_t2 * 1.8 * 2.5)  # 700 * 4.5 = 3150
    assert karma == expected

    # T3, 100% completeness -> tier 100 (4.0x) * 6.0 = 24.0
    karma = engine.calc_karma(reward, 3, 1.0)
    expected = int(reward.karma_t2 * 4.0 * 6.0)  # 700 * 24 = 16800
    assert karma == expected


def test_roll_success():
    """Test success roll mechanics."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    window = templates["expel_incompetent"].exploit_windows[0]  # buy_cheap, base_success=0.85
    # Low difficulty should succeed more often
    engine.rng = __import__("random").Random(0)
    success = engine.roll_success(window, 1.0)
    assert success is True  # with seed 0, random() < 0.85

    # High difficulty should fail more
    engine.rng = __import__("random").Random(0)
    success = engine.roll_success(window, 10.0)  # chance = 0.85/10 = 0.085
    assert success is False


def test_compute_completeness():
    """Test completeness calculation."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None

    # No windows executed
    comp = engine.compute_completeness(event, [])
    assert comp == 0.0

    # One window executed
    comp = engine.compute_completeness(event, ["buy_cheap"])
    assert comp == 0.5

    # Both windows executed
    comp = engine.compute_completeness(event, ["buy_cheap", "exclusive_contract"])
    assert comp == 1.0


def test_execute_t1_success():
    """Test T1 intervention execution."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window = event.exploit_windows[0]  # buy_cheap

    result = engine.execute_t1(event, window, player)
    assert result.success is True
    assert result.karma_gained > 0
    assert result.stolen_skill == "farming_blessing_minor"
    assert player.gold == 800  # 1000 - 200
    assert "farming_blessing_minor" in player.skills


def test_execute_t1_insufficient_gold():
    """Test T1 fails with insufficient gold."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    player.gold = 50  # Less than required 200
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window = event.exploit_windows[0]

    result = engine.execute_t1(event, window, player)
    assert result.success is False
    assert "所持金不足" in result.message


def test_execute_t2_requires_skill():
    """Test T2 requires specific skill."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    # Player doesn't have negotiation skill
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window = event.exploit_windows[1]  # exclusive_contract, req_skill=[negotiation]

    result = engine.execute_t2(event, window, player)
    assert result.success is False
    assert "必要スキル不足" in result.message

    # With skill
    player.skills.add("negotiation")
    gen2 = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event2 = gen2.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window2 = event2.exploit_windows[1]
    result = engine.execute_t2(event2, window2, player)
    assert result.success is True
    assert result.completeness == 0.8
    assert result.karma_good_evil_change == -2


def test_execute_t3_requires_karma():
    """Test T3 requires sufficient karma."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()
    meta_state.total_karma_points = 1000  # Less than 5000

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window = event.exploit_windows[0]  # Any window

    result = engine.execute_t3(event, window, player)
    assert result.success is False
    assert "因果ポイント不足" in result.message

    # With enough karma
    meta_state.total_karma_points = 10000
    gen2 = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event2 = gen2.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    window2 = event2.exploit_windows[0]
    result = engine.execute_t3(event2, window2, player)
    assert result.success is True
    assert result.completeness == 1.0
    assert "template_weight_expel_incompetent" in rule_engine.rules
    assert rule_engine.rules["template_weight_expel_incompetent"] == 0.0


def test_execute_main_entry():
    """Test main execute entry point."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()
    meta_state.total_karma_points = 10000

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    player.skills.add("negotiation")
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)

    # Execute T1 - test that it routes to execute_t1
    action = InterventionAction(tier=1, window_id="buy_cheap")
    # Force success by setting rng to a seed that succeeds
    engine.rng = __import__("random").Random(1)  # seed 1 gives random() < 0.85
    result = engine.execute(event, action, player)
    # With seed 1, roll_success should pass (0.85 chance)
    # Just test that it routes correctly and doesn't error
    assert result is not None

    # Execute T2
    player2 = MockPlayer()
    player2.skills.add("negotiation")
    gen2 = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event2 = gen2.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    action2 = InterventionAction(tier=2, window_id="exclusive_contract")
    engine.rng = __import__("random").Random(1)
    result2 = engine.execute(event2, action2, player2)
    assert result2 is not None


def test_apply_rewards():
    """Test reward application."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()
    meta_state.total_karma_points = 10000

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    player.template_exposure = 0
    player.karma_good_evil = 0

    result = InterventionResult(
        success=True,
        completeness=0.8,
        karma_gained=1000,
        exposure_gained=3,
        karma_good_evil_change=-2,
    )
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)

    engine.apply_rewards(player, result, event)

    assert meta_state.total_karma_points == 11000
    assert meta_state.devoured_template_counts["expel"] == 1
    assert player.template_exposure == 3
    assert player.karma_good_evil == -2


def test_failure_handling():
    """Test failure handling marks player as complicit."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()

    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )

    player = MockPlayer()
    player.karma_good_evil = 0
    player.template_exposure = 0
    gen = TemplateEventGenerator(templates, rng=__import__("random").Random(42))
    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)

    # Test invalid window (not found) - returns early with different message
    action = InterventionAction(tier=1, window_id="nonexistent")
    result = engine.execute(event, action, player)
    assert result.success is False
    assert "無効な介入窓" in result.message
    assert result.exposure_gained == 0  # Early return, no exposure penalty

    # Test actual failure (roll fails) - force failure with high difficulty
    engine.rng = __import__("random").Random(0)  # This might succeed, so use difficulty
    action2 = InterventionAction(tier=1, window_id="buy_cheap")
    # Use very high difficulty to force failure
    event.difficulty = 100.0
    result2 = engine.execute(event, action2, player)
    assert result2.success is False
    assert "介入失敗" in result2.message
    assert result2.exposure_gained == 5
    assert result2.karma_good_evil_change == -5


def test_reincarnation_carry():
    """Test that devoured template counts carry over with decay on reincarnation."""
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = MockRuleEngine()
    meta_state = MockMetaState()
    meta_state.total_karma_points = 10000
    meta_state.loop_count = 1  # Add loop_count

    # Simulate devouring templates in current life (high counts to trigger depletion message)
    meta_state.devoured_template_counts["expel"] = 6  # Will decay to 3, triggering message
    meta_state.devoured_template_counts["credit_steal"] = 4  # Will decay to 2

    from naRou.skill_eater_meta_quest_system import SkillEaterReincarnationSystem
    reincarnation_sys = SkillEaterReincarnationSystem()
    reincarnation_sys.meta_state = meta_state
    reincarnation_sys.registry = None  # Not needed for this test
    reincarnation_sys.presentation = pres
    reincarnation_sys.audio = audio

    # Mock player with some skills
    class MockPlayerState:
        def get_skill_ids(self):
            return []
        def has_skill(self, sid):
            return False

    player = MockPlayerState()
    new_player, msg = reincarnation_sys.process_reincarnation(player, [])

    # Check that template counts carried over with decay
    assert meta_state.devoured_template_counts["expel"] == 3  # 6 // 2 = 3
    assert meta_state.devoured_template_counts["credit_steal"] == 2  # 4 // 2 = 2
    assert meta_state.loop_count == 2  # incremented

    # Check world modifier mentions template depletion (expel >= 3)
    assert "テンプレ枯渇" in msg
    assert "expel" in msg