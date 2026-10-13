"""
Tests for missed_opportunity_system.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from missed_opportunity_system import MissedOpportunity, MissedOpportunitySystem


def test_missed_opportunity_creation():
    """Test that a MissedOpportunity can be created."""
    opp = MissedOpportunity(
        opportunity_id="opp1",
        quest_id="quest1",
        reason="time_limit",
        timestamp=1234567890.0,
        penalty={"gold": -100}
    )

    assert opp.opportunity_id == "opp1"
    assert opp.quest_id == "quest1"
    assert opp.reason == "time_limit"
    assert opp.timestamp == 1234567890.0
    assert opp.penalty == {"gold": -100}


def test_missed_opportunity_system_record():
    """Test recording a missed opportunity."""
    system = MissedOpportunitySystem()
    initial_count = len(system._missed_opportunities)

    system.record_missed_opportunity(
        opportunity_id="opp2",
        quest_id="quest2",
        reason="event_end",
        timestamp=9876543210.0,
        penalty={"reputation": -10}
    )

    assert len(system._missed_opportunities) == initial_count + 1
    opp = system._missed_opportunities[-1]
    assert opp.opportunity_id == "opp2"
    assert opp.quest_id == "quest2"
    assert opp.reason == "event_end"
    assert opp.timestamp == 9876543210.0
    assert opp.penalty == {"reputation": -10}


def test_missed_opportunity_system_record_default_timestamp():
    """Test recording with default timestamp (should use current time)."""
    system = MissedOpportunitySystem()
    import time
    before = time.time()
    system.record_missed_opportunity(
        opportunity_id="opp3",
        quest_id="quest3",
        reason="player_death"
    )
    after = time.time()

    assert len(system._missed_opportunities) == 1
    opp = system._missed_opportunities[0]
    assert opp.opportunity_id == "opp3"
    assert opp.quest_id == "quest3"
    assert opp.reason == "player_death"
    assert before <= opp.timestamp <= after


if __name__ == "__main__":
    test_missed_opportunity_creation()
    test_missed_opportunity_system_record()
    test_missed_opportunity_system_record_default_timestamp()
    print("All tests passed!")
