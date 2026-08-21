"""
Save Data Migration Pipeline for naRou
Handles backwards-compatibility, schema migrations (v1 -> v2), and missing default fields.
"""

from __future__ import annotations

from typing import Any

from components import (
    AchievementComponent,
    BaseStatsComponent,
    EconomyComponent,
    GuildFactionComponent,
    LevelComponent,
    ProceduralQuestComponent,
    ReincarnationComponent,
    SkillFusionComponent,
    SkillTreeJobComponent,
    StorytellerComponent,
    TitleComponent,
)

DEFAULT_FIELD_FACTORIES: dict[str, Any] = {
    # リスト型
    "titles": list,
    "title_notifications": list,
    "pets": list,
    "pet_fusion_history": list,
    "achievements": list,
    "unique_items_obtained": list,
    "special_items_combo": list,
    "achievement_notifications": list,
    "legacy_skills": list,
    "unlocked_reincarnation_dungeons": list,
    "collected_fragments": list,
    "awakened_skills": list,
    "equipped_skills": list,
    "inheritable_skills": list,
    "story_choices_made": list,
    "memory_fragments": list,
    "active_world_events": list,
    "completed_storylines": list,
    "available_storylines": list,
    "story_notifications": list,
    "previous_jobs": list,
    "mastered_jobs": list,
    "mastered_exclusive_skills": list,
    "inherited_skills": list,
    "completed_faction_events": list,
    "ranking_titles": list,
    "cycle_modifiers": list,
    "legacy_records": list,
    # 集合型
    "dungeon_floors_visited": set,
    "completed_tutorials": set,
    # None/文字列
    "equipped_title": lambda: None,
    "current_choice_prompt": lambda: None,
    "pending_tutorial_popup": lambda: None,
    "world_state_version": lambda: "1.0",
    "last_festival_check": lambda: "",
    "guild_id": lambda: None,
    "guild_role": lambda: None,
    "guild_rank": lambda: "none",
    "job": lambda: "novice",
    "save_version": lambda: "2.0.0",
    # 辞書型
    "kill_counts": dict,
    "craft_counts": dict,
    "achievement_progress": dict,
    "achievement_timers": dict,
    "monster_killed_types": dict,
    "permanent_bonuses": dict,
    "meta_progression": dict,
    "favor": dict,
    "inheritance_selection": dict,
    "challenge_progress": dict,
    "skill_fusion_materials": dict,
    "skill_evolution": dict,
    "skill_traits": dict,
    "skill_specialization": dict,
    "fusion_chain_progress": dict,
    "skill_archive_progress": dict,
    "story_flags": dict,
    "story_variables": dict,
    "player_legacy": dict,
    "character_relationships": dict,
    "ending_progress": dict,
    "skill_tree_progress": dict,
    "faction_reputation": dict,
    "guild_quest_progress": dict,
    "excavated_sites": list,
    "decoded_fragments": list,
    "owned_keys": list,
    "reached_truths": list,
    "leaned_endings": dict,
    "interpretation_notes": dict,
    "decoder_hints_seen": list,
    # World A (Skill Eater)
    "skill_eater_skills": dict,
    "devour_stats": dict,
    "world_a_unlocked": lambda: False,
    "toxicity_level": int,
    "slum_reputation": int,
    # 数値型
    "karma_law_chaos": int,
    "karma_good_evil": int,
    "reincarnation_count": int,
    "max_dungeon_depth": int,
    "near_death_count": int,
    "total_turns": int,
    "gold": int,
    "social_points": int,
    "weekly_play_time": int,
    "total_level_earned": int,
    "play_time_seconds": int,
    "friend_helps": int,
    "skill_points": int,
    "total_skill_points_earned": int,
    "job_level": lambda: 1,
    "job_exp": int,
    "guild_contribution": int,
}

REQUIRED_COMPONENTS = [
    TitleComponent,
    GuildFactionComponent,
    AchievementComponent,
    ReincarnationComponent,
    SkillTreeJobComponent,
    SkillFusionComponent,
    StorytellerComponent,
    ProceduralQuestComponent,
    BaseStatsComponent,
    EconomyComponent,
    LevelComponent,
]


class MigrationPipeline:
    """Manages data transformations between versions and populating defaults."""

    @classmethod
    def ensure_entity_compatibility(cls, player: Any) -> None:
        """Ensure entity has all required ECS components and default fields."""
        if not player:
            return

        if not hasattr(player, "components") or not isinstance(player.components, dict):
            player.components = {}

        for comp_cls in REQUIRED_COMPONENTS:
            if comp_cls not in player.components:
                player.components[comp_cls] = comp_cls()

        for field_name, factory in DEFAULT_FIELD_FACTORIES.items():
            if not hasattr(player, field_name):
                setattr(player, field_name, factory())

    @classmethod
    def migrate(
        cls, data: dict[str, Any], target_version: str = "2.0.0"
    ) -> dict[str, Any]:
        """Apply sequential migrations from current save_version up to target_version."""
        version = data.get("save_version", "1.0.0")
        if version == "1.0.0":
            data = cls._migrate_v1_to_v2(data)
        return data

    @classmethod
    def _migrate_v1_to_v2(cls, data: dict[str, Any]) -> dict[str, Any]:
        """v1.0.0 -> v2.0.0 JSON/Dict schema migration."""
        data["save_version"] = "2.0.0"
        if "player" in data and isinstance(data["player"], dict):
            p = data["player"]
            if "components" not in p:
                p["components"] = {}
        return data
