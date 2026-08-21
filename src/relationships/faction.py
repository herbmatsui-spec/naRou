"""
NPC Relationship Simulation - Faction Relationship System
Step 8: Faction relationship system
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import FactionAffiliation, InteractionType, RelationshipType


class FactionRelationType(Enum):
    """派閥間関係のタイプ"""

    ALLIED = "allied"  # 同盟
    NEUTRAL = "neutral"  # 中立
    TENSE = "tense"  # 緊張
    HOSTILE = "hostile"  # 敵対
    WAR = "war"  # 戦争状態


@dataclass
class FactionNode:
    """派閥ノード"""

    faction_id: str
    name: str
    members: set[str] = field(default_factory=set)
    leader_id: str | None = None
    power_level: int = 0
    territory: list[str] = field(default_factory=list)
    ideology: str = ""
    resources: dict[str, int] = field(default_factory=dict)

    def add_member(self, character_id: str) -> None:
        self.members.add(character_id)

    def remove_member(self, character_id: str) -> None:
        self.members.discard(character_id)
        if self.leader_id == character_id:
            self.leader_id = None


@dataclass
class FactionRelation:
    """派閥間関係"""

    faction_a: str
    faction_b: str
    relation_type: FactionRelationType
    relation_strength: int = 0  # -100〜+100
    conflict_history: list[dict[str, Any]] = field(default_factory=list)
    last_interaction: float = field(default_factory=time.time)

    def update_relation(self, delta: int) -> None:
        """関係を更新"""
        self.relation_strength = max(-100, min(100, self.relation_strength + delta))
        self._update_relation_type()
        self.last_interaction = time.time()

    def _update_relation_type(self) -> None:
        """関係強度に基づいて関係タイプを更新"""
        if self.relation_strength >= 60:
            self.relation_type = FactionRelationType.ALLIED
        elif self.relation_strength >= 20:
            self.relation_type = FactionRelationType.NEUTRAL
        elif self.relation_strength >= -20:
            self.relation_type = FactionRelationType.TENSE
        elif self.relation_strength >= -60:
            self.relation_type = FactionRelationType.HOSTILE
        else:
            self.relation_type = FactionRelationType.WAR

    def add_conflict_record(self, conflict_data: dict[str, Any]) -> None:
        """対立記録を追加"""
        conflict_data["timestamp"] = time.time()
        self.conflict_history.append(conflict_data)
        # 最新の10件のみ保持
        if len(self.conflict_history) > 10:
            self.conflict_history = self.conflict_history[-10:]


class FactionRelationshipSystem:
    """
    派閥関係システム
    個人関係から派閥レベルの関係を集約し、派閥ダイナミクスを管理
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # 派閥ストレージ
        self.factions: dict[str, FactionNode] = {}
        self.faction_relations: dict[tuple[str, str], FactionRelation] = {}

        # キャッシュ
        self._member_relationship_cache: dict[str, dict[str, int]] = {}
        self._last_cache_update: float = 0

        # 派閥設定
        self._faction_config: dict[str, Any] = self._load_faction_config()

        # 初期化
        self._initialize_factions()

    def _load_faction_config(self) -> dict[str, Any]:
        """派閥設定のロード"""
        # 簡易実装：ハードコードされた設定
        return {
            "aggregation_method": "weighted_average",  # 加重平均、majority、min、max
            "conflict_decay": 0.001,
            "alliance_threshold": 60,
            "war_threshold": -60,
            "member_weight": {
                "leader": 3.0,
                "elder": 2.0,
                "member": 1.0,
                "associate": 0.5,
            },
        }

    def _initialize_factions(self) -> None:
        """グラフから派閥情報を初期化"""
        # すべてのノードの派閥所属をチェック
        for node_id, node in self.graph.nodes.items():
            for faction_id, affiliation in node.faction_affiliations.items():
                # 派閥ノードを作成/取得
                if faction_id not in self.factions:
                    self.factions[faction_id] = FactionNode(
                        faction_id=faction_id, name=f"Faction_{faction_id}"
                    )
                # メンバーとして追加
                self.factions[faction_id].add_member(node_id)
                # リーダーの場合
                if affiliation == FactionAffiliation.LEADER:
                    self.factions[faction_id].leader_id = node_id

    def register_faction(
        self, faction_id: str, name: str, ideology: str = "", power_level: int = 0
    ) -> FactionNode:
        """新しい派閥を登録"""
        if faction_id not in self.factions:
            self.factions[faction_id] = FactionNode(
                faction_id=faction_id,
                name=name,
                ideology=ideology,
                power_level=power_level,
            )
        return self.factions[faction_id]

    def assign_to_faction(
        self,
        character_id: str,
        faction_id: str,
        affiliation: FactionAffiliation = FactionAffiliation.MEMBER,
    ) -> bool:
        """キャラクターを派閥に所属させる"""
        # キャラクターが存在するかチェック
        node = self.graph.get_node(character_id)
        if not node:
            return False

        # 派閥が存在するかチェック
        if faction_id not in self.factions:
            self.register_faction(faction_id, f"Faction_{faction_id}")

        # 既存の所属を更新（同じ派閥なら上書き、異なる派閥なら追加）
        node.faction_affiliations[faction_id] = affiliation

        # 派閥メンバーシップを更新
        self.factions[faction_id].add_member(character_id)
        if affiliation == FactionAffiliation.LEADER:
            self.factions[faction_id].leader_id = character_id

        # キャッシュを無効化
        self._invalidate_cache()

        return True

    def get_faction_relation(
        self, faction_a: str, faction_b: str
    ) -> FactionRelation | None:
        """二つの派閥間の関係を取得"""
        # 順序を正規化
        key = tuple(sorted([faction_a, faction_b]))
        return self.faction_relations.get(key)

    def aggregate_faction_relationships(
        self, faction_id: str
    ) -> dict[str, dict[str, int]]:
        """
        派閥内の個人関係から派閥間関係を集約
        戻り値: {他派閥ID: {関係タイプ: 強度}}
        """
        # キャッシュチェック
        current_time = time.time()
        if (
            faction_id in self._member_relationship_cache
            and current_time - self._last_cache_update < 3600
        ):  # 1時間キャッシュ
            return self._member_relationship_cache[faction_id]

        if faction_id not in self.factions:
            return {}

        faction = self.factions[faction_id]
        aggregated: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        member_counts: dict[str, dict[RelationshipType, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # 派閥メンバーごとに他派閥メンバーとの関係を集計
        for member_id in faction.members:
            # メンバーの他派閥関係を取得
            if member_id not in self.graph.nodes:
                continue

            self.graph.get_node(member_id)
            member_weight = self._get_member_weight(member_id, faction_id)

            # メンバーのすべての関係を取得
            for other_id, edge in self.graph.get_related_nodes(member_id):
                other_node = self.graph.get_node(other_id)
                if not other_node:
                    continue

                # 他の派閥所属をチェック
                for other_faction_id in other_node.faction_affiliations:
                    if other_faction_id == faction_id:
                        continue  # 同じ派閥はスキップ

                    # 重み付きで集計
                    aggregated[other_faction_id][edge.relationship_type.value] += (
                        edge.level * member_weight
                    )
                    member_counts[other_faction_id][edge.relationship_type] += (
                        member_weight
                    )

        # 平均を計算
        result: dict[str, dict[str, int]] = {}
        for other_faction_id, type_dict in aggregated.items():
            result[other_faction_id] = {}
            for rel_type, total in type_dict.items():
                count = member_counts[other_faction_id][RelationshipType(rel_type)]
                if count > 0:
                    result[other_faction_id][rel_type] = int(total / count)

        # キャッシュに保存
        self._member_relationship_cache[faction_id] = dict(result)
        self._last_cache_update = current_time

        return dict(result)

    def _get_member_weight(self, character_id: str, faction_id: str) -> float:
        """メンバーの重みを取得（リーダーは高い）"""
        node = self.graph.get_node(character_id)
        if not node:
            return 1.0

        affiliation = node.faction_affiliations.get(
            faction_id, FactionAffiliation.MEMBER
        )
        weight_map = self._faction_config.get("member_weight", {})

        if affiliation == FactionAffiliation.LEADER:
            return weight_map.get("leader", 3.0)
        elif affiliation == FactionAffiliation.ELDER:
            return weight_map.get("elder", 2.0)
        elif affiliation == FactionAffiliation.MEMBER:
            return weight_map.get("member", 1.0)
        else:
            return weight_map.get("associate", 0.5)

    def update_faction_relation(
        self,
        faction_a: str,
        faction_b: str,
        delta: int,
        conflict_data: dict[str, Any] | None = None,
    ) -> FactionRelation | None:
        """派閥間関係を更新"""
        if faction_a not in self.factions or faction_b not in self.factions:
            return None

        key = tuple(sorted([faction_a, faction_b]))

        if key not in self.faction_relations:
            # 初期関係を集約から計算
            aggregated_a = self.aggregate_faction_relationships(faction_a)
            aggregated_b = self.aggregate_faction_relationships(faction_b)

            # 平均関係強度を計算
            avg_strength = self._calculate_initial_faction_strength(
                aggregated_a, aggregated_b, faction_a, faction_b
            )

            relation = FactionRelation(
                faction_a=faction_a,
                faction_b=faction_b,
                relation_type=FactionRelationType.NEUTRAL,
                relation_strength=avg_strength,
            )
            relation._update_relation_type()
            self.faction_relations[key] = relation
        else:
            relation = self.faction_relations[key]

        # 関係を更新
        relation.update_relation(delta)

        # 対立記録を追加
        if conflict_data:
            relation.add_conflict_record(conflict_data)

        # キャッシュを無効化
        self._invalidate_cache()

        return relation

    def _calculate_initial_faction_strength(
        self,
        agg_a: dict[str, dict[str, int]],
        agg_b: dict[str, dict[str, int]],
        faction_a: str,
        faction_b: str,
    ) -> int:
        """初期派閥関係強度を計算"""
        # faction_a から見た faction_b への関係
        strength_a = 0
        if faction_b in agg_a:
            favorability = agg_a[faction_b].get("favorability", 0)
            enmity = agg_a[faction_b].get("enmity", 0)
            strength_a = favorability - enmity

        # faction_b から見た faction_a への関係
        strength_b = 0
        if faction_a in agg_b:
            favorability = agg_b[faction_a].get("favorability", 0)
            enmity = agg_b[faction_a].get("enmity", 0)
            strength_b = favorability - enmity

        # 平均を取る
        return int((strength_a + strength_b) / 2)

    def check_faction_conflicts(self) -> list[dict[str, Any]]:
        """派閥間で緊張や敵対状態をチェック"""
        conflicts = []

        for (faction_a, faction_b), relation in self.faction_relations.items():
            if relation.relation_type in [
                FactionRelationType.TENSE,
                FactionRelationType.HOSTILE,
                FactionRelationType.WAR,
            ]:
                conflicts.append(
                    {
                        "faction_a": faction_a,
                        "faction_b": faction_b,
                        "relation_type": relation.relation_type.value,
                        "strength": relation.relation_strength,
                        "severity": self._calculate_conflict_severity(relation),
                    }
                )

        return conflicts

    def _calculate_conflict_severity(self, relation: FactionRelation) -> str:
        """対立の深刻度を計算"""
        if relation.relation_type == FactionRelationType.WAR:
            return "critical"
        elif relation.relation_type == FactionRelationType.HOSTILE:
            return "high"
        elif relation.relation_type == FactionRelationType.TENSE:
            return "moderate"
        else:
            return "low"

    def simulate_faction_event(
        self,
        event_type: str,
        faction_id: str,
        target_faction_id: str | None = None,
        magnitude: int = 10,
    ) -> list[dict[str, Any]]:
        """派閥イベントをシミュレートし、関係に影響"""
        results = []

        if event_type == "war_declaration" and target_faction_id:
            # 宣戦布告
            relation = self.update_faction_relation(
                faction_id,
                target_faction_id,
                -magnitude,
                conflict_data={"type": "war_declaration", "magnitude": magnitude},
            )
            if relation:
                results.append(
                    {
                        "event": "war_declaration",
                        "relation": relation.relation_type.value,
                        "strength": relation.relation_strength,
                    }
                )

        elif event_type == "alliance_proposal" and target_faction_id:
            # 同盟提案
            relation = self.update_faction_relation(
                faction_id,
                target_faction_id,
                magnitude,
                conflict_data={"type": "alliance_proposal", "magnitude": magnitude},
            )
            if relation:
                results.append(
                    {
                        "event": "alliance_proposal",
                        "relation": relation.relation_type.value,
                        "strength": relation.relation_strength,
                    }
                )

        elif event_type == "territory_dispute" and target_faction_id:
            # 領土紛争
            relation = self.update_faction_relation(
                faction_id,
                target_faction_id,
                -magnitude // 2,
                conflict_data={"type": "territory_dispute", "magnitude": magnitude},
            )
            if relation:
                results.append(
                    {
                        "event": "territory_dispute",
                        "relation": relation.relation_type.value,
                        "strength": relation.relation_strength,
                    }
                )

        elif event_type == "resource_trade" and target_faction_id:
            # 資源取引
            relation = self.update_faction_relation(
                faction_id,
                target_faction_id,
                magnitude // 2,
                conflict_data={"type": "resource_trade", "magnitude": magnitude},
            )
            if relation:
                results.append(
                    {
                        "event": "resource_trade",
                        "relation": relation.relation_type.value,
                        "strength": relation.relation_strength,
                    }
                )

        return results

    def get_faction_influence_on_relationships(
        self, character_id: str
    ) -> dict[str, int]:
        """キャラクターの派閥所属が個人関係に与える影響を取得"""
        node = self.graph.get_node(character_id)
        if not node:
            return {}

        influences: dict[str, int] = {}

        # 各派閥所属について影響を計算
        for faction_id in node.faction_affiliations:
            if faction_id not in self.factions:
                continue

            # 派閥の他派閥との関係を取得
            aggregated = self.aggregate_faction_relationships(faction_id)

            for other_faction_id, rel_types in aggregated.items():
                favorability = rel_types.get("favorability", 0)
                enmity = rel_types.get("enmity", 0)

                # 派閥の敵対派閥に所属するキャラクターに対して影響
                for other_char_id, other_node in self.graph.nodes.items():
                    if other_char_id == character_id:
                        continue
                    if other_faction_id in other_node.faction_affiliations:
                        influence = favorability - enmity
                        if influence != 0:
                            influences[other_char_id] = (
                                influences.get(other_char_id, 0) + influence // 10
                            )

        return influences

    def apply_faction_influence_to_relationships(
        self, character_id: str
    ) -> dict[str, int]:
        """派閥影響を個人関係に適用"""
        influences = self.get_faction_influence_on_relationships(character_id)
        applied = {}

        for other_char_id, influence in influences.items():
            if influence == 0:
                continue

            # 派閥影響を関係に適用（小さな変化として）
            self.rm.modify_relationship(
                character_id,
                other_char_id,
                InteractionType.QUEST_COOPERATION,  # 適当なインタラクションタイプ
                influence,
            )
            applied[other_char_id] = influence

        return applied

    def get_faction_statistics(self) -> dict[str, Any]:
        """派閥システムの統計情報"""
        return {
            "faction_count": len(self.factions),
            "relation_count": len(self.faction_relations),
            "conflicts": len(self.check_faction_conflicts()),
            "factions": {
                fid: {
                    "name": f.name,
                    "member_count": len(f.members),
                    "power_level": f.power_level,
                    "ideology": f.ideology,
                }
                for fid, f in self.factions.items()
            },
        }

    def _invalidate_cache(self) -> None:
        """キャッシュを無効化"""
        self._member_relationship_cache.clear()
        self._last_cache_update = 0
