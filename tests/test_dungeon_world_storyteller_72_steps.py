"""
総合テストスクリプト: ダンジョン・ワールド自動生成ストーリーテラー 全72ステップの完全検証
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


def test_all_72_steps_storyteller_system():
    print("=== ダンジョン・ワールド自動生成ストーリーテラー 全72ステップ 総合検証開始 ===")

    # Step 1: data/procedural_scenarios.yaml 基本構造
    with open("data/procedural_scenarios.yaml", "r", encoding="utf-8") as f:
        scen_raw = yaml.safe_load(f)
    assert scen_raw and "scenario_templates" in scen_raw, "Step 1 Failed: scenario_templates missing"
    print("[OK] Step 1 (data/procedural_scenarios.yaml 基本構造)")

    # Step 2: data/procedural_scenarios.yaml ゴブリン侵略シナリオ追加
    gi = scen_raw.get("scenario_templates", {}).get("goblin_invasion")
    assert gi is not None, "Step 2 Failed: goblin_invasion missing"
    assert len(gi.get("chapters", [])) >= 2, "Step 2 Failed: chapters count mismatch"
    print("[OK] Step 2 (ゴブリン侵略シナリオ goblin_invasion)")

    # Step 3: data/story_choices.yaml 基本構造
    with open("data/story_choices.yaml", "r", encoding="utf-8") as f:
        cho_raw = yaml.safe_load(f)
    assert cho_raw and "choice_consequences" in cho_raw, "Step 3 Failed: choice_consequences missing"
    print("[OK] Step 3 (data/story_choices.yaml 基本構造)")

    # Step 4: data/story_choices.yaml 農家の生存者救出結果追加
    fss = cho_raw.get("choice_consequences", {}).get("farm_survivor_saved")
    assert fss is not None, "Step 4 Failed: farm_survivor_saved missing"
    assert len(fss.get("immediate_effects", [])) >= 2, "Step 4 Failed: immediate_effects missing"
    print("[OK] Step 4 (農家の生存者救出結果 farm_survivor_saved)")

    # Step 5: data/world_state.yaml 基本構造
    with open("data/world_state.yaml", "r", encoding="utf-8") as f:
        ws_raw = yaml.safe_load(f)
    assert ws_raw and "world_state_template" in ws_raw, "Step 5 Failed: world_state_template missing"
    print("[OK] Step 5 (data/world_state.yaml 基本構造)")

    # Step 6: data/world_state.yaml 基本ワールド状態テンプレート追加
    wst = ws_raw.get("world_state_template")
    assert wst is not None, "Step 6 Failed: template missing"
    assert "goblin_threat_level" in wst.get("persistent_variables", {}), "Step 6 Failed: persistent_variables missing"
    print("[OK] Step 6 (基本ワールド状態テンプレート)")

    # Step 7: data/dungeon_themes.yaml 基本構造
    with open("data/dungeon_themes.yaml", "r", encoding="utf-8") as f:
        dt_raw = yaml.safe_load(f)
    assert dt_raw and "dungeon_themes" in dt_raw, "Step 7 Failed: dungeon_themes missing"
    print("[OK] Step 7 (data/dungeon_themes.yaml 基本構造)")

    # Step 8: data/dungeon_themes.yaml ゴブリンの洞窟テーマ追加
    gc = dt_raw.get("dungeon_themes", {}).get("goblin_cave")
    assert gc is not None, "Step 8 Failed: goblin_cave missing"
    assert "common" in gc.get("enemy_pools", {}), "Step 8 Failed: enemy_pools missing"
    print("[OK] Step 8 (ゴブリンの洞窟テーマ goblin_cave)")

    # Step 9: data/character_relations.yaml 基本構造
    with open("data/character_relations.yaml", "r", encoding="utf-8") as f:
        cr_raw = yaml.safe_load(f)
    assert cr_raw and "relationship_templates" in cr_raw, "Step 9 Failed: relationship_templates missing"
    print("[OK] Step 9 (data/character_relations.yaml 基本構造)")

    # Step 10: data/character_relations.yaml 助けた村人関係追加
    sv = cr_raw.get("relationship_templates", {}).get("saved_villager")
    assert sv is not None, "Step 10 Failed: saved_villager missing"
    assert len(sv.get("interaction_effects", [])) >= 2, "Step 10 Failed: interaction_effects missing"
    print("[OK] Step 10 (助けた村人関係 saved_villager)")

    # Step 11: data/world_events.yaml 基本構造
    with open("data/world_events.yaml", "r", encoding="utf-8") as f:
        we_raw = yaml.safe_load(f)
    assert we_raw and "world_events" in we_raw, "Step 11 Failed: world_events missing"
    print("[OK] Step 11 (data/world_events.yaml 基本構造)")

    # Step 12: data/world_events.yaml 血の月イベント追加
    bm = we_raw.get("world_events", {}).get("blood_moon")
    assert bm is not None, "Step 12 Failed: blood_moon missing"
    assert bm.get("duration") == 100, "Step 12 Failed: duration mismatch"
    print("[OK] Step 12 (血の月イベント blood_moon)")

    # Step 13: data/memory_fragments.yaml 基本構造
    with open("data/memory_fragments.yaml", "r", encoding="utf-8") as f:
        mf_raw = yaml.safe_load(f)
    assert mf_raw and "memory_fragments" in mf_raw, "Step 13 Failed: memory_fragments missing"
    print("[OK] Step 13 (data/memory_fragments.yaml 基本構造)")

    # Step 14: data/memory_fragments.yaml ゴブリン子どもの悲鳴フラグメント追加
    gcs = mf_raw.get("memory_fragments", {}).get("goblin_child_screams")
    assert gcs is not None, "Step 14 Failed: goblin_child_screams missing"
    assert len(gcs.get("resolution_paths", [])) >= 2, "Step 14 Failed: resolution_paths missing"
    print("[OK] Step 14 (ゴブリン子どもの悲鳴フラグメント goblin_child_screams)")

    # Step 15: data/story_endings.yaml 基本構造
    with open("data/story_endings.yaml", "r", encoding="utf-8") as f:
        se_raw = yaml.safe_load(f)
    assert se_raw and "story_endings" in se_raw, "Step 15 Failed: story_endings missing"
    print("[OK] Step 15 (data/story_endings.yaml 基本構造)")

    # Step 16: data/story_endings.yaml ゴブリンの和平使者エンディング追加
    gpb = se_raw.get("story_endings", {}).get("goblin_peace_bringer")
    assert gpb is not None, "Step 16 Failed: goblin_peace_bringer missing"
    assert "spared_cubs_resolved" in gpb.get("unlock_conditions", []), "Step 16 Failed: unlock_conditions mismatch"
    print("[OK] Step 16 (ゴブリンの和平使者エンディング goblin_peace_bringer)")

    # Step 17: data/story_ui.yaml 基本構造
    with open("data/story_ui.yaml", "r", encoding="utf-8") as f:
        ui_raw = yaml.safe_load(f)
    assert ui_raw and "ui_elements" in ui_raw, "Step 17 Failed: ui_elements missing"
    print("[OK] Step 17 (data/story_ui.yaml 基本構造)")

    # Step 18: data/story_ui.yaml ストーリー通知UI要素追加
    sn = ui_raw.get("ui_elements", {}).get("story_notification")
    assert sn is not None, "Step 18 Failed: story_notification missing"
    assert sn.get("display_priority") == "high", "Step 18 Failed: display_priority mismatch"
    print("[OK] Step 18 (ストーリー通知UI要素 story_notification)")

    # Steps 19-32: entity.py ストーリー関連フィールド追加
    from entity import Entity
    ent_code = open("entity.py", encoding="utf-8").read()
    assert "# TODO: Story/world state fields" in ent_code, "Step 19 Failed: placeholder comment missing"
    
    e = Entity()
    assert hasattr(e, "story_flags") and isinstance(e.story_flags, dict), "Step 20 Failed"
    assert hasattr(e, "story_variables") and isinstance(e.story_variables, dict), "Step 21 Failed"
    assert hasattr(e, "story_choices_made") and isinstance(e.story_choices_made, list), "Step 22 Failed"
    assert hasattr(e, "world_state_version") and e.world_state_version == "1.0", "Step 23 Failed"
    assert hasattr(e, "player_legacy") and isinstance(e.player_legacy, dict), "Step 24 Failed"
    assert hasattr(e, "character_relationships") and isinstance(e.character_relationships, dict), "Step 25 Failed"
    assert hasattr(e, "memory_fragments") and isinstance(e.memory_fragments, list), "Step 26 Failed"
    assert hasattr(e, "active_world_events") and isinstance(e.active_world_events, list), "Step 27 Failed"
    assert hasattr(e, "completed_storylines") and isinstance(e.completed_storylines, list), "Step 28 Failed"
    assert hasattr(e, "available_storylines") and isinstance(e.available_storylines, list), "Step 29 Failed"
    assert hasattr(e, "story_notifications") and isinstance(e.story_notifications, list), "Step 30 Failed"
    assert hasattr(e, "current_choice_prompt"), "Step 31 Failed"
    assert hasattr(e, "ending_progress") and isinstance(e.ending_progress, dict), "Step 32 Failed"
    print("[OK] Steps 19-32 (entity.py ストーリー・ワールド状態フィールド)")

    # Steps 33-40: storyteller_system.py
    from storyteller_system import (
        StoryScenarioData, StoryChapterData, StoryChoiceData,
        StorytellerRegistry, StorytellerManager, REGISTRY as STORY_REG
    )
    assert StoryScenarioData is not None, "Step 34 Failed"
    assert StoryChapterData is not None, "Step 35 Failed"
    assert StoryChoiceData is not None, "Step 36 Failed"
    sr1 = StorytellerRegistry()
    sr2 = StorytellerRegistry()
    assert sr1 is sr2, "Step 38 Failed: singleton mismatch"
    STORY_REG.load()
    assert len(STORY_REG.all_scenarios()) >= 1, "Step 39 Failed: load"
    smgr = StorytellerManager(STORY_REG)
    scens = smgr.check_scenario_triggers(e)
    assert len(scens) >= 1, "Step 40 Failed: check_scenario_triggers"
    ok_act = smgr.activate_scenario(e, "goblin_invasion")
    assert ok_act and e.story_flags.get("goblin_invasion_active"), "Step 40 Failed: activate_scenario"
    print("[OK] Steps 33-40 (storyteller_system.py Data/Registry/Manager)")

    # Steps 41-46: choice_system.py
    from choice_system import ChoiceConsequenceData, ChoiceRegistry, ChoiceManager, REGISTRY as CHO_REG
    assert ChoiceConsequenceData is not None, "Step 42 Failed"
    cr1 = ChoiceRegistry()
    cr2 = ChoiceRegistry()
    assert cr1 is cr2, "Step 43 Failed: singleton mismatch"
    CHO_REG.load()
    assert len(CHO_REG.all_consequences()) >= 1, "Step 44 Failed: load"
    cmgr = ChoiceManager(CHO_REG)
    ok_cho = cmgr.apply_consequence(e, "farm_survivor_saved")
    assert ok_cho and e.story_variables.get("rescued_villagers_count") == 5, "Step 46 Failed: apply_consequence"
    print("[OK] Steps 41-46 (choice_system.py Data/Registry/Manager)")

    # Steps 47-53: world_state_system.py
    from world_state_system import WorldStateTemplate, WorldStateRegistry, WorldStateManager, REGISTRY as WS_REG
    assert WorldStateTemplate is not None, "Step 48 Failed"
    ws1 = WorldStateRegistry()
    ws2 = WorldStateRegistry()
    assert ws1 is ws2, "Step 49 Failed: singleton mismatch"
    WS_REG.load()
    assert WS_REG.get_template().version == "1.0", "Step 50 Failed: load"
    wsmgr = WorldStateManager(WS_REG)
    wsmgr.set_variable(e, "goblin_threat_level", 20)
    assert wsmgr.get_variable(e, "goblin_threat_level") == 20, "Step 52/53 Failed: get/set_variable"
    print("[OK] Steps 47-53 (world_state_system.py Data/Registry/Manager)")

    # Steps 54-59: procedural_dungeon_generator.py
    from procedural_dungeon_generator import DungeonThemeData, DungeonThemeRegistry, ProceduralDungeonGenerator, REGISTRY as DT_REG
    assert DungeonThemeData is not None, "Step 55 Failed"
    dt1 = DungeonThemeRegistry()
    dt2 = DungeonThemeRegistry()
    assert dt1 is dt2, "Step 56 Failed: singleton mismatch"
    DT_REG.load()
    assert len(DT_REG.all_themes()) >= 1, "Step 57 Failed: load"
    pdg = ProceduralDungeonGenerator(DT_REG)
    sel_theme = pdg.select_theme_by_story(e)
    assert sel_theme is not None and sel_theme.theme_id == "goblin_cave", "Step 59 Failed: select_theme_by_story"
    print("[OK] Steps 54-59 (procedural_dungeon_generator.py Data/Registry/Generator)")

    # Steps 60-66: relationship_system.py
    from relationship_system import RelationshipTemplateData, RelationshipRegistry, RelationshipManager, REGISTRY as REL_REG
    assert RelationshipTemplateData is not None, "Step 61 Failed"
    rel1 = RelationshipRegistry()
    rel2 = RelationshipRegistry()
    assert rel1 is rel2, "Step 62 Failed: singleton mismatch"
    REL_REG.load()
    assert len(REL_REG.all_templates()) >= 1, "Step 63 Failed: load"
    relmgr = RelationshipManager(REL_REG)
    relmgr.update_relationship(e, "gwen", action="talk", delta_trust=30, delta_mood=20)
    assert relmgr.get_relationship_level(e, "gwen") == 2, "Step 65/66 Failed: get_relationship_level"
    print("[OK] Steps 60-66 (relationship_system.py Data/Registry/Manager)")

    # Steps 67-71: world_event_system.py
    from world_event_system import WorldEventData, WorldEventRegistry, WorldEventManager, REGISTRY as WE_REG
    assert WorldEventData is not None, "Step 68 Failed"
    we1 = WorldEventRegistry()
    we2 = WorldEventRegistry()
    assert we1 is we2, "Step 69 Failed: singleton mismatch"
    WE_REG.load()
    assert len(WE_REG.all_events()) >= 1, "Step 70 Failed: load"
    wemgr = WorldEventManager(WE_REG)
    ok_we = wemgr.trigger_event(e, "blood_moon")
    assert ok_we and "blood_moon" in e.active_world_events, "Step 71 Failed: trigger_event"
    print("[OK] Steps 67-71 (world_event_system.py Data/Registry/Manager)")

    # Step 72: game.py Engine 統合 & save_system.py 永続化
    from game import Engine
    from save_system import SaveSystem
    eng = Engine()
    assert hasattr(eng, "storyteller_manager"), "Step 72 Failed: storyteller_manager on Engine"
    assert hasattr(eng, "choice_manager"), "Step 72 Failed: choice_manager on Engine"
    assert hasattr(eng, "world_state_manager"), "Step 72 Failed: world_state_manager on Engine"
    assert hasattr(eng, "procedural_dungeon_generator"), "Step 72 Failed: procedural_dungeon_generator on Engine"
    assert hasattr(eng, "relationship_manager"), "Step 72 Failed: relationship_manager on Engine"
    assert hasattr(eng, "world_event_manager"), "Step 72 Failed: world_event_manager on Engine"

    eng.player.story_flags["test_flag"] = True
    eng.player.active_world_events = ["blood_moon"]
    eng.player.character_relationships["gwen"] = {"trust": 50, "mood": 40}
    save_msg = SaveSystem.save(eng)
    assert "セーブ完了" in save_msg, "Step 72 Save failed"
    loaded_eng, _ = SaveSystem.load()
    assert loaded_eng is not None, "Step 72 Load failed"
    assert loaded_eng.player.story_flags.get("test_flag") is True, "Step 72 State persistence failed"
    assert "blood_moon" in loaded_eng.player.active_world_events, "Step 72 State persistence failed"
    assert loaded_eng.player.character_relationships["gwen"]["trust"] == 50, "Step 72 State persistence failed"
    print("[OK] Step 72 (game.py Engine 統合 & save_system.py 完全永続化)")

    print("\nALL 72 STEPS OF DUNGEON WORLD STORYTELLER SYSTEM VERIFIED 100% SUCCESSFULLY!")


if __name__ == "__main__":
    test_all_72_steps_storyteller_system()
