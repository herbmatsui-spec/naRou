"""Coverage tests for skill_eater_meta_intervention_system (template events + intervention engine)."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from skill_eater_meta_intervention_system import (
    InterventionAction,
    InterventionEngine,
    InterventionResult,
    TemplateEvent,
    TemplateEventGenerator,
)
from skill_eater_template_model import (
    ExploitWindow,
    RouteStep,
    TemplateData,
    TemplateReward,
)


def _make_template(template_id="tpl_1", archetype="expel", contexts=("slum",), windows=None, reward=None) -> TemplateData:
    if windows is None:
        windows = [
            ExploitWindow(id="buy_cheap", tier=1, req_gold=100, req_skill=[], base_success=0.9),
            ExploitWindow(id="reverse_pride", tier=2, req_gold=0, req_skill=["analysis"], base_success=0.6),
        ]
    if reward is None:
        reward = TemplateReward(karma_t1=50, karma_t2=200, stealable_skill="stolen_skill")
    return TemplateData(
        id=template_id,
        archetype=archetype,
        contexts=list(contexts),
        faction_weight={"outlaw": 0.5},
        route_steps=[RouteStep(flag="f1", turn=1, actor="a", on_fail="fail")],
        exploit_windows=windows,
        reward=reward,
    )


def _make_player(gold=1000, skills=None):
    player = MagicMock()
    player.gold = gold
    player.skills = set(skills or [])
    player.karma_good_evil = 0
    player.template_exposure = 0

    def has_skill(s):
        return s in player.skills

    def add_skill(s):
        player.skills.add(s)

    player.has_skill.side_effect = has_skill
    player.add_skill.side_effect = add_skill
    return player


class TestDataclasses:
    def test_template_event(self) -> None:
        ev = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.5, route_steps=[], exploit_windows=[], turn_spawned=5,
        )
        assert ev.template_id == "tpl_1"
        assert ev.difficulty == 1.5
        assert ev.turn_spawned == 5

    def test_intervention_action(self) -> None:
        a = InterventionAction(tier=2, window_id="reverse_pride", params={"k": "v"})
        assert a.tier == 2
        assert a.window_id == "reverse_pride"
        assert a.params == {"k": "v"}

    def test_intervention_result(self) -> None:
        r = InterventionResult(success=True, completeness=0.8, karma_gained=100, stolen_skill="s1")
        assert r.success is True
        assert r.completeness == 0.8
        assert r.karma_gained == 100
        assert r.stolen_skill == "s1"
        assert r.unique_skill_granted is None
        assert r.exposure_gained == 0


class TestTemplateEventGenerator:
    def setup_method(self) -> None:
        self.templates = {
            "tpl_1": _make_template("tpl_1", "expel", ["slum"]),
            "tpl_2": _make_template("tpl_2", "betray", ["guild"]),
        }
        self.gen = TemplateEventGenerator(self.templates, rng=None)

    def test_weighted_choice(self) -> None:
        import random

        rng = random.Random(1)
        gen = TemplateEventGenerator({}, rng=rng)
        choice = gen._weighted_choice([("a", 0.0), ("b", 1.0)])
        assert choice == "b"

    def test_weighted_choice_zero_total(self) -> None:
        import random

        rng = random.Random(1)
        gen = TemplateEventGenerator({}, rng=rng)
        assert gen._weighted_choice([("a", 0.0), ("b", 0.0)]) == "b"

    def test_find_template(self) -> None:
        tpl = self.gen._find_template("expel", "slum")
        assert tpl is not None
        assert tpl.id == "tpl_1"
        assert self.gen._find_template("nope", "slum") is None
        assert self.gen._find_template("expel", "nowhere") is None

    def test_build_route_and_extract_windows(self) -> None:
        tpl = self.templates["tpl_1"]
        assert self.gen.build_route(tpl) == tpl.route_steps
        assert self.gen.extract_windows(tpl) == tpl.exploit_windows

    def test_compute_difficulty(self) -> None:
        windows = [
            ExploitWindow(id="w1", tier=1, base_success=0.5),
            ExploitWindow(id="w2", tier=1, base_success=0.25),
        ]
        diff = self.gen.compute_difficulty(windows, loop_count=1)
        expected = ((1.0 / 0.5) + (1.0 / 0.25)) / 2
        assert diff == pytest.approx(expected)

    def test_compute_difficulty_empty(self) -> None:
        assert self.gen.compute_difficulty([], loop_count=1) == 1.0

    def test_compute_difficulty_loop_mod(self) -> None:
        windows = [ExploitWindow(id="w1", tier=1, base_success=0.5)]
        d1 = self.gen.compute_difficulty(windows, loop_count=1)
        d2 = self.gen.compute_difficulty(windows, loop_count=2)
        assert d2 < d1

    def test_maybe_spawn_no_spawn(self) -> None:
        gen = TemplateEventGenerator(self.templates, rng=None)
        # rng.random() returns ~0.84 > default spawn_chance 0.5 -> None
        result = gen.maybe_spawn("slum", 10)
        assert result is None

    def test_maybe_spawn_forced(self) -> None:
        import random

        gen = TemplateEventGenerator(self.templates, rng=random.Random(0.0))
        event = gen.maybe_spawn("slum", 10, spawn_chance=1.0)
        assert event is not None
        assert event.context == "slum"
        assert event.turn_spawned == 10
        assert event.archetype in ("expel", "betray", "credit_steal", "genius_discrimination")
        assert len(gen.active_events) == 1

    def test_maybe_spawn_unknown_context_fallback(self) -> None:
        import random

        gen = TemplateEventGenerator(self.templates, rng=random.Random(0.0))
        event = gen.maybe_spawn("unknown_ctx", 10, spawn_chance=1.0)
        # Falls back to default expel/outlaw weights; template not found -> None
        assert event is None

    def test_context_weights_keys(self) -> None:
        assert "slum" in self.gen.context_weights
        assert "guild" in self.gen.context_weights
        assert "noble_quarter" in self.gen.context_weights
        assert "dungeon_entrance" in self.gen.context_weights


class TestInterventionEngine:
    def setup_method(self) -> None:
        self.templates = {"tpl_1": _make_template()}
        self.registry = MagicMock()
        self.presentation = MagicMock()
        self.rule_engine = MagicMock()
        self.meta_state = MagicMock()
        self.meta_state.total_karma_points = 10000
        self.meta_state.devoured_template_counts = {}
        self.engine = InterventionEngine(
            registry=self.registry,
            presentation=self.presentation,
            rule_engine=self.rule_engine,
            meta_state=self.meta_state,
            templates=self.templates,
        )
        self.player = _make_player(gold=5000, skills=["analysis"])

    def test_tier_multipliers(self) -> None:
        assert InterventionEngine.TIER_MULTIPLIERS == {1: 1.0, 2: 2.5, 3: 6.0}

    def test_roll_success(self) -> None:
        window = ExploitWindow(id="w", tier=1, base_success=0.5)
        engine = InterventionEngine(None, None, None, None, rng=None)
        # rng.random() ~0.84; chance = 0.5/1.0 = 0.5 -> False
        assert engine.roll_success(window, 1.0) is False
        engine.rng = None  # force fresh? skip deterministic check
        # Use seeded RNG for True
        import random

        engine2 = InterventionEngine(None, None, None, None, rng=random.Random(0.0))
        assert engine2.roll_success(window, 1.0) is True  # 0.0 < 0.5

    def test_compute_completeness(self) -> None:
        event = TemplateEvent(
            template_id="t", archetype="a", context="c", faction="f",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="w1", tier=1), ExploitWindow(id="w2", tier=1)],
            turn_spawned=0,
        )
        assert self.engine.compute_completeness(event, []) == 0.0
        assert self.engine.compute_completeness(event, ["w1"]) == 0.5
        assert self.engine.compute_completeness(event, ["w1", "w2"]) == 1.0

    def test_compute_completeness_no_windows(self) -> None:
        event = TemplateEvent(
            template_id="t", archetype="a", context="c", faction="f",
            difficulty=1.0, route_steps=[], exploit_windows=[], turn_spawned=0,
        )
        assert self.engine.compute_completeness(event, []) == 1.0

    def test_calc_karma(self) -> None:
        reward = TemplateReward(karma_t1=100, karma_t2=200)
        assert self.engine.calc_karma(reward, 1, 0.0) == 30  # threshold 0 -> mult 0.3
        assert self.engine.calc_karma(reward, 1, 0.4) == 100  # 40 >= 40 -> mult 1.0
        assert self.engine.calc_karma(reward, 1, 0.5) == 250  # 50 >= 40 -> mult 1.0? check: sorted thresholds
        # COMPLETENESS_TIERS: 0:0.3, 40:1.0, 70:1.8, 90:2.6, 100:4.0
        # completeness 0.5 -> 50 >= 40 -> mult 1.0 -> 100*1*1 = 100
        assert self.engine.calc_karma(reward, 1, 0.5) == 100
        assert self.engine.calc_karma(reward, 2, 1.0) == 200 * 4.0 * 2.5  # 2000
        assert self.engine.calc_karma(reward, 3, 1.0, ) == 200 * 4.0 * 6.0  # 4800

    def test_execute_invalid_window(self) -> None:
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="w1", tier=1)], turn_spawned=0,
        )
        action = InterventionAction(tier=1, window_id="nope")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "無効な介入窓" in result.message

    def test_execute_tier_insufficient(self) -> None:
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="buy_cheap", tier=2)], turn_spawned=0,
        )
        action = InterventionAction(tier=1, window_id="buy_cheap")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "Tier 2" in result.message

    def test_execute_t1_success(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)  # always success
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="buy_cheap", tier=1, req_gold=100)], turn_spawned=0,
        )
        action = InterventionAction(tier=1, window_id="buy_cheap")
        result = self.engine.execute(event, action, self.player)
        assert result.success is True
        assert result.completeness == 0.5
        assert result.stolen_skill == "stolen_skill"
        self.player.add_skill.assert_called_with("stolen_skill")
        assert self.player.gold == 4900

    def test_execute_t1_insufficient_gold(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        self.player.gold = 10
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="buy_cheap", tier=1, req_gold=100)], turn_spawned=0,
        )
        action = InterventionAction(tier=1, window_id="buy_cheap")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "所持金不足" in result.message

    def test_execute_t2_success(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        target = MagicMock()
        target.scenario_flags = {"expel_flag": 1}
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="reverse_pride", tier=2, req_skill=["analysis"])],
            turn_spawned=0,
        )
        event.target_npc = target
        action = InterventionAction(tier=2, window_id="reverse_pride")
        result = self.engine.execute(event, action, self.player)
        assert result.success is True
        assert result.completeness == 0.8
        assert result.karma_good_evil_change == -2

    def test_execute_t2_missing_skill(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        self.player.skills = set()
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="reverse_pride", tier=2, req_skill=["analysis"])],
            turn_spawned=0,
        )
        action = InterventionAction(tier=2, window_id="reverse_pride")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "必要スキル不足" in result.message

    def test_execute_t3_success(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        self.rule_engine.override_rule.return_value = (True, "ok", 5000)
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="erase", tier=3)], turn_spawned=0,
        )
        action = InterventionAction(tier=3, window_id="erase")
        result = self.engine.execute(event, action, self.player)
        assert result.success is True
        assert result.completeness == 1.0
        assert result.exposure_gained == 10

    def test_execute_t3_insufficient_karma(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        self.meta_state.total_karma_points = 100
        self.rule_engine.override_rule.return_value = (False, "因果ポイント不足", 0)
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="erase", tier=3)], turn_spawned=0,
        )
        action = InterventionAction(tier=3, window_id="erase")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "因果ポイント不足" in result.message

    def test_execute_invalid_tier(self) -> None:
        import random

        self.engine.rng = random.Random(0.0)
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="w1", tier=1)], turn_spawned=0,
        )
        action = InterventionAction(tier=9, window_id="w1")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert "無効なTier" in result.message

    def test_execute_roll_failure(self) -> None:
        import random

        self.engine.rng = random.Random(0.99)  # high -> failure
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[],
            exploit_windows=[ExploitWindow(id="buy_cheap", tier=1, base_success=0.1)], turn_spawned=0,
        )
        action = InterventionAction(tier=1, window_id="buy_cheap")
        result = self.engine.execute(event, action, self.player)
        assert result.success is False
        assert result.completeness == 0.0

    def test_handle_failure(self) -> None:
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[], exploit_windows=[], turn_spawned=0,
        )
        player = _make_player()
        result = self.engine._handle_failure(event, player)
        assert result.success is False
        assert result.exposure_gained == 5
        assert result.karma_good_evil_change == -5
        assert player.karma_good_evil == -5
        assert player.template_exposure == 5

    def test_apply_rewards_success(self) -> None:
        self.meta_state.total_karma_points = 0
        result = InterventionResult(
            success=True, completeness=0.8, karma_gained=100, exposure_gained=3,
            karma_good_evil_change=-2, unique_skill_granted="unique_skill",
        )
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[], exploit_windows=[], turn_spawned=0,
        )
        player = _make_player()
        self.engine.apply_rewards(player, result, event)
        assert self.meta_state.total_karma_points == 100
        assert self.meta_state.devoured_template_counts["expel"] == 1
        assert player.template_exposure == 3
        assert player.karma_good_evil == -2
        player.add_skill.assert_called_with("unique_skill")
        self.presentation.add_event.assert_called_once()

    def test_apply_rewards_failure_no_op(self) -> None:
        result = InterventionResult(success=False, completeness=0.0, karma_gained=0)
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[], exploit_windows=[], turn_spawned=0,
        )
        player = _make_player()
        self.engine.apply_rewards(player, result, event)
        assert self.meta_state.total_karma_points == 0

    def test_apply_rewards_low_completeness_no_unique_skill(self) -> None:
        result = InterventionResult(
            success=True, completeness=0.5, karma_gained=50, unique_skill_granted="unique_skill",
        )
        event = TemplateEvent(
            template_id="tpl_1", archetype="expel", context="slum", faction="outlaw",
            difficulty=1.0, route_steps=[], exploit_windows=[], turn_spawned=0,
        )
        player = _make_player()
        self.engine.apply_rewards(player, result, event)
        player.add_skill.assert_not_called()
