"""
NPC Relationship Simulation - Core Data Models and Enums
Step 1: Core relationship data models and enums
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class RelationshipType(Enum):
    """関係タイプの列挙型"""

    FAVORABILITY = "favorability"  # 好感度
    FACTION = "faction"  # 派閥所属・対立
    ROMANCE = "romance"  # 恋愛関係
    MENTORSHIP = "mentorship"  # 師弟関係
    BETRAYAL = "betrayal"  # 裏切り・信頼失墜
    FAMILY = "family"  # 家族関係
    RIVALRY = "rivalry"  # 競争関係
    FRIENDSHIP = "friendship"  # 友情
    ENMITY = "enmity"  # 敵対関係
    BUSINESS = "business"  # 取引関係


class RelationshipLevel(IntEnum):
    """関係レベル（-100〜+100の範囲）"""

    MAXIMUM_HATRED = -100
    VERY_HATRED = -80
    HATRED = -60
    DISLIKED = -40
    COOL = -20
    NEUTRAL = 0
    FRIENDLY = 20
    LIKED = 40
    VERY_LIKED = 60
    TRUSTED = 80
    MAXIMUM_TRUST = 100


class InteractionType(Enum):
    """関係変化のトリガータイプ"""

    TALK = "talk"  # 会話
    GIFT = "gift"  # 贈り物
    QUEST_COOPERATION = "quest_cooperation"  # クエスト協力
    QUEST_CONFLICT = "quest_conflict"  # クエストでの衝突
    COMBAT_ALLY = "combat_ally"  # 戦闘での同盟
    COMBAT_ENEMY = "combat_enemy"  # 戦闘での敵対
    RESCUE = "rescue"  # 救出
    BETRAYAL = "betrayal"  # 裏切り
    CONFESSION = "confession"  # 告白
    ARGUMENT = "argument"  # 喧嘩
    TRADE = "trade"  # 取引
    KNOWLEDGE_SHARE = "knowledge_share"  # 知識共有
    EMOTIONAL_SUPPORT = "emotional_support"  # 感情的支援


class FactionAffiliation(Enum):
    """派閥所属タイプ"""

    NEUTRAL = "neutral"  # 中立
    ALLIED = "allied"  # 同盟
    MEMBER = "member"  # 正式メンバー
    LEADER = "leader"  # 指導者
    RIVAL = "rival"  # 競争相手
    HOSTILE = "hostile"  # 敵対
    OUTLAW = "outlaw"  # 追放者


@dataclass
class RelationshipModifier:
    """関係変化の修正子"""

    interaction_type: InteractionType
    amount: int  # 変化量（-100〜+100）
    multiplier: float = 1.0  # 倍率（パーソナリティ等による調整）
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)

    def get_effective_amount(self) -> int:
        """効果的な変化量を取得"""
        return int(self.amount * self.multiplier)


@dataclass
class RelationshipEdge:
    """関係エッジ（キャラクター間の関係）"""

    source_id: str  # ソースキャラクターID
    target_id: str  # ターゲットキャラクターID
    relationship_type: RelationshipType
    level: int = 0  # -100〜+100の関係レベル
    modifiers: list[RelationshipModifier] = field(default_factory=list)
    decay_rate: float = 0.01  # 時間経過による減衰率（0-1）
    last_interaction: float = field(default_factory=time.time)
    is_mutual: bool = True  # 双方向関係か（片思い等のため）

    def add_modifier(self, modifier: RelationshipModifier) -> None:
        """修正子を追加し、関係レベルを更新"""
        self.modifiers.append(modifier)
        self.level = max(-100, min(100, self.level + modifier.get_effective_amount()))
        self.last_interaction = time.time()

    def get_level_category(self) -> RelationshipLevel:
        """現在のレベルカテゴリを取得"""
        for level in reversed(list(RelationshipLevel)):
            if self.level >= level.value:
                return level
        return RelationshipLevel.MAXIMUM_HATRED

    def apply_decay(self, current_time: float | None = None) -> int:
        """時間経過による減衰を適用"""
        if current_time is None:
            current_time = time.time()

        hours_passed = (current_time - self.last_interaction) / 3600
        if hours_passed < 1:  # 1時間未満は減衰適用しない
            return 0

        decay_amount = int(
            self.level * self.decay_rate * hours_passed / 24
        )  # 日単位で調整
        if decay_amount != 0:
            old_level = self.level
            self.level = max(-100, min(100, self.level - decay_amount))
            return self.level - old_level
        return 0


@dataclass
class RelationshipNode:
    """関係ノード（キャラクター）"""

    character_id: str
    name: str
    personality_traits: dict[str, float] = field(default_factory=dict)  # Big Five等
    faction_affiliations: dict[str, FactionAffiliation] = field(default_factory=dict)
    memory_fragments: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_personality_trait(self, trait: str, value: float) -> None:
        """パーソナリティ特性を追加（0.0〜1.0の範囲）"""
        self.personality_traits[trait] = max(0.0, min(1.0, value))

    def set_faction_affiliation(
        self, faction_id: str, affiliation: FactionAffiliation
    ) -> None:
        """派閥所属を設定"""
        self.faction_affiliations[faction_id] = affiliation


@dataclass
class RelationshipTemplate:
    """関係テンプレート（YAMLからロードされるデフォルト設定）"""

    template_id: str
    name: str
    relationship_type: RelationshipType
    initial_level: int = 0
    decay_rate: float = 0.01
    interaction_effects: list[dict[str, Any]] = field(default_factory=list)
    benefits_at_levels: dict[str, str] = field(default_factory=dict)
    memory_triggers: list[str] = field(default_factory=list)
    # 拡張フィールド
    romance_potential: float = 0.0  # 0.0〜1.0
    betrayal_risk: float = 0.0  # 0.0〜1.0
    mentorship_value: float = 0.0  # 0.0〜1.0
    faction_influence: float = 0.0  # 0.0〜1.0
