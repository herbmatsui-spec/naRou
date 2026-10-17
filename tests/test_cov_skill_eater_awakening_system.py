"""Coverage tests for skill_eater_awakening_system (DevourAwakeningManager)."""

from __future__ import annotations

import pytest

from skill_eater_awakening_system import DevourAwakeningManager, Phase1MidBoss


@pytest.fixture
def mgr() -> DevourAwakeningManager:
    return DevourAwakeningManager()


class TestPhase1MidBoss:
    def test_defaults(self) -> None:
        boss = Phase1MidBoss()
        assert boss.boss_id == "MIDAS_ELITE_ENFORCER"
        assert boss.hp == 4000
        assert boss.max_hp == 4000
        assert boss.is_defeated is False


class TestInitialState:
    def test_fresh_manager(self, mgr: DevourAwakeningManager) -> None:
        assert mgr.devour_unlocked is False
        assert mgr.is_time_stopped is False
        assert mgr.phase1_completed is False
        assert mgr.boss.is_defeated is False


class TestNearDeathTimeStop:
    def test_triggers_below_10_percent(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.check_near_death_time_stop(300, 4000)
        assert res["triggered"] is True
        assert res["action"] == "TIME_STOP_RED_SCREEN"
        assert mgr.is_time_stopped is True

    def test_exactly_10_percent_triggers(self, mgr: DevourAwakeningManager) -> None:
        # 400 * 0.1 = 40 -> int() で 40、hp <= 40 なので発動
        res = mgr.check_near_death_time_stop(40, 4000)
        assert res["triggered"] is True

    def test_no_trigger_above_threshold(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.check_near_death_time_stop(401, 4000)
        assert res == {"triggered": False}
        assert mgr.is_time_stopped is False

    def test_no_trigger_after_devour_unlocked(self, mgr: DevourAwakeningManager) -> None:
        mgr.unlock_devour_command()
        res = mgr.check_near_death_time_stop(1, 4000)
        assert res == {"triggered": False}
        assert mgr.is_time_stopped is False


class TestGlitchFrames:
    def test_three_frames_returned(self, mgr: DevourAwakeningManager) -> None:
        frames = mgr.trigger_meta_system_error_glitch()
        assert len(frames) == 3
        assert [f["frame"] for f in frames] == [1, 2, 3]
        assert frames[0]["color"] == "RED"
        assert "喰らう者" in frames[2]["text"]


class TestDevourUnlockAndKill:
    def test_unlock_devour_command_payload(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.unlock_devour_command()
        assert res["command"] == "DEVOUR"
        assert res["action"] == "FORCE_COMMAND_UNLOCK"
        assert mgr.devour_unlocked is True

    def test_execute_kill_before_unlock_fails(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.execute_devour_kill()
        assert res == {"success": False, "error": "DEVOUR_NOT_UNLOCKED"}
        assert mgr.boss.hp == 4000

    def test_execute_kill_defeats_boss(self, mgr: DevourAwakeningManager) -> None:
        mgr.check_near_death_time_stop(100, 4000)
        mgr.unlock_devour_command()
        res = mgr.execute_devour_kill()
        assert res["success"] is True
        assert res["damage"] == 99999
        assert res["target_defeated"] is True
        assert res["stolen_skill"] == "ユニークスキル《重圧魔導砲》"
        assert mgr.boss.hp == 0
        assert mgr.boss.is_defeated is True
        assert mgr.is_time_stopped is False


class TestFanfare:
    def test_fanfare_presentation(self, mgr: DevourAwakeningManager) -> None:
        fx = mgr.get_awakening_fanfare_presentation()
        assert fx["action"] == "FANFARE_AWAKENING"
        assert fx["screen_effect"] == "RED_GOLD_BURST"
        assert fx["sound"].endswith(".ogg")


class TestPhaseTransition:
    def test_transition_with_existing_state(self, mgr: DevourAwakeningManager) -> None:
        world_state = {"world_id": "old", "keep_me": True}
        res = mgr.complete_phase1_transition(world_state)
        assert res["success"] is True
        assert res["next_phase"].startswith("Phase 2")
        assert world_state["world_id"] == "skill_eater"
        assert world_state["template_id"] == "skill_capitalism"
        assert world_state["phase_index"] == 2
        assert world_state["phase1_completed"] is True
        assert world_state["keep_me"] is True
        assert mgr.phase1_completed is True

    def test_transition_with_none_creates_state(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.complete_phase1_transition(None)
        assert res["success"] is True


class TestSaveStateExport:
    def test_export_without_defeat(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.export_phase1_save_state()
        save = res["save_data"]
        assert save["phase1_completed"] is True
        assert save["current_phase"] == 2
        assert save["devour_unlocked"] is False
        assert "acquired_skills" not in save

    def test_export_with_defeat_appends_stolen_skill(self, mgr: DevourAwakeningManager) -> None:
        mgr.unlock_devour_command()
        mgr.execute_devour_kill()
        res = mgr.export_phase1_save_state()
        assert res["save_data"]["acquired_skills"] == ["ユニークスキル《重圧魔導砲》"]

    def test_export_into_existing_save_no_dupes(self, mgr: DevourAwakeningManager) -> None:
        mgr.unlock_devour_command()
        mgr.execute_devour_kill()
        existing = {"acquired_skills": ["ユニークスキル《重圧魔導砲》"], "gold": 100}
        res = mgr.export_phase1_save_state(existing)
        save = res["save_data"]
        assert save["acquired_skills"] == ["ユニークスキル《重圧魔導砲》"]
        assert save["gold"] == 100

    def test_export_into_none_creates_new_dict(self, mgr: DevourAwakeningManager) -> None:
        res = mgr.export_phase1_save_state(None)
        assert res["success"] is True
        assert res["save_data"]["current_phase"] == 2
