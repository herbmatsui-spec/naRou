"""Coverage tests for skill_eater_world_preview (WorldPreviewManager)."""

from __future__ import annotations

import pytest

from skill_eater_world_preview import WorldPreviewManager


@pytest.fixture
def mgr() -> WorldPreviewManager:
    return WorldPreviewManager()


class TestDefaults:
    def test_two_worlds_defined(self, mgr: WorldPreviewManager) -> None:
        assert set(mgr.next_worlds) == {"W1_Magic_Dominant", "W5_Cyber_Anarchy"}

    def test_default_selection(self, mgr: WorldPreviewManager) -> None:
        assert mgr.selected_target_world == "W1_Magic_Dominant"


class TestWorldPreview:
    def test_default_preview(self, mgr: WorldPreviewManager) -> None:
        res = mgr.get_world_preview()
        assert res["world_id"] == "W1_Magic_Dominant"
        assert res["name"] == "W1: 魔法絶対主義の帝国"
        assert "高魔力警報" in res["preview"]
        assert "Magic" in res["recommended_tags"]

    def test_explicit_world_switch(self, mgr: WorldPreviewManager) -> None:
        res = mgr.get_world_preview("W5_Cyber_Anarchy")
        assert res["world_id"] == "W5_Cyber_Anarchy"
        assert res["name"] == "W5: 電脳無秩序スラム"
        assert mgr.selected_target_world == "W5_Cyber_Anarchy"

    def test_unknown_world_keeps_selection(self, mgr: WorldPreviewManager) -> None:
        res = mgr.get_world_preview("W99_Unknown")
        assert res["world_id"] == "W1_Magic_Dominant"
        assert mgr.selected_target_world == "W1_Magic_Dominant"

    def test_selection_persists_for_later_calls(self, mgr: WorldPreviewManager) -> None:
        mgr.get_world_preview("W5_Cyber_Anarchy")
        res = mgr.get_world_preview()
        assert res["world_id"] == "W5_Cyber_Anarchy"


class TestAnalyzeAndTagSkills:
    def test_recommended_skill(self, mgr: WorldPreviewManager) -> None:
        skills = [{"name": "Fire Bolt", "tags": ["Magic", "Fire"]}]
        tagged = mgr.analyze_and_tag_skills(skills)
        assert tagged[0]["solver_recommended"] is True
        assert tagged[0]["solver_warning"] is False
        assert tagged[0]["recommendation_badge"] == "[★次世界推奨]"

    def test_disadvantaged_skill(self, mgr: WorldPreviewManager) -> None:
        skills = [{"name": "Iron Body", "tags": ["Physical", "Heavy Armor"]}]
        tagged = mgr.analyze_and_tag_skills(skills)
        assert tagged[0]["solver_recommended"] is False
        assert tagged[0]["solver_warning"] is True
        assert tagged[0]["recommendation_badge"] == "[▲非推奨]"

    def test_standard_skill(self, mgr: WorldPreviewManager) -> None:
        skills = [{"name": "Cooking", "tags": ["Life"]}]
        tagged = mgr.analyze_and_tag_skills(skills)
        assert tagged[0]["solver_recommended"] is False
        assert tagged[0]["solver_warning"] is False
        assert tagged[0]["recommendation_badge"] == "[標準]"

    def test_missing_tags_key_treated_as_standard(self, mgr: WorldPreviewManager) -> None:
        tagged = mgr.analyze_and_tag_skills([{"name": "Mystery"}])
        assert tagged[0]["recommendation_badge"] == "[標準]"

    def test_recommended_takes_precedence_over_disadvantaged(self, mgr: WorldPreviewManager) -> None:
        skills = [{"name": "Hybrid", "tags": ["Magic", "Heavy Armor"]}]
        tagged = mgr.analyze_and_tag_skills(skills)
        assert tagged[0]["solver_recommended"] is True
        assert tagged[0]["recommendation_badge"] == "[★次世界推奨]"

    def test_original_skill_dict_not_mutated(self, mgr: WorldPreviewManager) -> None:
        skill = {"name": "Fire Bolt", "tags": ["Magic"]}
        mgr.analyze_and_tag_skills([skill])
        assert "solver_recommended" not in skill

    def test_cyber_world_tags(self, mgr: WorldPreviewManager) -> None:
        mgr.get_world_preview("W5_Cyber_Anarchy")
        skills = [
            {"name": "ICE Break", "tags": ["Hack"]},
            {"name": "Chant", "tags": ["Chant"]},
        ]
        tagged = mgr.analyze_and_tag_skills(skills)
        assert tagged[0]["solver_recommended"] is True
        assert tagged[1]["solver_warning"] is True


class TestUISkillList:
    def test_ui_list_structure(self, mgr: WorldPreviewManager) -> None:
        skills = [
            {"name": "Fire Bolt", "tags": ["Magic"]},
            {"name": "Iron Body", "tags": ["Heavy Armor"]},
            {"name": "Cooking", "tags": ["Life"]},
        ]
        res = mgr.generate_ui_skill_list(skills)
        assert res["target_world"] == "W1: 魔法絶対主義の帝国"
        assert "高魔力警報" in res["preview_description"]
        assert len(res["skills"]) == 3
        assert res["recommended_count"] == 1

    def test_recommended_count_zero(self, mgr: WorldPreviewManager) -> None:
        res = mgr.generate_ui_skill_list([{"name": "x", "tags": ["Life"]}])
        assert res["recommended_count"] == 0

    def test_recommended_count_all(self, mgr: WorldPreviewManager) -> None:
        skills = [{"name": f"s{i}", "tags": ["Hack"]} for i in range(3)]
        mgr.get_world_preview("W5_Cyber_Anarchy")
        res = mgr.generate_ui_skill_list(skills)
        assert res["recommended_count"] == 3
