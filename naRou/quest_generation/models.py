"""
プロシージャル・クエスト生成システム - データモデル (Steps 9-14)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from typing_extensions import Self

logger = logging.getLogger(__name__)

# 敵名のローマ字↔カタカナ/日本語ゆれを吸収する軽量マップ（ゲーム内実体名との照合用）
_ENEMY_NAME_MAP_CACHE = None


def _get_enemy_name_map():
    "Load and return enemy name aliases map with caching"
    global _ENEMY_NAME_MAP_CACHE
    if _ENEMY_NAME_MAP_CACHE is None:
        try:
            enemy_map_path = os.path.join(
                os.path.dirname(__file__), "data", "enemy_name_aliases.yaml"
            )
            if os.path.exists(enemy_map_path):
                with open(enemy_map_path, encoding="utf-8") as f:
                    _ENEMY_NAME_MAP_CACHE = yaml.safe_load(f) or {}
            else:
                # Fallback to hardcoded map if file not found
                _ENEMY_NAME_MAP_CACHE = {
                    "goblin": ["ゴブリン", "goblin", "ゴブリ"],
                    "slime": ["スライム", "ぷち", "slime"],
                    "wolf": ["オオカミ", "ウルフ", "wolf"],
                    "frost_wolf": ["フロストウルフ", "ice wolf", "frost_wolf"],
                    "bat": ["コウモリ", "bat"],
                    "cave_bear": ["ケイブベア", "cave_bear", "熊"],
                    "bear": ["ベア", "bear", "熊"],
                    "skeleton": ["スケルトン", "スケルトン"],
                    "ghost": ["ゴースト", "ゴースト"],
                    "golem": ["ゴーレム", "ゴーレム"],
                    "fire_lizard": ["ファイアリザード", "ファイアリザード"],
                    "magma_elemental": ["マグマエレメンタル", "マグマエレメンタル"],
                    "ifrit": ["イフリート", "イフリート"],
                    "yeti": ["イエティ", "イエティ"],
                    "ice_sprite": ["アイススプライト", "アイススプライト"],
                    "crocodile": ["クロコダイル", "ワニ", "クロコダイル"],
                    "venom_toad": ["ベノムトード", "ベノムトード"],
                    "abyssal_horror": ["アビサルホラー", "アビサルホラー"],
                    "void_lord": ["ヴォイドロード", "ヴォイドロード"],
                    "nightmare": ["ナイトメア", "ナイトメア"],
                    "bandit": ["バンディット", "バンディット", "盗賊"],
                    "stray_dog": ["野良犬", "野良犬"],
                    "pickpocket": ["スリ", "スリ"],
                    "dog": ["犬", "犬"],
                }
        except Exception as e:
            logger.warning("Failed to load enemy name map: %s", e)
            # Emergency fallback
            _ENEMY_NAME_MAP_CACHE = {"goblin": ["ゴブリン", "goblin", "ゴブリ"]}
    return _ENEMY_NAME_MAP_CACHE


if TYPE_CHECKING:
    from game import Engine
    from naRou.dungeon_quest_feedback import DungeonGenerationFeedback
    from naRou.ecs.entity import Entity


# Step 9: QuestArchetype
@dataclass
class QuestArchetype:
    """クエストアーキタイプ（形態）"""

    id: str = ""
    name: str = ""
    objective_type: str = "kill"  # kill/collect/visit/escort/explore/rescue/delivery
    title_template: str = "{setting}のクエスト"
    desc_template: str = "{setting}で任務を遂行せよ。"
    reward_weight: float = 1.0
    base_complexity: int = 1


# Step 10: DifficultyTier
@dataclass
class DifficultyTier:
    """難易度ティア（指数スケーリング）"""

    id: str = ""
    name: str = ""
    level_range: list[int] = field(default_factory=lambda: [1, 5])
    enemy_multiplier: float = 1.0
    objective_complexity: float = 1.0
    recommended_power: int = 10


# Step 11: RewardTable
@dataclass
class RewardTable:
    """報酬テーブル"""

    id: str = ""
    name: str = ""
    gold_range: list[int] = field(default_factory=lambda: [20, 80])
    exp_range: list[int] = field(default_factory=lambda: [10, 40])
    item_pool: list[str] = field(default_factory=list)
    bonus: dict[str, int] = field(default_factory=dict)


# Step 12: StageSetting
@dataclass
class StageSetting:
    """舞台設定"""

    id: str = ""
    name: str = ""
    flavor: str = ""
    enemy_pool: list[str] = field(default_factory=list)
    hazard: str = ""
    depth_modifier: float = 1.0
    environmental_modifier: float = 1.0


# Step 13: NPCQuestTheme
@dataclass
class NPCQuestTheme:
    """NPC個別クエストテーマ"""

    npc_type: str = ""
    quest_pool: list[str] = field(default_factory=list)
    relationship_gate: int = 1
    flavor: str = "{npc}「頼んだよ。」"


# Step 14: QuestObjectiveSpec / GeneratedQuest
@dataclass
class QuestObjectiveSpec:
    """生成されたクエストの1目的"""

    objective_id: str = ""
    description: str = ""
    target_type: str = "kill"
    target_id: str = ""
    required_count: int = 1
    current_count: int = 0
    cascade_bonus: dict[str, int] = field(default_factory=dict)  # 連鎖累積報酬 (Step 14)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "cascade_bonus": self.cascade_bonus,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> QuestObjectiveSpec:
        return cls(
            objective_id=d.get("objective_id", ""),
            description=d.get("description", ""),
            target_type=d.get("target_type", "kill"),
            target_id=d.get("target_id", ""),
            required_count=d.get("required_count", 1),
            current_count=d.get("current_count", 0),
            cascade_bonus=d.get("cascade_bonus", {}),
        )


@dataclass
class GeneratedQuest:
    """自動生成されたクエスト（組み合わせの実体）"""

    quest_id: str = ""
    title: str = ""
    description: str = ""
    source_type: str = "board"  # board / dungeon / npc
    archetype_id: str = ""
    difficulty_id: str = ""
    reward_id: str = ""
    setting_id: str = ""
    npc_id: str | None = None
    seed: int = 0
    recommended_level: int = 1
    objectives: list[QuestObjectiveSpec] = field(default_factory=list)
    reward: dict[str, Any] = field(default_factory=dict)
    expires: int = 0
    chain_id: str = ""  # 連鎖識別子 (Step 13)
    parent_id: str = ""  # 親クエストID (Step 13)
    depth: int = 0  # 連鎖深度 (Step 13)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "archetype_id": self.archetype_id,
            "difficulty_id": self.difficulty_id,
            "reward_id": self.reward_id,
            "setting_id": self.setting_id,
            "npc_id": self.npc_id,
            "seed": self.seed,
            "recommended_level": self.recommended_level,
            "objectives": [o.to_dict() for o in self.objectives],
            "reward": self.reward,
            "expires": self.expires,
            "chain_id": self.chain_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GeneratedQuest:
        return cls(
            quest_id=d.get("quest_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            source_type=d.get("source_type", "board"),
            archetype_id=d.get("archetype_id", ""),
            difficulty_id=d.get("difficulty_id", ""),
            reward_id=d.get("reward_id", ""),
            setting_id=d.get("setting_id", ""),
            npc_id=d.get("npc_id"),
            seed=d.get("seed", 0),
            recommended_level=d.get("recommended_level", 1),
            objectives=[QuestObjectiveSpec.from_dict(o) for o in d.get("objectives", [])],
            reward=d.get("reward", {}),
            expires=d.get("expires", 0),
            chain_id=d.get("chain_id", ""),
            parent_id=d.get("parent_id", ""),
            depth=d.get("depth", 0),
        )

    def is_completed(self) -> bool:
        return all(o.current_count >= o.required_count for o in self.objectives)
