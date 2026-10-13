"""Unit tests for Phase 0 System (Steps 65-71)."""

from skill_eater_phase0_system import EscapeMap, Phase0Manager, Phase0State, UIMode


def test_step65_vr_tutorial_completion():
    manager = Phase0Manager()
    manager.start_vr_training()
    assert manager.current_state == Phase0State.VR_TRAINING

    # Record deliberate inefficient actions
    manager.record_vr_action("MISS_ATTACK")
    manager.record_vr_action("WASTE_MP")
    manager.record_vr_action("IDLE_STARE")

    res = manager.complete_vr_training()
    assert res["success"] is True
    assert manager.current_state == Phase0State.APTITUDE_TEST
    assert res["evaluation"] == "INCOMPETENT"


def test_step66_aptitude_and_future_avoidance():
    manager = Phase0Manager()
    manager.current_state = Phase0State.APTITUDE_TEST

    # Selecting true overpowered skill triggers refusal
    reject = manager.evaluate_aptitude_choice("opt_attack")
    assert reject["accepted"] is False

    # Selecting analysis succeeds
    accept = manager.evaluate_aptitude_choice("opt_analysis")
    assert accept["accepted"] is True

    # Avoid future doom by signing dismissal
    sign_res = manager.sign_dismissal_paper(accept=True)
    assert sign_res["success"] is True
    assert sign_res["future_flag"] == "AVOIDED"
    assert manager.future_avoided is True


def test_step67_embezzlement_minigame():
    manager = Phase0Manager()
    manager.start_embezzlement_timer(30)
    assert manager.current_state == Phase0State.HACKING

    # Failure pattern
    fail_res = manager.submit_hacking_attempt("0000")
    assert fail_res["success"] is False

    # Success pattern
    succ_res = manager.submit_hacking_attempt("7734")
    assert succ_res["success"] is True
    assert "裏帳簿" in succ_res["reward"]["name"]


def test_step68_stealth_escape_map_pathfinding():
    emap = EscapeMap()
    overlays = emap.reveal_stealth_overlays(analysis_active=True)
    assert len(overlays["danger_zones"]) > 0
    assert len(overlays["safe_path_hint"]) > 0

    # Test step on safe path
    step_res = emap.step_player((1, 2), analysis_active=True)
    assert step_res["detected"] is False
    assert step_res["escaped"] is False


def test_step69_boss_encounter_and_environmental_escape():
    manager = Phase0Manager()
    manager.trigger_boss_encounter()
    assert manager.current_state == Phase0State.BOSS
    assert manager.boss_enemy is not None

    # Analysis of boss weakness
    weakness_res = manager.analyze_boss_weakness()
    assert weakness_res["success"] is True

    # Execute environmental escape
    escape_res = manager.execute_environmental_escape()
    assert escape_res["success"] is True
    assert escape_res["action"] == "ESCAPE_TO_SLUM"


def test_step70_ui_hack_transition_rendering():
    manager = Phase0Manager()
    assert manager.ui_mode == UIMode.CLASSIC_RPG

    hack_res = manager.trigger_ui_hack_transition()
    assert hack_res["status"] == "UI_HACKED"
    assert manager.ui_mode == UIMode.SKILL_SCANNER
    assert len(hack_res["glitch_sequence"]) == 3


def test_step71_end_to_end_phase0_workflow():
    manager = Phase0Manager()
    save_state = {}

    # 1. VR
    manager.start_vr_training()
    manager.record_vr_action("MISS_ATTACK")
    manager.record_vr_action("MISS_ATTACK")
    manager.record_vr_action("MISS_ATTACK")
    manager.complete_vr_training()

    # 2. Aptitude & Firing
    manager.evaluate_aptitude_choice("opt_analysis")
    manager.sign_dismissal_paper(True)

    # 3. Hack & Escape
    manager.start_embezzlement_timer()
    manager.submit_hacking_attempt("7734")

    # 4. Boss
    manager.trigger_boss_encounter()
    manager.analyze_boss_weakness()
    manager.execute_environmental_escape()

    # 5. Transition to Slum & Complete
    manager.transition_to_slum_alley()
    comp = manager.complete_phase0_workflow(save_state)
    assert comp["success"] is True
    assert save_state["phase0_completed"] is True
    assert save_state["phase0_meta_score"] > 0
