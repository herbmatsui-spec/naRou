"""
Elona Roguelike - Entity Component System (ECS) Data Components
Modularized state storage for Subsystems (Titles, Guilds, Achievements, Reincarnation, Story, Skills, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttributesComponent:
    """主能力 8種 - ECSコンポーネントとして管理 (Step 2)"""

    strength: int = 10
    endurance: int = 10
    dexterity: int = 10
    perception: int = 10
    learning: int = 10
    will: int = 10
    magic: int = 10
    charisma: int = 10

    def to_dict(self) -> dict[str, int]:
        return {
            "strength": self.strength,
            "endurance": self.endurance,
            "dexterity": self.dexterity,
            "perception": self.perception,
            "learning": self.learning,
            "will": self.will,
            "magic": self.magic,
            "charisma": self.charisma,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributesComponent:
        return cls(
            strength=data.get("strength", 10),
            endurance=data.get("endurance", 10),
            dexterity=data.get("dexterity", 10),
            perception=data.get("perception", 10),
            learning=data.get("learning", 10),
            will=data.get("will", 10),
            magic=data.get("magic", 10),
            charisma=data.get("charisma", 10),
        )


@dataclass
class TitleComponent:
    """称号およびプレイヤー実績統計用コンポーネント"""

    titles: list[str] = field(default_factory=list)
    equipped_title: str | None = None
    title_notifications: list[str] = field(default_factory=list)
    kill_counts: dict[str, int] = field(default_factory=dict)
    craft_counts: dict[str, int] = field(default_factory=dict)
    max_dungeon_depth: int = 0
    near_death_count: int = 0
    total_turns: int = 0
    gold: int = 0


@dataclass
class GuildFactionComponent:
    """ギルド・派閥・ランキング用コンポーネント"""

    guild_id: str | None = None
    guild_rank: str = "none"
    guild_contribution: int = 0
    guild_role: str | None = None
    faction_reputation: dict[str, int] = field(default_factory=dict)
    completed_faction_events: list[str] = field(default_factory=list)
    ranking_titles: list[str] = field(default_factory=list)
    guild_quest_progress: dict[str, int] = field(default_factory=dict)


@dataclass
class AchievementComponent:
    """実績・トロフィー・メタ進行用コンポーネント"""

    achievements: list[str] = field(default_factory=list)
    achievement_progress: dict[str, int] = field(default_factory=dict)
    achievement_timers: dict[str, int] = field(default_factory=dict)
    monster_killed_types: dict[str, int] = field(default_factory=dict)
    unique_items_obtained: list[str] = field(default_factory=list)
    social_points: int = 0
    weekly_play_time: int = 0
    total_level_earned: int = 0
    permanent_bonuses: dict[str, int] = field(default_factory=dict)
    meta_progression: dict[str, int] = field(default_factory=dict)
    dungeon_floors_visited: set[tuple[int, int]] = field(default_factory=set)
    play_time_seconds: int = 0
    last_festival_check: str = ""
    friend_helps: int = 0
    special_items_combo: list[str] = field(default_factory=list)
    achievement_notifications: list[str] = field(default_factory=list)


@dataclass
class ReincarnationComponent:
    """輪廻転生・ニューゲーム+用コンポーネント"""

    reincarnation_count: int = 0
    karma_law_chaos: int = 0
    karma_good_evil: int = 0
    legacy_skills: list[str] = field(default_factory=list)
    unlocked_reincarnation_dungeons: list[str] = field(default_factory=list)
    collected_fragments: list[dict[str, Any]] = field(default_factory=list)
    favor: dict[str, int] = field(default_factory=dict)
    inheritance_selection: dict[str, Any] = field(default_factory=dict)
    challenge_progress: dict[str, int] = field(default_factory=dict)
    cycle_modifiers: list[dict[str, Any]] = field(default_factory=list)
    legacy_records: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SkillTreeJobComponent:
    """スキルツリーおよびジョブシステム用コンポーネント"""

    skill_tree_progress: dict[str, list[str]] = field(default_factory=dict)
    skill_points: int = 0
    total_skill_points_earned: int = 0
    job: str = "novice"
    job_level: int = 1
    job_exp: int = 0
    previous_jobs: list[str] = field(default_factory=list)
    mastered_jobs: list[str] = field(default_factory=list)
    mastered_exclusive_skills: list[str] = field(default_factory=list)
    inherited_skills: list[str] = field(default_factory=list)
    learned_passive_skills: list[str] = field(default_factory=list)
    inherited_stat_bonus: int = 0


@dataclass
class SkillFusionComponent:
    """スキル合成・進化・覚醒用コンポーネント"""

    skill_fusion_materials: dict[str, int] = field(default_factory=dict)
    skill_evolution: dict[str, str] = field(default_factory=dict)
    awakened_skills: list[str] = field(default_factory=list)
    skill_traits: dict[str, dict[str, float]] = field(default_factory=dict)
    equipped_skills: list[str] = field(default_factory=list)
    inheritable_skills: list[str] = field(default_factory=list)
    skill_specialization: dict[str, str] = field(default_factory=dict)
    fusion_chain_progress: dict[str, int] = field(default_factory=dict)
    skill_archive_progress: dict[str, bool] = field(default_factory=dict)


@dataclass
class ProceduralQuestComponent:
    """プロシージャル・クエスト生成用コンポーネント (Steps 34-35)"""

    active_board: list[dict[str, Any]] = field(default_factory=list)
    accepted_quests: list[dict[str, Any]] = field(default_factory=list)
    completed_quest_ids: list[str] = field(default_factory=list)
    completed_count: int = 0
    generated_total_count: int = 0
    board_seed: int = 0
    active_chains: dict[str, list[str]] = field(
        default_factory=dict
    )  # 連鎖状態 (Step 23)


@dataclass
class StorytellerComponent:
    """ダンジョン・ワールド自動生成ストーリーテラー用コンポーネント"""

    story_flags: dict[str, bool] = field(default_factory=dict)
    story_variables: dict[str, Any] = field(default_factory=dict)
    story_choices_made: list[str] = field(default_factory=list)
    world_state_version: str = "1.0"
    player_legacy: dict[str, Any] = field(default_factory=dict)
    character_relationships: dict[str, dict[str, int]] = field(default_factory=dict)
    memory_fragments: list[str] = field(default_factory=list)
    active_world_events: list[str] = field(default_factory=list)
    completed_storylines: list[str] = field(default_factory=list)
    available_storylines: list[str] = field(default_factory=list)
    story_notifications: list[dict[str, Any]] = field(default_factory=list)
    current_choice_prompt: dict[str, Any] | None = None
    ending_progress: dict[str, int] = field(default_factory=dict)


@dataclass
class ArchaeologyComponent:
    """考古学・発掘・解読メタゲーム用コンポーネント (Steps 10-12)"""

    excavated_sites: list[str] = field(default_factory=list)  # 発掘済み遺跡サイト id
    collected_fragments: list[str] = field(
        default_factory=list
    )  # 収集済み断片 id（生・未解読含む）
    decoded_fragments: list[str] = field(default_factory=list)  # 解読済み断片 id
    owned_keys: list[str] = field(default_factory=list)  # 所持デコーダー鍵 id
    reached_truths: list[str] = field(default_factory=list)  # 到達済み真理ノード id
    leaned_endings: dict[str, str] = field(
        default_factory=dict
    )  # truth_id -> 寄り先 ending_id
    interpretation_notes: dict[str, str] = field(
        default_factory=dict
    )  # truth_id -> プレイヤー解釈文
    decoder_hints_seen: list[str] = field(
        default_factory=list
    )  # 蓄積された解読ヒント（気づき）
    decipherment_gauge: int = 0  # 解読ゲージ（破片収集で上昇）


@dataclass
class BaseStatsComponent:
    """HP/MPの基本ステータス用ECSコンポーネント"""

    hp: int = 50
    max_hp: int = 50
    mp: int = 20
    max_mp: int = 20


@dataclass
class EconomyComponent:
    """所持金・経済用ECSコンポーネント"""

    gold: int = 0
    platinum: int = 0


@dataclass
class LevelComponent:
    """レベル・経験値・スキルポイント用ECSコンポーネント"""

    level: int = 1
    exp: int = 0
    exp_next: int = 100
    skill_points: int = 0
    total_skill_points_earned: int = 0


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str | None = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager

    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
