import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from game import Engine
from ui_fx_systems import TutorialManager


def test_tutorial_manager_loading_and_triggers():
    tm = TutorialManager("data/tutorial_guides.yaml")
    assert len(tm.guides) >= 5
    assert "welcome_start" in tm.guides
    completed = set()
    guide = tm.check_triggers("game_start", completed)
    assert guide is not None
    assert guide.id == "welcome_start"
    completed.add("welcome_start")
    guide2 = tm.check_triggers("game_start", completed)
    assert guide2 is None


def test_engine_tutorial_and_notification_flow():
    eng = Engine()
    assert "welcome_start" in eng.player.completed_tutorials
    eng.player.hp = 1
    eng.check_tutorial_triggers("hp_below_50")
    assert "first_low_hp" in eng.player.completed_tutorials
    assert len(eng.notification_manager.active_notifications) > 0


def test_screen_shake_and_log_levels():
    eng = Engine()
    assert not eng.screen_shake.is_active
    eng.screen_shake.trigger(intensity=1.5, duration=3)
    assert eng.screen_shake.is_active
    eng.screen_shake.update()
    eng.screen_shake.update()
    eng.screen_shake.update()
    assert not eng.screen_shake.is_active
    eng.log("Normal info", level="INFO")
    eng.log("Level up!", level="SUCCESS")
    eng.log("Danger!", level="WARNING")
    recent = eng.msg_log.get_recent(3)
    assert recent[0].level == "INFO"
    assert recent[1].level == "SUCCESS"
    assert recent[2].level == "WARNING"


def test_web_server_serialization():
    eng = Engine()
    if eng.web_server:
        from web_server import GameHTTPRequestHandler

        h = GameHTTPRequestHandler.__new__(GameHTTPRequestHandler)
        state = h._serialize_engine_state(eng)
        assert "logs" in state
        assert "floating_notification" in state
        assert "screen_shake" in state
        assert isinstance(state["logs"], list)
