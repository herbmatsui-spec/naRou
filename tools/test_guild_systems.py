"""Tests for Guild/Faction Proposals 6-9."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guild_systems import (
    GuildRoleManager, GuildWarManager, GuildWarState,
    RankingTitleManager, FactionEventManager,
)


class FakePlayer:
    def __init__(self):
        self.ranking_titles = []
        self.faction_reputation = {}
        self.completed_faction_events = []


# 提案6: roles
def test_role_permissions():
    mgr = GuildRoleManager()
    assert mgr.has_permission("guildmaster", "kick_members")
    assert not mgr.has_permission("member", "kick_members")
    assert mgr.has_permission("officer", "withdraw_funds")
    assert mgr.can_promote("member", "elder")
    assert not mgr.can_promote("member", "guildmaster")
    print("PASS: guild role permissions")


# 提案7: wars
def test_war_victory():
    mgr = GuildWarManager()
    st = GuildWarState(attacker="A", defender="B", eliminations=50,
                       territory=["derphy"], quest_progress=10)
    assert mgr.is_victory(st)
    st.quest_progress = 0
    assert not mgr.is_victory(st)
    mgr.form_alliance(st, "C")
    assert "C" in st.allied_with
    print("PASS: guild war victory check")


# 提案8: ranking titles
def test_ranking_titles():
    mgr = RankingTitleManager()
    p = FakePlayer()
    t = mgr.grant_title(p, "individual", 1)
    assert t == "world_champion"
    assert "world_champion" in p.ranking_titles
    effects = mgr.aggregate_effects(p)
    assert effects["stat_bonus"].get("strength") == 10
    assert effects["bonuses"].get("drop_rate_bonus") == 0.5
    print("PASS: ranking titles grant + aggregate")


# 提案9: faction events
def test_faction_events():
    mgr = FactionEventManager()
    p = FakePlayer()
    p.faction_reputation = {"church_of_lumiest": 80}
    avail = mgr.available_events("church_of_lumiest", p.faction_reputation)
    ids = {e["id"] for e in avail}
    assert "heresy_trial" in ids
    result = mgr.complete_event(p, "church_of_lumiest", "heresy_trial", "innocent")
    assert "skill_unlock" in [r["type"] for r in result["rewards"]]
    assert p.faction_reputation["church_of_lumiest"] == 100
    assert "shadow_hand" in p.faction_reputation
    print("PASS: faction event available + complete")


if __name__ == "__main__":
    test_role_permissions()
    test_war_victory()
    test_ranking_titles()
    test_faction_events()
    print("\nALL GUILD/FACTION TESTS PASSED")
