"""Coverage tests for skill_eater_epilogue (EpilogueAndTransitionManager)."""

from __future__ import annotations

import pytest

from skill_eater_epilogue import EpilogueAndTransitionManager


@pytest.fixture
def mgr() -> EpilogueAndTransitionManager:
    return EpilogueAndTransitionManager()


class TestDefaults:
    def test_initial_state(self, mgr: EpilogueAndTransitionManager) -> None:
        assert mgr.global_account_artifacts == []
        assert mgr.is_world_a_closed is False
        assert mgr.transition_event_triggered is False


class TestEpilogueStory:
    def test_zero_donation_independent_ending(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_epilogue_story({"Combat": 10, "Recovery": 5, "Production": 3}, donated_count=0)
        assert res["epilogue_completed"] is True
        assert "【過酷なる独立】" in res["epilogue_story"]
        assert "NPC一同" in res["npc_farewell"]

    def test_combat_dominant_ending(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_epilogue_story({"Combat": 100, "Recovery": 5, "Production": 3}, donated_count=2)
        assert "【覇道の鉄塞】" in res["epilogue_story"]
        assert "バルバロッサ" in res["npc_farewell"]

    def test_recovery_dominant_ending(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_epilogue_story({"Combat": 5, "Recovery": 100, "Production": 3}, donated_count=2)
        assert "【博愛の聖域】" in res["epilogue_story"]
        assert "シスター・エレナ" in res["npc_farewell"]

    def test_production_dominant_ending(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_epilogue_story({"Combat": 5, "Recovery": 3, "Production": 100}, donated_count=2)
        assert "【理知の魔導都市】" in res["epilogue_story"]
        assert "技術長クラフト" in res["npc_farewell"]

    def test_dominant_tie_picks_first_max_key(self, mgr: EpilogueAndTransitionManager) -> None:
        # max() is stable: first key with max value wins
        res = mgr.generate_epilogue_story({"Combat": 10, "Recovery": 10}, donated_count=2)
        assert "【覇道の鉄塞】" in res["epilogue_story"]


class TestRemnantArtifact:
    def test_generates_registered_artifact(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_remnant_artifact()
        assert res["success"] is True
        art = res["artifact"]
        assert art["artifact_id"] == "art_broken_golden_coin"
        assert art["origin_world"].startswith("W4")
        assert "+10%" in art["passive_effect"]
        assert mgr.global_account_artifacts == [art]
        assert "REMNANT ARTIFACT" in res["message"]

    def test_bosses_defeated_parameter_ignored_but_accepted(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.generate_remnant_artifact(bosses_defeated=0)
        assert res["success"] is True

    def test_multiple_artifacts_accumulate(self, mgr: EpilogueAndTransitionManager) -> None:
        mgr.generate_remnant_artifact()
        mgr.generate_remnant_artifact()
        assert len(mgr.global_account_artifacts) == 2


class TestWorldTransition:
    def test_default_transition(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.trigger_world_transition()
        assert res["success"] is True
        assert res["world_a_closed"] is True
        assert res["target_world"] == "W1_Magic_Dominant"
        assert res["phase5_completed"] is True
        assert res["game_loop_status"] == "NEXT_WORLD_INITIALIZATION_READY"
        assert mgr.is_world_a_closed is True
        assert mgr.transition_event_triggered is True

    def test_custom_target_world(self, mgr: EpilogueAndTransitionManager) -> None:
        res = mgr.trigger_world_transition("W7_Clockwork_Steam")
        assert res["target_world"] == "W7_Clockwork_Steam"
        assert "[W7_Clockwork_Steam]" in res["transition_log"]

    def test_transition_log_structure(self, mgr: EpilogueAndTransitionManager) -> None:
        log = mgr.trigger_world_transition()["transition_log"]
        lines = log.split("\n")
        assert lines[0] == "=================================================="
        assert lines[-1] == "=================================================="
        assert any("次元ゲート開放" in ln for ln in lines)
