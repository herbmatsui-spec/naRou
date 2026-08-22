"""
NPC Relationship Simulation - NPC Personality and Archetypes
Step 13: NPC personality traits and archetypes
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import InteractionType, RelationshipType


class PersonalityTrait(Enum):
    """ビッグファイブ（5因子）パーソナリティ特性"""

    OPENNESS = "openness"  # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 誠実性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 協調性
    NEUROTICISM = "neuroticism"  # 神経症傾向


class CharacterArchetype(Enum):
    """キャラクターアーキタイプ"""

    HERO = "hero"  # 英雄
    VILLAIN = "villain"  # 悪役
    SAGE = "sage"  # 賢者
    JESTER = "jester"  # 道化
    GUARDIAN = "guardian"  # 守護者
    TRICKSTER = "trickster"  # いたずら者
    MENTOR = "mentor"  # 導師
    RIVAL = "rival"  # 好敵手
    LOVER = "lover"  # 恋人
    OUTCAST = "outcast"  # はみ出し者
    LEADER = "leader"  # 指導者
    FOLLOWER = "follower"  # 従者


# 各アーキタイプのデフォルトパーソナリティプロファイル
ARCHETYPE_PROFILES: dict[CharacterArchetype, dict[PersonalityTrait, float]] = {
    CharacterArchetype.HERO: {
        PersonalityTrait.OPENNESS: 0.7,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.8,
        PersonalityTrait.EXTRAVERSION: 0.6,
        PersonalityTrait.AGREEABLENESS: 0.7,
        PersonalityTrait.NEUROTICISM: 0.3,
    },
    CharacterArchetype.VILLAIN: {
        PersonalityTrait.OPENNESS: 0.5,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.6,
        PersonalityTrait.EXTRAVERSION: 0.5,
        PersonalityTrait.AGREEABLENESS: 0.2,
        PersonalityTrait.NEUROTICISM: 0.6,
    },
    CharacterArchetype.SAGE: {
        PersonalityTrait.OPENNESS: 0.9,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.8,
        PersonalityTrait.EXTRAVERSION: 0.3,
        PersonalityTrait.AGREEABLENESS: 0.6,
        PersonalityTrait.NEUROTICISM: 0.2,
    },
    CharacterArchetype.JESTER: {
        PersonalityTrait.OPENNESS: 0.8,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.3,
        PersonalityTrait.EXTRAVERSION: 0.9,
        PersonalityTrait.AGREEABLENESS: 0.7,
        PersonalityTrait.NEUROTICISM: 0.5,
    },
    CharacterArchetype.GUARDIAN: {
        PersonalityTrait.OPENNESS: 0.4,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.9,
        PersonalityTrait.EXTRAVERSION: 0.4,
        PersonalityTrait.AGREEABLENESS: 0.8,
        PersonalityTrait.NEUROTICISM: 0.3,
    },
    CharacterArchetype.TRICKSTER: {
        PersonalityTrait.OPENNESS: 0.9,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.3,
        PersonalityTrait.EXTRAVERSION: 0.7,
        PersonalityTrait.AGREEABLENESS: 0.5,
        PersonalityTrait.NEUROTICISM: 0.4,
    },
    CharacterArchetype.MENTOR: {
        PersonalityTrait.OPENNESS: 0.8,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.9,
        PersonalityTrait.EXTRAVERSION: 0.5,
        PersonalityTrait.AGREEABLENESS: 0.8,
        PersonalityTrait.NEUROTICISM: 0.2,
    },
    CharacterArchetype.RIVAL: {
        PersonalityTrait.OPENNESS: 0.6,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.7,
        PersonalityTrait.EXTRAVERSION: 0.6,
        PersonalityTrait.AGREEABLENESS: 0.4,
        PersonalityTrait.NEUROTICISM: 0.5,
    },
    CharacterArchetype.LOVER: {
        PersonalityTrait.OPENNESS: 0.7,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.5,
        PersonalityTrait.EXTRAVERSION: 0.6,
        PersonalityTrait.AGREEABLENESS: 0.8,
        PersonalityTrait.NEUROTICISM: 0.6,
    },
    CharacterArchetype.OUTCAST: {
        PersonalityTrait.OPENNESS: 0.6,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.4,
        PersonalityTrait.EXTRAVERSION: 0.2,
        PersonalityTrait.AGREEABLENESS: 0.5,
        PersonalityTrait.NEUROTICISM: 0.7,
    },
    CharacterArchetype.LEADER: {
        PersonalityTrait.OPENNESS: 0.7,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.8,
        PersonalityTrait.EXTRAVERSION: 0.8,
        PersonalityTrait.AGREEABLENESS: 0.6,
        PersonalityTrait.NEUROTICISM: 0.3,
    },
    CharacterArchetype.FOLLOWER: {
        PersonalityTrait.OPENNESS: 0.5,
        PersonalityTrait.CONSCIENTIOUSNESS: 0.6,
        PersonalityTrait.EXTRAVERSION: 0.4,
        PersonalityTrait.AGREEABLENESS: 0.7,
        PersonalityTrait.NEUROTICISM: 0.5,
    },
}


# アーキタイプによる関係形成の傾向
ARCHETYPE_RELATIONSHIP_TENDENCIES: dict[CharacterArchetype, dict[RelationshipType, float]] = {
    CharacterArchetype.HERO: {
        RelationshipType.FAVORABILITY: 1.2,
        RelationshipType.FRIENDSHIP: 1.3,
        RelationshipType.MENTORSHIP: 0.8,
        RelationshipType.ENMITY: 0.5,
        RelationshipType.BETRAYAL: 0.3,
    },
    CharacterArchetype.VILLAIN: {
        RelationshipType.FAVORABILITY: 0.7,
        RelationshipType.ENMITY: 1.5,
        RelationshipType.BETRAYAL: 1.8,
        RelationshipType.FRIENDSHIP: 0.5,
        RelationshipType.MENTORSHIP: 0.4,
    },
    CharacterArchetype.SAGE: {
        RelationshipType.MENTORSHIP: 1.8,
        RelationshipType.FAVORABILITY: 1.0,
        RelationshipType.FRIENDSHIP: 0.9,
        RelationshipType.ENMITY: 0.3,
        RelationshipType.ROMANCE: 0.5,
    },
    CharacterArchetype.JESTER: {
        RelationshipType.FRIENDSHIP: 1.5,
        RelationshipType.FAVORABILITY: 1.2,
        RelationshipType.ROMANCE: 1.1,
        RelationshipType.MENTORSHIP: 0.6,
        RelationshipType.ENMITY: 0.4,
    },
    CharacterArchetype.GUARDIAN: {
        RelationshipType.FRIENDSHIP: 1.2,
        RelationshipType.MENTORSHIP: 1.2,
        RelationshipType.FAVORABILITY: 1.0,
        RelationshipType.BETRAYAL: 0.2,
        RelationshipType.ENMITY: 0.5,
    },
    CharacterArchetype.TRICKSTER: {
        RelationshipType.FAVORABILITY: 0.8,
        RelationshipType.BETRAYAL: 1.5,
        RelationshipType.FRIENDSHIP: 0.9,
        RelationshipType.ROMANCE: 1.0,
        RelationshipType.MENTORSHIP: 0.5,
    },
    CharacterArchetype.MENTOR: {
        RelationshipType.MENTORSHIP: 2.0,
        RelationshipType.FAVORABILITY: 1.1,
        RelationshipType.FRIENDSHIP: 1.0,
        RelationshipType.ENMITY: 0.2,
        RelationshipType.BETRAYAL: 0.2,
    },
    CharacterArchetype.RIVAL: {
        RelationshipType.RIVALRY: 1.8,
        RelationshipType.FAVORABILITY: 0.9,
        RelationshipType.FRIENDSHIP: 0.7,
        RelationshipType.ENMITY: 0.8,
        RelationshipType.BETRAYAL: 0.7,
    },
    CharacterArchetype.LOVER: {
        RelationshipType.ROMANCE: 2.0,
        RelationshipType.FAVORABILITY: 1.3,
        RelationshipType.FRIENDSHIP: 1.1,
        RelationshipType.BETRAYAL: 1.2,
        RelationshipType.ENMITY: 0.4,
    },
    CharacterArchetype.OUTCAST: {
        RelationshipType.FAVORABILITY: 0.8,
        RelationshipType.FRIENDSHIP: 0.7,
        RelationshipType.ENMITY: 0.9,
        RelationshipType.BETRAYAL: 0.8,
        RelationshipType.MENTORSHIP: 0.3,
    },
    CharacterArchetype.LEADER: {
        RelationshipType.FAVORABILITY: 1.3,
        RelationshipType.MENTORSHIP: 1.1,
        RelationshipType.FRIENDSHIP: 1.0,
        RelationshipType.ENMITY: 0.6,
        RelationshipType.BETRAYAL: 0.5,
    },
    CharacterArchetype.FOLLOWER: {
        RelationshipType.FAVORABILITY: 1.0,
        RelationshipType.FRIENDSHIP: 1.1,
        RelationshipType.MENTORSHIP: 0.7,
        RelationshipType.ENMITY: 0.4,
        RelationshipType.BETRAYAL: 0.6,
    },
}


@dataclass
class PersonalityProfile:
    """パーソナリティプロファイル"""

    character_id: str
    traits: dict[PersonalityTrait, float] = field(default_factory=dict)
    archetype: CharacterArchetype | None = None
    dominant_trait: PersonalityTrait | None = None
    relationship_tendencies: dict[RelationshipType, float] = field(default_factory=dict)

    def get_trait(self, trait: PersonalityTrait) -> float:
        """特性値を取得（0.0〜1.0）"""
        return self.traits.get(trait, 0.5)

    def get_dominant_trait(self) -> PersonalityTrait | None:
        """最も強い特性を取得"""
        if not self.traits:
            return None
        return max(self.traits, key=lambda t: self.traits[t])

    def calculate_relationship_modifier(self, relationship_type: RelationshipType) -> float:
        """関係タイプに対する修正子を計算"""
        if relationship_type in self.relationship_tendencies:
            return self.relationship_tendencies[relationship_type]

        # デフォルトの計算（特性ベース）
        modifier = 1.0
        if relationship_type == RelationshipType.FRIENDSHIP:
            modifier = 0.5 + self.get_trait(PersonalityTrait.EXTRAVERSION)
        elif relationship_type == RelationshipType.FAVORABILITY:
            modifier = 0.5 + self.get_trait(PersonalityTrait.AGREEABLENESS)
        elif relationship_type == RelationshipType.ENMITY:
            modifier = 0.5 + (1 - self.get_trait(PersonalityTrait.AGREEABLENESS))
        elif relationship_type == RelationshipType.BETRAYAL:
            modifier = (
                0.3
                + (1 - self.get_trait(PersonalityTrait.CONSCIENTIOUSNESS))
                + self.get_trait(PersonalityTrait.NEUROTICISM) * 0.3
            )
        elif relationship_type == RelationshipType.MENTORSHIP:
            modifier = (
                0.5
                + self.get_trait(PersonalityTrait.OPENNESS) * 0.5
                + self.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) * 0.5
            )
        elif relationship_type == RelationshipType.ROMANCE:
            modifier = (
                0.4
                + self.get_trait(PersonalityTrait.OPENNESS) * 0.3
                + self.get_trait(PersonalityTrait.AGREEABLENESS) * 0.3
            )
        elif relationship_type == RelationshipType.RIVALRY:
            modifier = (
                0.5
                + self.get_trait(PersonalityTrait.EXTRAVERSION) * 0.3
                + (1 - self.get_trait(PersonalityTrait.AGREEABLENESS)) * 0.2
            )

        return max(0.1, min(2.0, modifier))


class PersonalitySystem:
    """
    パーソナリティとアーキタイプシステム
    NPCの性格特性とアーキタイプによる関係形成パターンを管理
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # パーソナリティプロファイルのストレージ
        self.profiles: dict[str, PersonalityProfile] = {}

        # アーキタイプ定義
        self.archetypes = CharacterArchetype

        # 設定
        self._config = {
            "trait_influence_factor": 0.3,  # 関係変化に対する特性の影響度
            "archetype_influence_factor": 0.5,  # アーキタイプの影響度
            "random_variance": 0.1,  # ランダム変動
        }

    def assign_personality(
        self,
        character_id: str,
        traits: dict[PersonalityTrait, float] | None = None,
        archetype: CharacterArchetype | None = None,
    ) -> PersonalityProfile:
        """キャラクターにパーソナリティを割り当て"""
        # 既存のプロファイルをチェック
        if character_id in self.profiles:
            profile = self.profiles[character_id]
        else:
            profile = PersonalityProfile(character_id=character_id)
            self.profiles[character_id] = profile

        # アーキタイプが指定されている場合、ベースプロファイルを設定
        if archetype:
            profile.archetype = archetype
            base_traits = ARCHETYPE_PROFILES.get(archetype, {})
            # 指定された特性があれば上書き、なければアーキタイプのデフォルトを使用
            for trait, value in base_traits.items():
                if traits and trait in traits:
                    profile.traits[trait] = traits[trait]
                else:
                    profile.traits[trait] = value

        # 明示的に指定された特性を適用
        if traits:
            for trait, value in traits.items():
                profile.traits[trait] = max(0.0, min(1.0, value))

        # 関係傾向を計算
        profile.relationship_tendencies = self._calculate_relationship_tendencies(profile)
        profile.dominant_trait = profile.get_dominant_trait()

        return profile

    def _calculate_relationship_tendencies(
        self, profile: PersonalityProfile
    ) -> dict[RelationshipType, float]:
        """関係傾向を計算"""
        tendencies: dict[RelationshipType, float] = {}

        # アーキタイプベースの傾向
        if profile.archetype and profile.archetype in ARCHETYPE_RELATIONSHIP_TENDENCIES:
            arch_tendencies = ARCHETYPE_RELATIONSHIP_TENDENCIES[profile.archetype]
            for rel_type, value in arch_tendencies.items():
                tendencies[rel_type] = value

        # 特性ベースの修正
        for rel_type in RelationshipType:
            if rel_type not in tendencies:
                tendencies[rel_type] = 1.0

            # 特性による微調整
            trait_mod = self._calculate_trait_modifier(profile, rel_type)
            tendencies[rel_type] *= trait_mod

        return tendencies

    def _calculate_trait_modifier(
        self, profile: PersonalityProfile, rel_type: RelationshipType
    ) -> float:
        """特性による修正子を計算"""
        modifier = 1.0
        t = profile.traits

        # 関係タイプに応じた特性の影響
        if rel_type == RelationshipType.FRIENDSHIP:
            modifier *= 0.7 + t.get(PersonalityTrait.EXTRAVERSION, 0.5) * 0.6
        elif rel_type == RelationshipType.FAVORABILITY:
            modifier *= 0.7 + t.get(PersonalityTrait.AGREEABLENESS, 0.5) * 0.6
        elif rel_type == RelationshipType.ENMITY:
            modifier *= 0.7 + (1 - t.get(PersonalityTrait.AGREEABLENESS, 0.5)) * 0.6
        elif rel_type == RelationshipType.BETRAYAL:
            betrayal_factor = (1 - t.get(PersonalityTrait.CONSCIENTIOUSNESS, 0.5)) * 0.7 + t.get(
                PersonalityTrait.NEUROTICISM, 0.5
            ) * 0.3
            modifier *= 0.6 + betrayal_factor
        elif rel_type == RelationshipType.MENTORSHIP:
            modifier *= (
                0.6
                + t.get(PersonalityTrait.OPENNESS, 0.5) * 0.4
                + t.get(PersonalityTrait.CONSCIENTIOUSNESS, 0.5) * 0.4
            )
        elif rel_type == RelationshipType.ROMANCE:
            modifier *= (
                0.6
                + t.get(PersonalityTrait.OPENNESS, 0.5) * 0.3
                + t.get(PersonalityTrait.AGREEABLENESS, 0.5) * 0.3
            )
        elif rel_type == RelationshipType.RIVALRY:
            modifier *= 0.7 + t.get(PersonalityTrait.EXTRAVERSION, 0.5) * 0.3

        return max(0.1, min(2.0, modifier))

    def get_interaction_modifier(
        self,
        source_id: str,
        target_id: str,
        interaction_type: InteractionType,
        relationship_type: RelationshipType,
    ) -> float:
        """インタラクションに対する修正子を計算"""
        source_profile = self.profiles.get(source_id)
        target_profile = self.profiles.get(target_id)

        if not source_profile:
            return 1.0

        modifier = 1.0

        # ソースキャラクターの特性による影響
        if source_profile:
            # 関係傾向による基本修正
            rel_tendency = source_profile.relationship_tendencies.get(relationship_type, 1.0)
            modifier *= 1.0 + (rel_tendency - 1.0) * self._config["archetype_influence_factor"]

        # ターゲットキャラクターの特性による影響（受容性）
        if target_profile:
            # ターゲットが友好的（agreeableness高）ならポジティブなインタラクションをより受け入れる
            if interaction_type in [
                InteractionType.TALK,
                InteractionType.GIFT,
                InteractionType.EMOTIONAL_SUPPORT,
            ]:
                agreeableness = target_profile.get_trait(PersonalityTrait.AGREEABLENESS)
                modifier *= 0.7 + agreeableness * 0.6
            # ターゲットが神経症的（neuroticism高）ならネガティブなインタラクションをより強く受ける
            elif interaction_type in [
                InteractionType.ARGUMENT,
                InteractionType.BETRAYAL,
            ]:
                neuroticism = target_profile.get_trait(PersonalityTrait.NEUROTICISM)
                modifier *= 1.0 + neuroticism * 0.5

        # ランダム変動
        variance = self._config["random_variance"]
        modifier *= 1.0 + random.uniform(-variance, variance)

        return max(0.1, min(3.0, modifier))

    def generate_random_personality(
        self, character_id: str, archetype: CharacterArchetype | None = None
    ) -> PersonalityProfile:
        """ランダムなパーソナリティを生成"""
        if archetype is None:
            archetype = random.choice(list(CharacterArchetype))

        # アーキタイプのベースプロファイルを取得
        base_traits = ARCHETYPE_PROFILES.get(archetype, {})

        # ランダムな変動を追加
        traits = {}
        for trait, base_value in base_traits.items():
            # ±0.15のランダム変動
            value = base_value + random.uniform(-0.15, 0.15)
            traits[trait] = max(0.0, min(1.0, value))

        return self.assign_personality(character_id, traits, archetype)

    def get_compatibility_between(self, char_a: str, char_b: str) -> float:
        """二人のキャラクター間の相性を計算"""
        profile_a = self.profiles.get(char_a)
        profile_b = self.profiles.get(char_b)

        if not profile_a or not profile_b:
            return 0.5

        # 特性の類似性を計算
        similarity = 0.0
        count = 0
        for trait in PersonalityTrait:
            if trait in profile_a.traits and trait in profile_b.traits:
                # 値の差（0に近いほど類似）
                diff = abs(profile_a.traits[trait] - profile_b.traits[trait])
                similarity += 1.0 - diff
                count += 1

        if count == 0:
            return 0.5

        base_similarity = similarity / count

        # 補完的な関係も考慮（例：外向性と内向性は補完的）
        complementarity = 0.0
        if (
            PersonalityTrait.EXTRAVERSION in profile_a.traits
            and PersonalityTrait.EXTRAVERSION in profile_b.traits
        ):
            ext_a = profile_a.traits[PersonalityTrait.EXTRAVERSION]
            ext_b = profile_b.traits[PersonalityTrait.EXTRAVERSION]
            # 一方が外向的で一方が内向的なら補完的
            complementarity += (1.0 - abs(ext_a - ext_b)) * 0.5

        compatibility = base_similarity * 0.8 + complementarity * 0.2
        return max(0.0, min(1.0, compatibility))

    def predict_relationship_development(
        self, char_a: str, char_b: str, relationship_type: RelationshipType
    ) -> str:
        """関係の発展を予測"""
        profile_a = self.profiles.get(char_a)
        profile_b = self.profiles.get(char_b)

        if not profile_a or not profile_b:
            return "unknown"

        # 各キャラクターの関係傾向を取得
        tendency_a = profile_a.relationship_tendencies.get(relationship_type, 1.0)
        tendency_b = profile_b.relationship_tendencies.get(relationship_type, 1.0)

        avg_tendency = (tendency_a + tendency_b) / 2

        if avg_tendency >= 1.5:
            return "rapidly_improving"
        elif avg_tendency >= 1.1:
            return "improving"
        elif avg_tendency >= 0.9:
            return "stable"
        elif avg_tendency >= 0.5:
            return "declining"
        else:
            return "rapidly_declining"

    def get_profile(self, character_id: str) -> PersonalityProfile | None:
        """パーソナリティプロファイルを取得"""
        return self.profiles.get(character_id)

    def get_all_profiles(self) -> dict[str, PersonalityProfile]:
        """すべてのプロファイルを取得"""
        return self.profiles.copy()

    def serialize(self) -> dict[str, Any]:
        """パーソナリティデータをシリアライズ"""
        return {
            "profiles": {
                char_id: {
                    "character_id": profile.character_id,
                    "traits": {t.value: v for t, v in profile.traits.items()},
                    "archetype": profile.archetype.value if profile.archetype else None,
                    "dominant_trait": (
                        profile.dominant_trait.value if profile.dominant_trait else None
                    ),
                    "relationship_tendencies": {
                        rt.value: v for rt, v in profile.relationship_tendencies.items()
                    },
                }
                for char_id, profile in self.profiles.items()
            }
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """パーソナリティデータをデシリアライズ"""
        self.profiles.clear()

        for char_id, profile_data in data.get("profiles", {}).items():
            profile = PersonalityProfile(
                character_id=profile_data["character_id"],
                traits={PersonalityTrait(k): v for k, v in profile_data.get("traits", {}).items()},
                archetype=(
                    CharacterArchetype(profile_data["archetype"])
                    if profile_data.get("archetype")
                    else None
                ),
                dominant_trait=(
                    PersonalityTrait(profile_data["dominant_trait"])
                    if profile_data.get("dominant_trait")
                    else None
                ),
                relationship_tendencies={
                    RelationshipType(k): v
                    for k, v in profile_data.get("relationship_tendencies", {}).items()
                },
            )
            self.profiles[char_id] = profile
