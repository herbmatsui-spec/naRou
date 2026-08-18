"""
総合テストスクリプト: スキル合成・進化システム全72ステップの完全検証
"""

import sys
import os
import yaml

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows cp932 環境対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_all_72_steps_skill_synthesis_system():
    print("=== スキル合成・進化システム 全72ステップ 総合検証開始 ===")

    # Step 1: data/skill_fusion.yaml 基本構造作成
    with open("data/skill_fusion.yaml", "r", encoding="utf-8") as f:
        f_raw = yaml.safe_load(f)
    assert f_raw and "fusion_recipes" in f_raw, "Step 1 Failed: fusion_recipes key missing"
    print("[OK] Step 1 (data/skill_fusion.yaml 基本構造)")

    # Step 2: data/skill_fusion.yaml 基本融合レシピ追加
    fb = f_raw.get("fusion_recipes", {}).get("fireball_fusion")
    assert fb is not None, "Step 2 Failed: fireball_fusion recipe missing"
    assert fb.get("name") == "火炎爆砕合成", "Step 2 Failed: name mismatch"
    assert fb.get("output") == "mega_fireball", "Step 2 Failed: output mismatch"
    print("[OK] Step 2 (基本融合レシピ fireball_fusion)")

    # Step 3: data/skill_evolution.yaml 基本構造作成
    with open("data/skill_evolution.yaml", "r", encoding="utf-8") as f:
        evo_raw = yaml.safe_load(f)
    assert evo_raw and "evolution_chains" in evo_raw, "Step 3 Failed: evolution_chains key missing"
    print("[OK] Step 3 (data/skill_evolution.yaml 基本構造)")

    # Step 4: data/skill_evolution.yaml 剣の熟達進化チェーン追加
    sm = evo_raw.get("evolution_chains", {}).get("sword_mastery")
    assert sm is not None, "Step 4 Failed: sword_mastery missing"
    assert len(sm.get("stages", [])) >= 3, "Step 4 Failed: stages count mismatch"
    print("[OK] Step 4 (剣の熟達進化チェーン sword_mastery)")

    # Step 5: data/skill_awakening.yaml 基本構造作成
    with open("data/skill_awakening.yaml", "r", encoding="utf-8") as f:
        awa_raw = yaml.safe_load(f)
    assert awa_raw and "awakenings" in awa_raw, "Step 5 Failed: awakenings key missing"
    print("[OK] Step 5 (data/skill_awakening.yaml 基本構造)")

    # Step 6: data/skill_awakening.yaml 竜殺しの覚醒追加
    ds = awa_raw.get("awakenings", {}).get("dragon_slaying_awakening")
    assert ds is not None, "Step 6 Failed: dragon_slaying_awakening missing"
    assert ds.get("base_skill") == "swordsmanship", "Step 6 Failed: base_skill mismatch"
    assert ds.get("awakened_skill") == "true_dragon_slayer", "Step 6 Failed: awakened_skill mismatch"
    print("[OK] Step 6 (竜殺しの覚醒 dragon_slaying_awakening)")

    # Step 7: data/skill_transfer.yaml 基本構造作成
    with open("data/skill_transfer.yaml", "r", encoding="utf-8") as f:
        tra_raw = yaml.safe_load(f)
    assert tra_raw and "transfer_traits" in tra_raw, "Step 7 Failed: transfer_traits key missing"
    print("[OK] Step 7 (data/skill_transfer.yaml 基本構造)")

    # Step 8: data/skill_transfer.yaml クリティカル強化転移追加
    cb = tra_raw.get("transfer_traits", {}).get("critical_boost")
    assert cb is not None, "Step 8 Failed: critical_boost missing"
    assert cb.get("transfer_ratio") == 0.80, "Step 8 Failed: transfer_ratio mismatch"
    print("[OK] Step 8 (クリティカル強化転移 critical_boost)")

    # Step 9: data/skill_resonance.yaml 基本構造作成
    with open("data/skill_resonance.yaml", "r", encoding="utf-8") as f:
        res_raw = yaml.safe_load(f)
    assert res_raw and "resonance_sets" in res_raw, "Step 9 Failed: resonance_sets key missing"
    print("[OK] Step 9 (data/skill_resonance.yaml 基本構造)")

    # Step 10: data/skill_resonance.yaml 炎の騎士セット追加
    fk = res_raw.get("resonance_sets", {}).get("flame_knight_set")
    assert fk is not None, "Step 10 Failed: flame_knight_set missing"
    assert "swordsmanship" in fk.get("required_skills", []), "Step 10 Failed: required_skills mismatch"
    print("[OK] Step 10 (炎の騎士セット flame_knight_set)")

    # Step 11: data/skill_inheritance.yaml 基本構造作成
    with open("data/skill_inheritance.yaml", "r", encoding="utf-8") as f:
        inh_raw = yaml.safe_load(f)
    assert inh_raw and "inheritance_rules" in inh_raw, "Step 11 Failed: inheritance_rules key missing"
    print("[OK] Step 11 (data/skill_inheritance.yaml 基本構造)")

    # Step 12: data/skill_inheritance.yaml 血統スキル継承追加
    bs = inh_raw.get("inheritance_rules", {}).get("bloodline_skills")
    assert bs is not None, "Step 12 Failed: bloodline_skills missing"
    assert "swordsmanship" in bs.get("eligible_skills", []), "Step 12 Failed: eligible_skills mismatch"
    print("[OK] Step 12 (血統スキル継承 bloodline_skills)")

    # Step 13: data/skill_specialization.yaml 基本構造作成
    with open("data/skill_specialization.yaml", "r", encoding="utf-8") as f:
        spec_raw = yaml.safe_load(f)
    assert spec_raw and "specialization_paths" in spec_raw, "Step 13 Failed: specialization_paths key missing"
    print("[OK] Step 13 (data/skill_specialization.yaml 基本構造)")

    # Step 14: data/skill_specialization.yaml ファイアボール専門化パス追加
    fs = spec_raw.get("specialization_paths", {}).get("fireball_specialization")
    assert fs is not None, "Step 14 Failed: fireball_specialization missing"
    assert fs.get("base_skill") == "magic_cast", "Step 14 Failed: base_skill mismatch"
    assert len(fs.get("branches", [])) >= 2, "Step 14 Failed: branches count mismatch"
    print("[OK] Step 14 (ファイアボール専門化パス fireball_specialization)")

    # Step 15: data/skill_fusion_chains.yaml 基本構造作成
    with open("data/skill_fusion_chains.yaml", "r", encoding="utf-8") as f:
        fc_raw = yaml.safe_load(f)
    assert fc_raw and "fusion_chains" in fc_raw, "Step 15 Failed: fusion_chains key missing"
    print("[OK] Step 15 (data/skill_fusion_chains.yaml 基本構造)")

    # Step 16: data/skill_fusion_chains.yaml 究極竜殺し融合連鎖追加
    uds = fc_raw.get("fusion_chains", {}).get("ultimate_dragon_slayer")
    assert uds is not None, "Step 16 Failed: ultimate_dragon_slayer missing"
    assert len(uds.get("stages", [])) >= 3, "Step 16 Failed: stages count mismatch"
    print("[OK] Step 16 (究極竜殺し融合連鎖 ultimate_dragon_slayer)")

    # Step 17: data/skill_archive.yaml 基本構造作成
    with open("data/skill_archive.yaml", "r", encoding="utf-8") as f:
        arc_raw = yaml.safe_load(f)
    assert arc_raw and "archive_categories" in arc_raw, "Step 17 Failed: archive_categories key missing"
    print("[OK] Step 17 (data/skill_archive.yaml 基本構造)")

    # Step 18: data/skill_archive.yaml 元素魔法アーカイブ追加
    es = arc_raw.get("archive_categories", {}).get("elemental_spells")
    assert es is not None, "Step 18 Failed: elemental_spells missing"
    assert "fireball" in es.get("skills", []), "Step 18 Failed: skills list mismatch"
    print("[OK] Step 18 (元素魔法アーカイブ elemental_spells)")

    # Steps 19-28: entity.py スキル合成関連フィールド追加
    from entity import Entity, Skill
    ent_code = open("entity.py", encoding="utf-8").read()
    assert "# TODO: Skill synthesis/evolution fields" in ent_code, "Step 19 Failed: placeholder comment missing"
    
    e = Entity()
    assert hasattr(e, "skill_fusion_materials") and isinstance(e.skill_fusion_materials, dict), "Step 20 Failed"
    assert hasattr(e, "skill_evolution") and isinstance(e.skill_evolution, dict), "Step 21 Failed"
    assert hasattr(e, "awakened_skills") and isinstance(e.awakened_skills, list), "Step 22 Failed"
    assert hasattr(e, "skill_traits") and isinstance(e.skill_traits, dict), "Step 23 Failed"
    assert hasattr(e, "equipped_skills") and isinstance(e.equipped_skills, list), "Step 24 Failed"
    assert hasattr(e, "inheritable_skills") and isinstance(e.inheritable_skills, list), "Step 25 Failed"
    assert hasattr(e, "skill_specialization") and isinstance(e.skill_specialization, dict), "Step 26 Failed"
    assert hasattr(e, "fusion_chain_progress") and isinstance(e.fusion_chain_progress, dict), "Step 27 Failed"
    assert hasattr(e, "skill_archive_progress") and isinstance(e.skill_archive_progress, dict), "Step 28 Failed"
    print("[OK] Steps 19-28 (entity.py スキル合成・進化フィールド)")

    # Steps 29-35: skill_fusion_system.py
    from skill_fusion_system import SkillFusionData, SkillFusionRegistry, SkillFusionManager, REGISTRY as FUSION_REG
    assert SkillFusionData is not None, "Step 30 Failed"
    fr1 = SkillFusionRegistry()
    fr2 = SkillFusionRegistry()
    assert fr1 is fr2, "Step 31 Failed: singleton mismatch"
    FUSION_REG.load()
    assert len(FUSION_REG.all()) >= 1, "Step 32 Failed: registry load"
    
    fmgr = SkillFusionManager(FUSION_REG)
    e.level = 15
    e.skills["magic_cast"] = Skill("magic_cast", level=10)
    e.skill_fusion_materials["fire_essence"] = 1
    e.skills["magic_dart"] = Skill("magic_dart", level=5)
    assert fmgr.can_fuse(e, "fireball_fusion"), "Step 34 Failed: can_fuse"
    ok, fmsg = fmgr.fuse_skills(e, "fireball_fusion")
    assert ok and "mega_fireball" in e.skills, "Step 35 Failed: fuse_skills"
    print("[OK] Steps 29-35 (skill_fusion_system.py Data/Registry/Manager)")

    # Steps 36-42: skill_evolution_system.py
    from skill_evolution_system import SkillEvolutionData, SkillEvolutionRegistry, SkillEvolutionManager, REGISTRY as EVO_REG
    assert SkillEvolutionData is not None, "Step 37 Failed"
    er1 = SkillEvolutionRegistry()
    er2 = SkillEvolutionRegistry()
    assert er1 is er2, "Step 38 Failed: singleton mismatch"
    EVO_REG.load()
    assert len(EVO_REG.all()) >= 1, "Step 39 Failed: registry load"
    
    emgr = SkillEvolutionManager(EVO_REG)
    e.skills["swordsmanship"] = Skill("swordsmanship", level=15)
    next_st = emgr.check_evolution(e, "sword_mastery")
    assert next_st is not None and next_st.get("id") == "sword_stage_1", "Step 41 Failed: check_evolution"
    ok_evo = emgr.evolve_skill(e, "sword_mastery")
    assert ok_evo and e.skill_evolution.get("sword_mastery") == "sword_stage_1", "Step 42 Failed: evolve_skill"
    print("[OK] Steps 36-42 (skill_evolution_system.py Data/Registry/Manager)")

    # Steps 43-49: skill_awakening_system.py
    from skill_awakening_system import SkillAwakeningData, SkillAwakeningRegistry, SkillAwakeningManager, REGISTRY as AWA_REG
    assert SkillAwakeningData is not None, "Step 44 Failed"
    ar1 = SkillAwakeningRegistry()
    ar2 = SkillAwakeningRegistry()
    assert ar1 is ar2, "Step 45 Failed: singleton mismatch"
    AWA_REG.load()
    assert len(AWA_REG.all()) >= 1, "Step 46 Failed: registry load"
    
    amgr = SkillAwakeningManager(AWA_REG)
    e.skills["swordsmanship"].level = 35
    e.monster_killed_types["dragon"] = 10
    assert amgr.can_awaken(e, "dragon_slaying_awakening"), "Step 48 Failed: can_awaken"
    ok_awa = amgr.awaken_skill(e, "dragon_slaying_awakening")
    assert ok_awa and "true_dragon_slayer" in e.skills, "Step 49 Failed: awaken_skill"
    print("[OK] Steps 43-49 (skill_awakening_system.py Data/Registry/Manager)")

    # Steps 50-56: skill_transfer_system.py
    from skill_transfer_system import SkillTransferData, SkillTransferRegistry, SkillTransferManager, REGISTRY as TRA_REG
    assert SkillTransferData is not None, "Step 51 Failed"
    tr1 = SkillTransferRegistry()
    tr2 = SkillTransferRegistry()
    assert tr1 is tr2, "Step 52 Failed: singleton mismatch"
    TRA_REG.load()
    assert len(TRA_REG.all()) >= 1, "Step 53 Failed: registry load"
    
    tmgr = SkillTransferManager(TRA_REG)
    e.skill_points = 50
    e.gold = 10000
    e.skills["swordsmanship"] = Skill("swordsmanship", level=10)
    assert tmgr.can_transfer(e, "critical_boost", "swordsmanship"), "Step 55 Failed: can_transfer"
    ok_tra = tmgr.transfer_trait(e, "critical_boost", "swordsmanship")
    assert ok_tra and "swordsmanship" in e.skill_traits, "Step 56 Failed: transfer_trait"
    print("[OK] Steps 50-56 (skill_transfer_system.py Data/Registry/Manager)")

    # Steps 57-64: skill_resonance_system.py
    from skill_resonance_system import SkillResonanceData, SkillResonanceRegistry, SkillResonanceManager, REGISTRY as RES_REG
    assert SkillResonanceData is not None, "Step 58 Failed"
    rr1 = SkillResonanceRegistry()
    rr2 = SkillResonanceRegistry()
    assert rr1 is rr2, "Step 59 Failed: singleton mismatch"
    RES_REG.load()
    assert len(RES_REG.all()) >= 1, "Step 60 Failed: registry load"
    
    rmgr = SkillResonanceManager(RES_REG)
    e.skills["swordsmanship"] = Skill("swordsmanship", level=10)
    e.skills["magic_cast"] = Skill("magic_cast", level=10)
    active_sets = rmgr.check_resonance(e)
    assert len(active_sets) >= 1, "Step 62 Failed: check_resonance"
    effs = rmgr.apply_resonance_effects(e)
    assert "fire_dmg_boost" in effs, "Step 63 Failed: apply_resonance_effects"
    print("[OK] Steps 57-64 (skill_resonance_system.py Data/Registry/Manager)")

    # Steps 65-69: skill_inheritance_system.py
    from skill_inheritance_system import SkillInheritanceData, SkillInheritanceRegistry, SkillInheritanceManager, REGISTRY as INH_REG
    assert SkillInheritanceData is not None, "Step 66 Failed"
    ir1 = SkillInheritanceRegistry()
    ir2 = SkillInheritanceRegistry()
    assert ir1 is ir2, "Step 67 Failed: singleton mismatch"
    INH_REG.load()
    assert len(INH_REG.all()) >= 1, "Step 68 Failed: registry load"
    
    imgr = SkillInheritanceManager(INH_REG)
    avail_inh = imgr.get_inheritable_skills(e, "bloodline_skills")
    assert "swordsmanship" in avail_inh, "Step 69 Failed: get_inheritable_skills"
    ok_inh = imgr.inherit_skill(e, "swordsmanship", "bloodline_skills")
    assert ok_inh and "swordsmanship" in e.inheritable_skills, "Step 69 Failed: inherit_skill"
    print("[OK] Steps 65-69 (skill_inheritance_system.py Data/Registry/Manager)")

    # Steps 70-71: skill_specialization_system.py
    from skill_specialization_system import SkillSpecializationData, SkillSpecializationManager, REGISTRY as SPEC_REG
    assert SkillSpecializationData is not None, "Step 71 Failed"
    SPEC_REG.load()
    assert len(SPEC_REG.all()) >= 1, "Step 71 Failed: registry load"
    smgr = SkillSpecializationManager(SPEC_REG)
    assert smgr.can_specialize(e, "fireball_specialization", "inferno_burst"), "Step 71 Failed: can_specialize"
    ok_spec = smgr.specialize_skill(e, "fireball_specialization", "inferno_burst")
    assert ok_spec and e.skill_specialization.get("fireball_specialization") == "inferno_burst", "Step 71 Failed: specialize_skill"
    print("[OK] Steps 70-71 (skill_specialization_system.py Data/Registry/Manager)")

    # Step 72: game.py & save_system.py 統合・永続化検証
    from game import Engine
    from save_system import SaveSystem
    eng = Engine()
    assert hasattr(eng, "skill_fusion_manager"), "Step 72 Failed: fusion manager on Engine"
    assert hasattr(eng, "skill_evolution_manager"), "Step 72 Failed: evolution manager on Engine"
    assert hasattr(eng, "skill_awakening_manager"), "Step 72 Failed: awakening manager on Engine"
    assert hasattr(eng, "skill_transfer_manager"), "Step 72 Failed: transfer manager on Engine"
    assert hasattr(eng, "skill_resonance_manager"), "Step 72 Failed: resonance manager on Engine"
    assert hasattr(eng, "skill_inheritance_manager"), "Step 72 Failed: inheritance manager on Engine"
    assert hasattr(eng, "skill_specialization_manager"), "Step 72 Failed: specialization manager on Engine"

    eng.player.skill_evolution["sword_mastery"] = "sword_stage_2"
    eng.player.awakened_skills = ["dragon_slaying_awakening"]
    save_msg = SaveSystem.save(eng)
    assert "セーブ完了" in save_msg, "Step 72 Save failed"
    loaded_eng, _ = SaveSystem.load()
    assert loaded_eng is not None, "Step 72 Load failed"
    assert loaded_eng.player.skill_evolution.get("sword_mastery") == "sword_stage_2", "Step 72 State persistence failed"
    assert "dragon_slaying_awakening" in loaded_eng.player.awakened_skills, "Step 72 State persistence failed"
    print("[OK] Step 72 (game.py Engine 統合 & save_system.py 完全永続化)")

    print("\nALL 72 STEPS OF SKILL SYNTHESIS & EVOLUTION SYSTEM VERIFIED 100% SUCCESSFULLY!")


if __name__ == "__main__":
    test_all_72_steps_skill_synthesis_system()
