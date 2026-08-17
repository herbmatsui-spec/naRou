"""
Elona Roguelike - Entity Component System (ECS) Data Components
Modularized state storage for Subsystems (Titles, Guilds, Achievements, Reincarnation, Story, Skills, etc.)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Any, Optional


@dataclass
class TitleComponent:
    """称号およびプレイヤー実績統計用コンポーネント"""
    titles: List[str] = field(default_factory=list)
    equipped_title: Optional[str] = None
    title_notifications: List[str] = field(default_factory=list)
    kill_counts: Dict[str, int] = field(default_factory=dict)
    craft_counts: Dict[str, int] = field(default_factory=dict)
    max_dungeon_depth: int = 0
    near_death_count: int = 0
    total_turns: int = 0
    gold: int = 0


@dataclass
class GuildFactionComponent:
    """ギルド・派閥・ランキング用コンポーネント"""
    guild_id: Optional[str] = None
    guild_rank: str = "none"
    guild_contribution: int = 0
    guild_role: Optional[str] = None
    faction_reputation: Dict[str, int] = field(default_factory=dict)
    completed_faction_events: List[str] = field(default_factory=list)
    ranking_titles: List[str] = field(default_factory=list)
    guild_quest_progress: Dict[str, int] = field(default_factory=dict)


@dataclass
class AchievementComponent:
    """実績・トロフィー・メタ進行用コンポーネント"""
    achievements: List[str] = field(default_factory=list)
    achievement_progress: Dict[str, int] = field(default_factory=dict)
    achievement_timers: Dict[str, int] = field(default_factory=dict)
    monster_killed_types: Dict[str, int] = field(default_factory=dict)
    unique_items_obtained: List[str] = field(default_factory=list)
    social_points: int = 0
    weekly_play_time: int = 0
    total_level_earned: int = 0
    permanent_bonuses: Dict[str, int] = field(default_factory=dict)
    meta_progression: Dict[str, int] = field(default_factory=dict)
    dungeon_floors_visited: Set[Tuple[int, int]] = field(default_factory=set)
    play_time_seconds: int = 0
    last_festival_check: str = ""
    friend_helps: int = 0
    special_items_combo: List[str] = field(default_factory=list)
    achievement_notifications: List[str] = field(default_factory=list)


@dataclass
class ReincarnationComponent:
    """輪廻転生・ニューゲーム+用コンポーネント"""
    reincarnation_count: int = 0
    karma_law_chaos: int = 0
    karma_good_evil: int = 0
    legacy_skills: List[str] = field(default_factory=list)
    unlocked_reincarnation_dungeons: List[str] = field(default_factory=list)
    collected_fragments: List[Dict[str, Any]] = field(default_factory=list)
    favor: Dict[str, int] = field(default_factory=dict)
    inheritance_selection: Dict[str, Any] = field(default_factory=dict)
    challenge_progress: Dict[str, int] = field(default_factory=dict)
    cycle_modifiers: List[Dict[str, Any]] = field(default_factory=list)
    legacy_records: List[Dict[str, Any]] = field(default_factory=list)



@dataclass
class SkillTreeJobComponent:
    """スキルツリーおよびジョブシステム用コンポーネント"""
    skill_tree_progress: Dict[str, List[str]] = field(default_factory=dict)
    skill_points: int = 0
    total_skill_points_earned: int = 0
    job: str = "novice"
    job_level: int = 1
    job_exp: int = 0
    previous_jobs: List[str] = field(default_factory=list)
    mastered_jobs: List[str] = field(default_factory=list)
    mastered_exclusive_skills: List[str] = field(default_factory=list)
    inherited_skills: List[str] = field(default_factory=list)


@dataclass
class SkillFusionComponent:
    """スキル合成・進化・覚醒用コンポーネント"""
    skill_fusion_materials: Dict[str, int] = field(default_factory=dict)
    skill_evolution: Dict[str, str] = field(default_factory=dict)
    awakened_skills: List[str] = field(default_factory=list)
    skill_traits: Dict[str, Dict[str, float]] = field(default_factory=dict)
    equipped_skills: List[str] = field(default_factory=list)
    inheritable_skills: List[str] = field(default_factory=list)
    skill_specialization: Dict[str, str] = field(default_factory=dict)
    fusion_chain_progress: Dict[str, int] = field(default_factory=dict)
    skill_archive_progress: Dict[str, bool] = field(default_factory=dict)


@dataclass
class StorytellerComponent:
    """ダンジョン・ワールド自動生成ストーリーテラー用コンポーネント"""
    story_flags: Dict[str, bool] = field(default_factory=dict)
    story_variables: Dict[str, Any] = field(default_factory=dict)
    story_choices_made: List[str] = field(default_factory=list)
    world_state_version: str = "1.0"
    player_legacy: Dict[str, Any] = field(default_factory=dict)
    character_relationships: Dict[str, Dict[str, int]] = field(default_factory=dict)
    memory_fragments: List[str] = field(default_factory=list)
    active_world_events: List[str] = field(default_factory=list)
    completed_storylines: List[str] = field(default_factory=list)
    available_storylines: List[str] = field(default_factory=list)
    story_notifications: List[Dict[str, Any]] = field(default_factory=list)
    current_choice_prompt: Optional[Dict[str, Any]] = None
    ending_progress: Dict[str, int] = field(default_factory=dict)
