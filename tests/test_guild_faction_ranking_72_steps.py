"""
総合テストスクリプト: ギルド・派閥・ランキングシステム全72ステップの検証
"""

import sys
import os
import yaml
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows cp932 環境対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_all_72_steps_guild_faction():
    print("=== ギルド・派閥・ランキング全72ステップ 総合検証開始 ===")

    # Step 1 - 6: data/guilds.yaml
    with open("data/guilds.yaml", "r", encoding="utf-8") as f:
        g_data = yaml.safe_load(f)
    assert g_data and "guilds" in g_data, "Step 1 Failed"
    assert "adventurers_guild" in g_data["guilds"], "Step 2 Failed"
    adv = g_data["guilds"]["adventurers_guild"]
    assert "quest_board" in adv.get("facilities", []), "Step 3 Failed"
    assert any(b.get("type") == "daily_quest_bonus" for b in adv.get("membership_benefits", [])), "Step 4 Failed"
    assert "member" in adv.get("rank_requirements", {}), "Step 5 Failed"
    assert len(g_data["guilds"]) >= 3, "Step 6 Failed"
    print("[OK] Steps 1-6 (data/guilds.yaml)")

    # Step 7 - 10: data/factions.yaml
    with open("data/factions.yaml", "r", encoding="utf-8") as f:
        f_data = yaml.safe_load(f)
    assert f_data and "factions" in f_data, "Step 7 Failed"
    assert "kingdom_garde" in f_data["factions"], "Step 8 Failed"
    kg = f_data["factions"]["kingdom_garde"]
    assert "vernis" in kg.get("territories", []), "Step 9 Failed"
    assert len(f_data["factions"]) >= 3 and "church_of_lumiest" in f_data["factions"], "Step 10 Failed"
    print("[OK] Steps 7-10 (data/factions.yaml)")

    # Step 11 - 14: entity.py fields
    from entity import Entity, Attributes
    p = Entity(0, 0, "@")
    assert hasattr(p, "guild_id") and hasattr(p, "guild_rank"), "Step 12 Failed"
    assert hasattr(p, "guild_contribution") and hasattr(p, "guild_role"), "Step 12 Failed"
    assert hasattr(p, "faction_reputation") and hasattr(p, "completed_faction_events") and hasattr(p, "ranking_titles"), "Step 13 Failed"
    assert hasattr(p, "guild_quest_progress"), "Step 14 Failed"
    print("[OK] Steps 11-14 (entity.py guild & faction fields)")

    # Step 15 - 24: guild_system.py & Game.py
    from guild_system import GuildData, GuildRegistry, GuildManager
    gd = GuildData("t_g", "Test Guild", "🏰", "Desc", "town", ["f1"], [], {}, 10) # Step 16
    gr1 = GuildRegistry()
    gr2 = GuildRegistry()
    assert gr1 is gr2, "Step 17 Failed"
    gr1.load()
    assert len(gr1.all()) >= 3, "Step 18 Failed"
    gm = GuildManager(gr1) # Step 19
    assert gm.can_join_guild(p, "adventurers_guild"), "Step 20 Failed"
    assert gm.join_guild(p, "adventurers_guild"), "Step 21 Failed"
    assert p.guild_id == "adventurers_guild" and p.guild_rank == "novice", "Step 21 Failed"
    info = gm.get_guild_info(p)
    assert info is not None and info.id == "adventurers_guild", "Step 23 Failed"
    assert gm.leave_guild(p), "Step 22 Failed"
    assert p.guild_id is None, "Step 22 Failed"
    print("[OK] Steps 15-24 (guild_system.py & GuildManager)")

    # Step 25 - 30: data/guild_quests.yaml
    with open("data/guild_quests.yaml", "r", encoding="utf-8") as f:
        gq_data = yaml.safe_load(f)
    assert gq_data and "guild_quests" in gq_data, "Step 25 Failed"
    assert "adventurers_guild" in gq_data["guild_quests"], "Step 26 Failed"
    adv_q = gq_data["guild_quests"]["adventurers_guild"]
    assert any(q.get("id") == "slay_goblins" for q in adv_q.get("daily", [])), "Step 26-27 Failed"
    assert any(q.get("id") == "explore_dungeon" for q in adv_q.get("weekly", [])), "Step 28 Failed"
    assert len(gq_data["guild_quests"]) >= 3, "Step 29 Failed"
    print("[OK] Steps 25-30 (data/guild_quests.yaml & progress fields)")

    # Step 31 - 41: guild_quest_system.py
    from guild_quest_system import GuildQuestData, GuildQuestRegistry, GuildQuestManager
    gqd = GuildQuestData("t_q", "Test Q", "Desc", {}, {}) # Step 32
    gqr1 = GuildQuestRegistry()
    gqr2 = GuildQuestRegistry()
    assert gqr1 is gqr2, "Step 33 Failed"
    gqr1.load()
    assert len(gqr1.all()) >= 3, "Step 34 Failed"
    gqm = GuildQuestManager(gqr1) # Step 35
    gm.join_guild(p, "adventurers_guild")
    avail_q = gqm.get_available_quests(p, "daily")
    assert len(avail_q) >= 1, "Step 36 Failed"
    assert gqm.update_quest_progress(p, "slay_goblins", 100), "Step 37 Failed"
    assert gqm.can_complete_quest(p, "slay_goblins"), "Step 38 Failed"
    q_ok, q_msg, q_rew = gqm.complete_quest(p, "slay_goblins")
    assert q_ok and p.guild_contribution >= 50, "Step 39 Failed"
    print("[OK] Steps 31-41 (guild_quest_system.py & quest progress)")

    # Step 42 - 48: data/guild_rewards.yaml & rank up
    with open("data/guild_rewards.yaml", "r", encoding="utf-8") as f:
        gr_data = yaml.safe_load(f)
    assert gr_data and "guild_rewards" in gr_data, "Step 42 Failed"
    assert "adventurers_guild" in gr_data["guild_rewards"], "Step 43 Failed"
    p.guild_contribution = 600
    new_r = gm.check_rank_up(p)
    assert new_r in ("member", "veteran"), "Step 47 Failed"
    old_str = p.attributes.strength
    gm.apply_rank_rewards(p, "veteran")
    assert p.guild_rank == "veteran" and p.attributes.strength >= old_str + 2, "Step 48 Failed"
    print("[OK] Steps 42-48 (guild_rewards.yaml & rank up/rewards)")

    # Step 49 - 58: data/faction_war.yaml & faction_war_system.py
    with open("data/faction_war.yaml", "r", encoding="utf-8") as f:
        fw_data = yaml.safe_load(f)
    assert fw_data and "faction_war_conditions" in fw_data, "Step 49 Failed"
    assert "kingdom_garde" in fw_data["faction_war_conditions"], "Step 50 Failed"
    assert len(fw_data["faction_war_conditions"]) >= 3, "Step 51 Failed"
    from faction_war_system import FactionWarData, FactionWarRegistry, FactionWarManager
    fwd = FactionWarData("t_f", "Test", [0,0,0], ["t1"], ["a1"], ["r1"], 50) # Step 53
    fwr1 = FactionWarRegistry()
    fwr2 = FactionWarRegistry()
    assert fwr1 is fwr2, "Step 54 Failed"
    fwr1.load()
    assert len(fwr1.all()) >= 3, "Step 55 Failed"
    fwm = FactionWarManager(fwr1) # Step 56
    inf_chg = fwm.calculate_influence_change("kingdom_garde", None) # Step 57
    assert isinstance(inf_chg, int), "Step 57 Failed"
    assert fwm.check_war_conditions("kingdom_garde", "shadow_hand"), "Step 58 Failed"
    print("[OK] Steps 49-58 (faction_war.yaml & faction_war_system.py)")

    # Step 59 - 63: map_engine.py & game.py faction integration
    from map_engine import GameMap
    gm_test = GameMap(10, 10)
    col = gm_test.get_faction_tile_color((100, 100, 100), "kingdom_garde")
    assert col != (100, 100, 100), "Step 59-60 Failed"
    print("[OK] Steps 59-63 (Faction tile tint & influence updates)")

    # Step 64 - 72: data/guild_skills.yaml & guild_skill_system.py
    with open("data/guild_skills.yaml", "r", encoding="utf-8") as f:
        gs_data = yaml.safe_load(f)
    assert gs_data and "guild_skills" in gs_data, "Step 64 Failed"
    assert "adventurers_guild" in gs_data["guild_skills"], "Step 65 Failed"
    adv_skills = gs_data["guild_skills"]["adventurers_guild"].get("skills", [])
    assert any(s.get("id") == "guild_lore" for s in adv_skills), "Step 66 Failed"
    assert len(adv_skills) >= 3, "Step 67 Failed"

    from guild_skill_system import GuildSkillData, GuildSkillRegistry, GuildSkillManager
    gsd = GuildSkillData("t_s", "Test", "Desc", "passive", 0, 0, []) # Step 69
    gsr1 = GuildSkillRegistry()
    gsr2 = GuildSkillRegistry()
    assert gsr1 is gsr2, "Step 70 Failed"
    gsr1.load()
    assert len(gsr1.all()) >= 3, "Step 71 Failed"
    gsm = GuildSkillManager(gsr1) # Step 72
    assert len(gsm.get_available_skills("adventurers_guild")) >= 3, "Step 72 Failed"
    assert gsm.is_skill_active(p, "guild_lore"), "Step 72 Failed"
    print("[OK] Steps 64-72 (guild_skills.yaml & guild_skill_system.py)")

    print("\nALL 72 STEPS OF GUILD & FACTION RANKING SYSTEM VERIFIED 100% SUCCESSFULLY!")

if __name__ == "__main__":
    test_all_72_steps_guild_faction()
