"""Coverage tests for skill_eater_pursuer_system (HoundSpawnManager)."""

from __future__ import annotations

import pytest

from skill_eater_pursuer_system import HoundSpawnManager, MidasHoundPursuer


@pytest.fixture
def mgr() -> HoundSpawnManager:
    return HoundSpawnManager()


class TestPursuerDefaults:
    def test_hound_defaults(self) -> None:
        hound = MidasHoundPursuer()
        assert hound.hound_id == "HOUND_UNIT_09"
        assert hound.level == 20
        assert hound.vision_range == 2
        assert hound.alert_level == "NORMAL"
        assert hound.patrol_points == [(5, 5), (5, 2), (2, 2), (2, 5)]

    def test_manager_defaults(self, mgr: HoundSpawnManager) -> None:
        assert mgr.is_spawned is False
        assert mgr.player_is_hidden is False
        assert mgr.hiding_spots == [(1, 1), (8, 2)]


class TestSpawn:
    def test_spawn_at_custom_pos(self, mgr: HoundSpawnManager) -> None:
        res = mgr.spawn_hound((3, 3))
        assert res["action"] == "HOUND_SPAWNED"
        assert res["pos"] == (3, 3)
        assert mgr.is_spawned is True
        assert mgr.hound.alert_level == "NORMAL"


class TestPatrolAndDetect:
    def test_no_detection_before_spawn(self, mgr: HoundSpawnManager) -> None:
        res = mgr.update_hound_patrol_and_detect((5, 5))
        assert res == {"detected": False}

    def test_patrol_advances_when_normal(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((5, 5))
        res = mgr.update_hound_patrol_and_detect((50, 50))
        assert res["detected"] is False
        # index 0 -> 1 に進む
        assert mgr.hound.patrol_index == 1
        assert mgr.hound.pos == (5, 2)

    def test_patrol_wraps_around(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound()
        mgr.hound.patrol_index = 3
        mgr.update_hound_patrol_and_detect((50, 50))
        assert mgr.hound.patrol_index == 0
        assert mgr.hound.pos == (5, 5)

    def test_combat_detection_in_vision_range(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((5, 5))
        # spawn 後パトロールが1つ進み pos=(5,2)。同ターンで距離0
        res = mgr.update_hound_patrol_and_detect((5, 2))
        assert res["detected"] is True
        assert res["alert_level"] == "COMBAT"
        assert mgr.hound.alert_level == "COMBAT"

    def test_hearing_detection_when_running(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((5, 5))
        # パトロール後 pos=(5,2)、player=(5,4): dist=2、走行で聴覚探知が視界判定に先行
        res = mgr.update_hound_patrol_and_detect((5, 4), is_running=True)
        assert res["detected"] is True
        assert res["alert_level"] == "SUSPICIOUS"
        assert res["reason"] == "足音を探知された！"

    def test_walking_outside_vision_not_detected(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((5, 5))
        # パトロール後 pos=(5,2)、player=(5,5): dist=3 > vision_range=2
        res = mgr.update_hound_patrol_and_detect((5, 5), is_running=False)
        assert res["detected"] is False

    def test_hidden_player_never_detected(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((5, 5))
        mgr.interact_with_hiding_spot((1, 1))
        res = mgr.update_hound_patrol_and_detect((5, 5), is_running=True)
        assert res["detected"] is False
        assert res["alert_level"] == "NORMAL"


class TestAlertIndicator:
    def test_indicator_normal(self, mgr: HoundSpawnManager) -> None:
        assert mgr.render_hound_alert_indicator()["color"] == "GREEN"

    def test_indicator_suspicious(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound()
        mgr.hound.alert_level = "SUSPICIOUS"
        res = mgr.render_hound_alert_indicator()
        assert res["icon"] == "❓"
        assert res["color"] == "YELLOW_CAUTION"

    def test_indicator_combat(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound()
        mgr.hound.alert_level = "COMBAT"
        res = mgr.render_hound_alert_indicator()
        assert res["icon"] == "‼️"
        assert res["color"] == "RED_ALERT"


class TestHiding:
    def test_hide_at_valid_spot(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound()
        mgr.hound.alert_level = "SUSPICIOUS"
        res = mgr.interact_with_hiding_spot((8, 2))
        assert res["success"] is True
        assert res["hidden"] is True
        assert mgr.player_is_hidden is True
        assert mgr.hound.alert_level == "NORMAL"

    def test_hide_at_invalid_spot(self, mgr: HoundSpawnManager) -> None:
        res = mgr.interact_with_hiding_spot((9, 9))
        assert res == {"success": False, "error": "NOT_A_HIDING_SPOT"}
        assert mgr.player_is_hidden is False


class TestDefeatAndOverlays:
    def test_defeat_hound_with_trap(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound()
        res = mgr.defeat_hound_with_trap()
        assert res["success"] is True
        assert res["reward_skill"] == "SKILL_SHADOW_STEP_COMPLETE"
        assert mgr.hound.hp == 0
        assert mgr.is_spawned is False

    def test_highlight_routes_payload(self, mgr: HoundSpawnManager) -> None:
        mgr.spawn_hound((2, 5))
        res = mgr.highlight_hound_routes()
        assert res["hound_pos"] == (2, 5)
        assert res["patrol_line"] == [(5, 5), (5, 2), (2, 2), (2, 5)]
        assert res["danger_radius"] == 2
        assert res["hearing_radius"] == 3
        assert res["overlay_color"] == "RED_SCAN_CONE"

    def test_chase_event_payload(self, mgr: HoundSpawnManager) -> None:
        res = mgr.trigger_hound_chase_event()
        assert res["action"] == "CHASE_SEQUENCE_START"
        assert res["countdown_seconds"] == 10
        assert res["bgm"].endswith(".ogg")
