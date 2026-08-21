"""Unit tests for Phase 1 System (Steps 65-71)."""

import pytest
from skill_eater_combat_system import Phase1CombatManager
from skill_eater_crafting_system import PatchworkCraftingEngine, PatchworkSkill, SkillScrap
from skill_eater_slum_map import SlumMapManager
from skill_eater_meta_recipes import MetaRecipeCraftingEngine
from skill_eater_toxicity_system import SafehouseLocation, SkillToxicityManager
from skill_eater_resistance_system import ResistanceMarketManager
from skill_eater_pursuer_system import HoundSpawnManager
from skill_eater_awakening_system import DevourAwakeningManager


def test_step65_environmental_kill_and_weak_point_combat():
    combat_mgr = Phase1CombatManager()
    combat_mgr.setup_slum_tutorial_encounter()
    assert len(combat_mgr.current_enemies) == 1
    assert len(combat_mgr.environment_objects) == 1

    # Analysis reveals weakness
    enemy_id = combat_mgr.current_enemies[0].enemy_id
    analysis_res = combat_mgr.analyze_enemy_weakness(enemy_id)
    assert analysis_res["success"] is True

    # Weak point attack deals 3x critical damage
    atk_res = combat_mgr.attack_weak_point(enemy_id, base_atk=10)
    assert atk_res["critical"] is True
    assert atk_res["damage"] == 50  # 10 * 3 + 20

    # Environmental trap trigger
    trap_res = combat_mgr.trigger_environmental_hazard("SCAFFOLD_01")
    assert trap_res["success"] is True
    assert trap_res["damage_dealt"] == 120
    assert combat_mgr.current_enemies[0].hp <= 0


def test_step66_patchwork_crafting_and_durability_break():
    craft_engine = PatchworkCraftingEngine()
    
    # Synthesize scraps
    scraps = ["SCRAP_BEAST_FANG", "SCRAP_AGILITY_FRAGMENT"]
    craft_res = craft_engine.synthesize_patchwork_skill(scraps)
    assert craft_res["success"] is True
    assert "瞬突・牙咬み" in craft_res["skill"]["name"]
    
    # Use patchwork skill until it breaks
    skill = PatchworkSkill(
        skill_id="SK_TEST",
        name="瞬突・牙咬み",
        effect_type="QUICK_ATTACK",
        power=45,
        max_durability=2,
        current_durability=2,
    )
    
    use1 = craft_engine.use_patchwork_skill(skill)
    assert use1["is_shattered"] is False
    assert skill.current_durability == 1
    
    use2 = craft_engine.use_patchwork_skill(skill)
    assert use2["is_shattered"] is True
    assert skill.is_broken is True


def test_step67_husk_memory_extraction_and_safe_unlock():
    slum_mgr = SlumMapManager()
    assert len(slum_mgr.husks) >= 2

    # Extract memory from first Husk
    husk_id = slum_mgr.husks[0].npc_id
    analyze_res = slum_mgr.analyze_husk(husk_id)
    assert analyze_res["success"] is True

    extract_res = slum_mgr.extract_memory_data(husk_id)
    assert extract_res["success"] is True
    assert extract_res["secret_value"] == "4989"

    # Unlock safe using extracted code
    safe_res = slum_mgr.unlock_slum_hidden_safe("4989")
    assert safe_res["success"] is True
    assert safe_res["reward_gold"] == 1200


def test_step68_meta_recipes_and_resistance_reputation():
    meta_engine = MetaRecipeCraftingEngine()
    
    # Craft C4 magic bomb from junk
    junk_ingredients = ["SLIME_MUCUS", "FLINT_STONE", "SULFUR_POWDER"]
    craft_res = meta_engine.craft_with_meta_knowledge(junk_ingredients)
    assert craft_res["success"] is True
    assert craft_res["item_id"] == "ITEM_C4_MAGIC_BOMB"
    assert craft_res["power"] == 350

    # Resistance donations
    res_mgr = ResistanceMarketManager()
    donate_res = res_mgr.donate_items_to_resistance(["SCRAP_IRON_GUARD", "SAFE_PASSWORD_MIDAS_SLUM"])
    assert donate_res["success"] is True
    assert donate_res["earned_reputation"] == 140
    assert res_mgr.state.reputation_level == 1
    assert "FREE_MEDICAL_STATION" in res_mgr.state.unlocked_facilities


def test_step69_toxicity_accumulation_debuffs_and_safehouse_rest():
    tox_mgr = SkillToxicityManager()
    assert tox_mgr.state.is_overloaded is False

    # Add toxicity over 80%
    tox_mgr.add_toxicity(85, "FORCED_SYNTHESIS")
    assert tox_mgr.state.is_overloaded is True
    assert tox_mgr.state.movement_speed_penalty == 0.5
    assert tox_mgr.state.atk_multiplier == 0.5

    # Safehouse rest removes debuffs
    safehouse = SafehouseLocation("SH_01", "地下水路の隠れ家", recovery_rate=100)
    rest_res = tox_mgr.rest_at_safehouse(safehouse)
    assert rest_res["success"] is True
    assert tox_mgr.state.current_toxicity == 0
    assert tox_mgr.state.is_overloaded is False


def test_step70_hound_stealth_hiding_and_trap_defeat():
    hound_mgr = HoundSpawnManager()
    hound_mgr.spawn_hound((5, 5))
    assert hound_mgr.is_spawned is True

    # Player hides in dumpster
    hide_res = hound_mgr.interact_with_hiding_spot((1, 1))
    assert hide_res["success"] is True
    assert hound_mgr.player_is_hidden is True

    # Hound cannot detect hidden player
    patrol_res = hound_mgr.update_hound_patrol_and_detect((1, 1), is_running=True)
    assert patrol_res["detected"] is False

    # Defeat Hound with trap
    defeat_res = hound_mgr.defeat_hound_with_trap()
    assert defeat_res["success"] is True
    assert defeat_res["reward_skill"] == "SKILL_SHADOW_STEP_COMPLETE"


def test_step71_awakening_event_and_phase1_end_to_end():
    awakening_mgr = DevourAwakeningManager()
    save_state = {}

    # Player near-death trigger (< 10% HP)
    stop_res = awakening_mgr.check_near_death_time_stop(player_hp=5, player_max_hp=100)
    assert stop_res["triggered"] is True

    # Unlock Devour command
    unlock_res = awakening_mgr.unlock_devour_command()
    assert unlock_res["command"] == "DEVOUR"

    # Devour Kill on Mid-Boss
    kill_res = awakening_mgr.execute_devour_kill()
    assert kill_res["success"] is True
    assert kill_res["target_defeated"] is True
    assert kill_res["stolen_skill"] == "ユニークスキル《重圧魔導砲》"

    # Transition to Phase 2
    trans_res = awakening_mgr.complete_phase1_transition()
    assert trans_res["success"] is True
    assert trans_res["next_phase"] == "Phase 2: テンプレート破壊 (Lv21-50)"

    # Persist Save State
    export_res = awakening_mgr.export_phase1_save_state(save_state)
    assert export_res["success"] is True
    assert save_state["phase1_completed"] is True
    assert "ユニークスキル《重圧魔導砲》" in save_state["acquired_skills"]
