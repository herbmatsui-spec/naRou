"""
Repository-layer test suite for Elona Masterpiece Edition (v2.0).

Validates that every generated repository correctly indexes and queries the
schema-validated game data exposed through DataManager.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest

from data_manager import DataManager


@pytest.fixture(scope="module")
def dm() -> DataManager:
    return DataManager()


# ----------------------------- ItemRepository -----------------------------


def test_item_count(dm):
    assert len(dm.items.get_all()) > 0


def test_item_get_by_category(dm):
    weapons = dm.items.get_by_category("weapon")
    assert weapons
    assert all(i.category == "weapon" for i in weapons)


def test_item_weapons_armor_consumables(dm):
    assert dm.items.get_weapons()
    assert dm.items.get_armor()
    assert dm.items.get_consumables()


def test_item_query_by_price_range(dm):
    cheap = dm.items.query_by_price_range(0, 100)
    assert all(0 <= i.base_value <= 100 for i in cheap)


def test_item_get_by_material(dm):
    # every item with a material should be indexed
    for item in dm.items.get_all():
        if item.material:
            assert item in dm.items.get_by_material(item.material)


# --------------------------- MonsterRepository ---------------------------


def test_monster_count(dm):
    assert len(dm.monsters.get_all()) > 0


def test_monster_get_by_faction(dm):
    monsters = dm.monsters.get_by_faction("monster")
    assert monsters
    assert all(m.faction == "monster" for m in monsters)


def test_monster_get_by_level_range(dm):
    low = dm.monsters.get_by_level_range(1, 5)
    assert all((m.level or 1) <= 5 for m in low)


def test_monster_bosses(dm):
    bosses = dm.monsters.get_bosses()
    assert all((m.level or 0) >= 50 for m in bosses)


# ------------------------- SkillTreeRepository --------------------------


def test_skill_tree_count(dm):
    assert len(dm.skill_trees.get_all()) > 0


def test_skill_tree_skills(dm):
    for tree_id, tree in dm.skill_trees._data.items():
        tiers = dm.skill_trees.get_tree_skills(tree_id)
        assert len(tiers) == len(tree.tiers)


# ---------------------------- SpellRepository ---------------------------


def test_spell_count(dm):
    assert len(dm.spells.get_all()) > 0


def test_spell_get_by_element(dm):
    spells = dm.spells.get_all()
    elements = {s.element for s in spells}
    for element in elements:
        result = dm.spells.get_by_element(element)
        assert all(s.element == element for s in result)


# ------------------------- SkillFusionRepository ------------------------


def test_skill_fusion_count(dm):
    assert len(dm.skill_fusions.get_all()) > 0


def test_skill_fusion_lookup(dm):
    for fusion in dm.skill_fusions.get_all():
        for result in fusion.result_skills:
            res_val = getattr(result, "root", result)
            found = dm.skill_fusions.get_fusions_for_result(res_val)
            assert fusion in found
        for req in fusion.required_skills:
            req_val = getattr(req, "root", req)
            used = dm.skill_fusions.get_fusions_using_skill(req_val)
            assert fusion in used


# --------------------------- QuestRepository ----------------------------


def test_quest_count(dm):
    assert len(dm.quests.get_all()) > 0


def test_quest_available_for_level(dm):
    available = dm.quests.get_available_for_level(1)
    assert isinstance(available, list)


def test_quest_repeatable(dm):
    repeatable = dm.quests.get_repeatable()
    assert all(q.repeatable for q in repeatable)


# -------------------------- FactionRepository ---------------------------


def test_faction_count(dm):
    assert len(dm.factions.get_all()) > 0


def test_faction_territory_index(dm):
    for faction in dm.factions.get_all():
        for territory in faction.territories:
            assert faction in dm.factions.get_by_territory(territory)


def test_faction_allies_rivals(dm):
    for fid in dm.factions._data:
        allies = dm.factions.get_allies(fid)
        rivals = dm.factions.get_rivals(fid)
        assert all(a is not None for a in allies)
        assert all(r is not None for r in rivals)


# ------------------------ AchievementRepository -------------------------


def test_achievement_count(dm):
    assert len(dm.achievements.get_all()) > 0


def test_achievement_visible_hidden(dm):
    visible = dm.achievements.get_visible()
    hidden = dm.achievements.get_hidden()
    total = len(dm.achievements.get_all())
    assert len(visible) + len(hidden) == total


# --------------------------- TitleRepository ----------------------------


def test_title_count(dm):
    assert len(dm.titles.get_all()) > 0


def test_title_by_category(dm):
    for title in dm.titles.get_all():
        assert title in dm.titles.get_by_category(title.category)


def test_title_visible_hidden(dm):
    visible = dm.titles.get_visible()
    hidden = dm.titles.get_hidden()
    total = len(dm.titles.get_all())
    assert len(visible) + len(hidden) == total


# ----------------------------- JobRepository ----------------------------


def test_job_count(dm):
    assert len(dm.jobs.get_all()) > 0


def test_job_by_tier(dm):
    for job in dm.jobs.get_all():
        assert job in dm.jobs.get_by_tier(job.tier)


def test_job_unlock_conditions(dm):
    job = dm.jobs.get_all()[0]
    cond = job.unlock_conditions
    # unlock condition model must expose the documented fields or keys
    if isinstance(cond, dict):
        assert "level" in cond or hasattr(cond, "level") or cond == {}
    else:
        assert hasattr(cond, "level")
        assert hasattr(cond, "skills")
        assert hasattr(cond, "stats")


# ----------------------------- GodRepository ----------------------------


def test_god_count(dm):
    assert len(dm.gods.get_all()) > 0


def test_god_domains(dm):
    for god in dm.gods.get_all():
        for domain in god.domain.split("・"):
            assert god in dm.gods.get_by_domain(domain.strip())


# ------------------------ DungeonThemeRepository ------------------------


def test_dungeon_theme_count(dm):
    assert len(dm.dungeon_themes.get_all()) > 0


def test_dungeon_theme_for_level(dm):
    for theme in dm.dungeon_themes.get_all():
        if theme.min_level is not None and theme.max_level is not None:
            result = dm.dungeon_themes.get_for_level(theme.min_level)
            assert theme in result


# --------------------------- GuildRepository ----------------------------


def test_guild_count(dm):
    assert len(dm.guilds.get_all()) > 0


def test_guild_by_location(dm):
    for guild in dm.guilds.get_all():
        assert guild in dm.guilds.get_by_location(guild.hall_location)


# --------------------------- DataManager --------------------------------


def test_data_manager_create_item(dm):
    item = dm.create_item("longsword", quality="god", material="rubynus")
    assert item.name
    assert item.material == "rubynus"
    assert item.quality == "god"


def test_data_manager_create_monster(dm):
    mob = dm.create_monster("minotaur", level_scale=3)
    assert mob.name
    assert mob.max_hp > 0
    assert isinstance(mob.ai_type, str)


def test_data_manager_validate_all_data(dm):
    errors = dm.validate_all_data()
    assert errors == []
