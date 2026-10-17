from __future__ import annotations

"""Tests for Seasonal Proposals 6-9."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seasonal_systems import (
    EventAction,
    EventAnalyticsManager,
    EventAnnouncer,
    EventFeedbackManager,
    EventResourceManager,
)


# 提案6: announcement
def test_announcement():
    a = EventAnnouncer(announcement_period=10)
    ev = {"id": "blood_moon", "name": "血の月", "description": "teaser"}
    # start 5s away -> within announcement period
    ann = a.build_announcement(ev, start_time=100, now=95)
    assert ann["announced"] is True
    assert ann["countdown_sec"] == 5
    # start far away -> not announced
    ann2 = a.build_announcement(ev, start_time=1000, now=95)
    assert ann2["announced"] is False
    print("PASS: event announcement + countdown")


# 提案7: feedback
def test_feedback():
    mgr = EventFeedbackManager()
    mgr.submit_survey("blood_moon", 4, ["more rewards"])
    mgr.submit_survey("blood_moon", 2, ["too hard"])
    assert mgr.average_satisfaction("blood_moon") == 3.0
    mgr.record_legend("blood_moon", "紅月の戦い", "伝説の記録")
    assert len(mgr._legends) == 1
    print("PASS: event feedback + legend")


# 提案8: analytics
def test_analytics():
    mgr = EventAnalyticsManager()
    mgr.record(EventAction("blood_moon", "p1", "join"))
    mgr.record(EventAction("blood_moon", "p2", "join"))
    mgr.record(EventAction("blood_moon", "p1", "reward", 10.0))
    mgr.record(EventAction("blood_moon", "p2", "reward", 20.0))
    assert abs(mgr.participation_rate("blood_moon", 2) - 1.0) < 1e-9
    bal = mgr.reward_balance("blood_moon")
    assert bal["avg"] == 15.0 and bal["max"] == 20.0
    print("PASS: event analytics participation + balance")


# 提案9: resource reuse
def test_resource_reuse():
    mgr = EventResourceManager()
    events = mgr.get_events()
    assert "blood_moon" in events
    assert mgr.validate_all() == []
    res = mgr.reusable_assets("blood_moon")
    assert "story" in res["modules"]
    # backward compat: event missing extra fields but has id/name is valid
    assert mgr.schema_compatible({"id": "x", "name": "X"})
    print("PASS: event resource reuse + schema compat")


if __name__ == "__main__":
    test_announcement()
    test_feedback()
    test_analytics()
    test_resource_reuse()
    print("\nALL SEASONAL SYSTEM TESTS PASSED")
