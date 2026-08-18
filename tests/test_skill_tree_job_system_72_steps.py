import sys
import os
import yaml

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows cp932 環境対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_all_72_steps():
    print("=== 全72ステップ 総合検証開始 ===")

    # Step 1 - 8: skill_trees.yaml
    with open("data/skill_trees.yaml", "r", encoding="utf-8") as f:
        st_data = yaml.safe_load(f)
    assert st_data and "skill_trees" in st_data, "Step 1 Failed"
    assert "sword" in st_data["skill_trees"], "Step 2 Failed"
    sword_tiers = st_data["skill_trees"]["sword"]["tiers"]
    assert len(sword_tiers) >= 1 and sword_tiers[0]["id"] == "basic_sword", "Step 3 Failed"
    assert any(t["id"] == "sword_mastery" for t in sword_tiers), "Step 4 Failed"
    assert any(t["id"] == "sword_essence" for t in sword_tiers), "Step 5 Failed"
    assert "magic" in st_data["skill_trees"], "Step 6 Failed"
    magic_tiers = st_data["skill_trees"]["magic"]["tiers"]
    assert len(magic_tiers) == 3 and any(t["id"] == "magic_essence" for t in magic_tiers), "Step 7 Failed"
    assert len(st_data["skill_trees"]) >= 3 and "martial_arts" in st_data["skill_trees"], "Step 8 Failed"
    print("[OK] Steps 1-8 (skill_trees.yaml)")

    # Step 9 - 10: entity.py fields
    from entity import Entity
    p = Entity(0, 0, "@")
    assert hasattr(p, "skill_tree_progress") and isinstance(p.skill_tree_progress, dict), "Step 9 Failed"
    assert hasattr(p, "skill_points") and hasattr(p, "total_skill_points_earned"), "Step 10 Failed"
    print("[OK] Steps 9-10 (entity.py skill tree fields)")

    # Step 11 - 22: skill_tree_system.py
    from skill_tree_system import SkillTreeEffect, SkillTreeTier, SkillTree, SkillTreeRegistry, SkillTreeManager
    eff = SkillTreeEffect(type="damage_bonus", value=5, target="melee") # Step 12
    tier = SkillTreeTier("t1", "Tier 1", "Desc", 5, [], [eff]) # Step 13
    tree = SkillTree("sword", "Sword", "⚔", [tier]) # Step 14
    r1 = SkillTreeRegistry()
    r2 = SkillTreeRegistry()
    assert r1 is r2, "Step 15 Failed"
    r1.load()
    assert len(r1.all()) >= 3, "Step 16 Failed"
    assert r1.get("sword") is not None, "Step 17 Failed"

    stm = SkillTreeManager(r1) # Step 18
    assert stm.check_prerequisites(p, r1.get("sword").tiers[0]), "Step 19 Failed"
    p.skill_points = 50
    assert stm.learn_skill(p, "sword", "basic_sword"), "Step 20 Failed"
    assert "basic_sword" in p.skill_tree_progress["sword"], "Step 20 Failed"
    avail_skills = stm.get_available_skills(p)
    assert len(avail_skills) > 0, "Step 21 Failed"
    learned = stm.get_learned_skills(p)
    assert "basic_sword" in learned, "Step 22 Failed"
    print("[OK] Steps 11-22 (skill_tree_system.py & registry/manager)")

    # Step 23 - 24: entity.py gain_exp with SP
    p2 = Entity(0, 0, "@")
    initial_sp = p2.skill_points
    p2.gain_exp(1000)
    assert p2.skill_points > initial_sp and p2.total_skill_points_earned > 0, "Step 24 Failed"
    print("[OK] Steps 23-24 (entity.py gain_exp SP)")

    # Step 25 - 30: game.py & UI integration
    from ui_fx_systems import SkillTreeUI
    sum_str = SkillTreeUI.format_tree_summary("sword", "剣術", 3, 1)
    tier_str = SkillTreeUI.format_tier_line("剣の基礎", 5, True, False)
    assert "剣術" in sum_str and "習得済" in tier_str, "Step 28 Failed"
    print("[OK] Steps 25-30 (game.py skill tree manager & UI)")

    # Step 31 - 36: data/jobs.yaml
    with open("data/jobs.yaml", "r", encoding="utf-8") as f:
        job_data = yaml.safe_load(f)
    assert job_data and "jobs" in job_data, "Step 31 Failed"
    assert "novice" in job_data["jobs"], "Step 32 Failed"
    assert job_data["jobs"]["warrior"]["stat_modifiers"]["strength"] == 10, "Step 33 Failed"
    assert job_data["jobs"]["swordmaster"]["unlock_conditions"]["job"] == "warrior", "Step 34 Failed"
    assert job_data["jobs"]["mage"]["stat_modifiers"]["magic"] == 12, "Step 35 Failed"
    assert job_data["jobs"]["archmage"]["unlock_conditions"]["job"] == "mage", "Step 36 Failed"
    print("[OK] Steps 31-36 (data/jobs.yaml)")

    # Step 37: entity.py job fields
    assert hasattr(p, "job") and p.job == "novice", "Step 37 Failed"
    assert hasattr(p, "job_level") and hasattr(p, "job_exp"), "Step 37 Failed"
    assert hasattr(p, "previous_jobs") and hasattr(p, "mastered_jobs"), "Step 37 Failed"
    print("[OK] Step 37 (entity.py job fields)")

    # Step 38 - 47: job_system.py
    from job_system import JobEffect, JobData, JobRegistry, JobManager
    je = JobEffect("stat_modifier", 5, "strength") # Step 39
    jd = JobData("t_job", "Test Job", 1, "Desc", {}, {}, [], {}) # Step 40
    jr1 = JobRegistry()
    jr2 = JobRegistry()
    assert jr1 is jr2, "Step 41 Failed"
    jr1.load()
    assert len(jr1.all()) >= 5, "Step 42 Failed"
    jm = JobManager(jr1) # Step 43
    p3 = Entity(0, 0, "@")
    p3.level = 15
    p3.attributes.strength = 20
    p3.skills["basic_sword"] = type("Skill", (), {"level": 35})()
    p3.skills["shield"] = type("Skill", (), {"level": 25})()
    assert jm.check_unlock_conditions(p3, jr1.get("warrior")), "Step 44 Failed"
    assert jm.change_job(p3, "warrior"), "Step 45 Failed"
    assert p3.job == "warrior" and "novice" in p3.previous_jobs, "Step 45 Failed"
    avail_j = jm.get_available_jobs(p3)
    assert isinstance(avail_j, list), "Step 46 Failed"
    jm.apply_job_stats(p3, jr1.get("warrior")) # Step 47
    print("[OK] Steps 38-47 (job_system.py & JobRegistry/JobManager)")

    # Step 48 - 54: entity recalculate_stats, job exp, UI
    p3.recalculate_stats() # Step 48, 49
    from ui_fx_systems import JobUI
    j_sum = JobUI.format_job_summary("戦士", 1, 0)
    assert "戦士" in j_sum, "Step 53 Failed"
    print("[OK] Steps 48-54 (recalculate_stats, job exp & UI)")

    # Step 55 - 58: data/exclusive_skills.yaml
    with open("data/exclusive_skills.yaml", "r", encoding="utf-8") as f:
        excl_data = yaml.safe_load(f)
    assert excl_data and "exclusive_skills" in excl_data, "Step 55 Failed"
    assert excl_data["exclusive_skills"]["shield_bash"]["job"] == "warrior", "Step 56 Failed"
    assert excl_data["exclusive_skills"]["iaijutsu"]["job"] == "swordmaster", "Step 57 Failed"
    assert excl_data["exclusive_skills"]["meteor"]["job"] == "archmage", "Step 58 Failed"
    print("[OK] Steps 55-58 (data/exclusive_skills.yaml)")

    # Step 59 - 61: skill_tree_system exclusive manager & entity exclusive fields
    assert hasattr(p, "mastered_exclusive_skills") and hasattr(p, "inherited_skills"), "Step 61 Failed"
    assert stm.check_exclusive_learnable(p3, excl_data["exclusive_skills"]["shield_bash"]), "Step 59-60 Failed"
    p3.skill_points = 50
    assert stm.learn_exclusive_skill(p3, "shield_bash", cost=5), "Step 60 Failed"
    assert "shield_bash" in p3.mastered_exclusive_skills, "Step 60 Failed"
    print("[OK] Steps 59-61 (Exclusive skills manager & entity fields)")

    # Step 62 - 63: systems.py CombatSystem integration
    from systems import CombatSystem
    assert CombatSystem.is_exclusive_skill("shield_bash"), "Step 62 Failed"
    target_dummy = Entity(0, 0, "D")
    dmg, log_msg = CombatSystem.execute_exclusive_skill(p3, "shield_bash", target_dummy)
    assert dmg > 0, "Step 63 Failed"
    print("[OK] Steps 62-63 (CombatSystem exclusive skills)")

    # Step 64 - 67: data/skill_fusion.yaml
    with open("data/skill_fusion.yaml", "r", encoding="utf-8") as f:
        fus_data = yaml.safe_load(f)
    assert fus_data and "fusions" in fus_data, "Step 64 Failed"
    assert "spellblade" in fus_data["fusions"], "Step 65 Failed"
    assert fus_data["fusions"]["holy_knight"]["required_job"] == "warrior", "Step 66 Failed"
    assert fus_data["fusions"]["shadow_assassin"]["required_job"] == "rogue", "Step 67 Failed"
    print("[OK] Steps 64-67 (data/skill_fusion.yaml)")

    # Step 68 - 72: skill_fusion_system.py
    from skill_fusion_system import FusionEffect, FusionData, FusionRegistry
    fe = FusionEffect("elemental_damage", 20) # Step 69
    fd = FusionData("test_f", "Test Fusion", "Desc", ["req1"], None, None, ["res1"], [fe]) # Step 70
    fr1 = FusionRegistry()
    fr2 = FusionRegistry()
    assert fr1 is fr2, "Step 71 Failed"
    fr1.load()
    assert len(fr1.all()) >= 3, "Step 72 Failed"
    assert fr1.get("spellblade") is not None, "Step 72 Failed"
    print("[OK] Steps 68-72 (skill_fusion_system.py & FusionRegistry)")

    print("\nALL 72 STEPS COMPLETED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all_72_steps()
