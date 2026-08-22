"""
NPC Relationship Simulation - Relationship Graph Data Structure
Step 2: Relationship graph data structure
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from .models import (
    FactionAffiliation,
    InteractionType,
    RelationshipEdge,
    RelationshipModifier,
    RelationshipNode,
    RelationshipType,
)


class RelationshipGraph:
    """
    マルチレイヤー関係グラフ
    複数の関係タイプ層を持つ有向グラフ（片思い等のため有向、相互関係のため双方向エッジもサポート）
    """

    def __init__(self):
        # ノードストレージ: character_id -> RelationshipNode
        self.nodes: dict[str, RelationshipNode] = {}

        # エッジストレージ: (source_id, target_id, relationship_type) -> RelationshipEdge
        # 多層グラフのため、同じノードペアでも関係タイプが異なる場合別エッジとして保持
        self.edges: dict[tuple[str, str, RelationshipType], RelationshipEdge] = {}

        # 高速アクセス用インデックス
        self.node_edges: dict[str, set[tuple[str, str, RelationshipType]]] = defaultdict(set)
        self.type_edges: dict[RelationshipType, set[tuple[str, str]]] = defaultdict(set)

        # グラフ統計情報
        self.stats = {"node_count": 0, "edge_count": 0, "last_updated": time.time()}

    def add_node(self, node: RelationshipNode) -> None:
        """ノードをグラフに追加"""
        if node.character_id not in self.nodes:
            self.nodes[node.character_id] = node
            self.stats["node_count"] = len(self.nodes)
            self.stats["last_updated"] = time.time()

    def remove_node(self, character_id: str) -> bool:
        """ノードと関連するすべてのエッジを削除"""
        if character_id not in self.nodes:
            return False

        # 関連するすべてのエッジを削除
        edges_to_remove = list(self.node_edges[character_id])
        for source_id, target_id, rel_type in edges_to_remove:
            self._remove_edge_internal(source_id, target_id, rel_type)

        # ノードを削除
        del self.nodes[character_id]
        del self.node_edges[character_id]

        self.stats["node_count"] = len(self.nodes)
        self.stats["edge_count"] = len(self.edges)
        self.stats["last_updated"] = time.time()
        return True

    def get_node(self, character_id: str) -> RelationshipNode | None:
        """ノードを取得"""
        return self.nodes.get(character_id)

    def add_edge(self, edge: RelationshipEdge) -> bool:
        """エッジをグラフに追加"""
        key = (edge.source_id, edge.target_id, edge.relationship_type)

        # 既存エッジがある場合は更新（または重複防止）
        if key in self.edges:
            # 既存エッジの修正子をマージ
            existing_edge = self.edges[key]
            existing_edge.modifiers.extend(edge.modifiers)
            # レベルは新しいエッジのレベルで上書き（または平均を取るか設計による）
            existing_edge.level = edge.level
            existing_edge.last_interaction = edge.last_interaction
            existing_edge.is_mutual = edge.is_mutual
            existing_edge.decay_rate = edge.decay_rate
        else:
            # 新しいエッジを追加
            self.edges[key] = edge
            self.node_edges[edge.source_id].add(key)
            self.node_edges[edge.target_id].add(key)  # 双方向アクセスのため
            self.type_edges[edge.relationship_type].add((edge.source_id, edge.target_id))

            self.stats["edge_count"] = len(self.edges)

        self.stats["last_updated"] = time.time()
        return True

    def remove_edge(
        self, source_id: str, target_id: str, relationship_type: RelationshipType
    ) -> bool:
        """エッジを削除"""
        return self._remove_edge_internal(source_id, target_id, relationship_type)

    def _remove_edge_internal(
        self, source_id: str, target_id: str, relationship_type: RelationshipType
    ) -> bool:
        """内部エッジ削除メソッド"""
        key = (source_id, target_id, relationship_type)
        if key not in self.edges:
            return False

        del self.edges[key]
        self.node_edges[source_id].discard(key)
        self.node_edges[target_id].discard(key)
        self.type_edges[relationship_type].discard((source_id, target_id))

        self.stats["edge_count"] = len(self.edges)
        self.stats["last_updated"] = time.time()
        return True

    def get_edge(
        self, source_id: str, target_id: str, relationship_type: RelationshipType
    ) -> RelationshipEdge | None:
        """特定の関係タイプのエッジを取得"""
        return self.edges.get((source_id, target_id, relationship_type))

    def get_edges_between(self, source_id: str, target_id: str) -> list[RelationshipEdge]:
        """二つのノード間のすべての関係タイプのエッジを取得"""
        edges = []
        for (src, tgt, rel_type), edge in self.edges.items():
            if src == source_id and tgt == target_id:
                edges.append(edge)
        return edges

    def get_node_edges(self, character_id: str) -> list[RelationshipEdge]:
        """特定のノードに関連するすべてのエッジを取得"""
        edges = []
        for key in self.node_edges.get(character_id, set()):
            if key in self.edges:
                edges.append(self.edges[key])
        return edges

    def get_edges_by_type(self, relationship_type: RelationshipType) -> list[RelationshipEdge]:
        """特定の関係タイプのすべてのエッジを取得"""
        edges = []
        for source_id, target_id in self.type_edges.get(relationship_type, set()):
            key = (source_id, target_id, relationship_type)
            if key in self.edges:
                edges.append(self.edges[key])
        return edges

    def has_node(self, character_id: str) -> bool:
        """ノードが存在するかチェック"""
        return character_id in self.nodes

    def has_edge(self, source_id: str, target_id: str, relationship_type: RelationshipType) -> bool:
        """エッジが存在するかチェック"""
        return (source_id, target_id, relationship_type) in self.edges

    def get_related_nodes(
        self, character_id: str, relationship_type: RelationshipType | None = None
    ) -> list[tuple[str, RelationshipEdge]]:
        """特定のキャラクターに関連するすべてのノードとエッジを取得"""
        related = []
        for key in self.node_edges.get(character_id, set()):
            if key in self.edges:
                edge = self.edges[key]
                # 自分自身以外のノードを取得
                other_id = edge.target_id if edge.source_id == character_id else edge.source_id
                # 関係タイプでフィルタリング（指定されている場合）
                if relationship_type is None or edge.relationship_type == relationship_type:
                    related.append((other_id, edge))
        return related

    def get_strongest_relationships(
        self,
        character_id: str,
        limit: int = 10,
        relationship_type: RelationshipType | None = None,
    ) -> list[tuple[str, RelationshipEdge, int]]:
        """最も強い関係（絶対値で）を取得"""
        relationships = []
        for other_id, edge in self.get_related_nodes(character_id, relationship_type):
            strength = abs(edge.level)
            relationships.append((other_id, edge, strength))

        # 強さでソート（降順）
        relationships.sort(key=lambda x: x[2], reverse=True)
        return relationships[:limit]

    def get_positive_relationships(
        self,
        character_id: str,
        relationship_type: RelationshipType | None = None,
        min_level: int = 20,
    ) -> list[tuple[str, RelationshipEdge]]:
        """肯定的な関係を取得"""
        positive = []
        for other_id, edge in self.get_related_nodes(character_id, relationship_type):
            if edge.level >= min_level:
                positive.append((other_id, edge))
        return positive

    def get_negative_relationships(
        self,
        character_id: str,
        relationship_type: RelationshipType | None = None,
        max_level: int = -20,
    ) -> list[tuple[str, RelationshipEdge]]:
        """否定的な関係を取得"""
        negative = []
        for other_id, edge in self.get_related_nodes(character_id, relationship_type):
            if edge.level <= max_level:
                negative.append((other_id, edge))
        return negative

    def apply_decay_to_all(self, current_time: float | None = None) -> dict[str, int]:
        """すべてのエッジに減衰を適用し、変更されたエッジ数を返す"""
        if current_time is None:
            current_time = time.time()

        changes = defaultdict(int)
        for edge in self.edges.values():
            change = edge.apply_decay(current_time)
            if change != 0:
                # ソースキャラクターIDとターゲットキャラクターIDの両方に変更を記録
                changes[edge.source_id] += abs(change)
                changes[edge.target_id] += abs(change)

        self.stats["last_updated"] = time.time()
        return dict(changes)

    def find_path(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType | None = None,
        max_hops: int = 6,
    ) -> list[str] | None:
        """二つのノード間のパスを見つける（BFS）"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        if source_id == target_id:
            return [source_id]

        # BFSキュー: (current_node_id, path_so_far)
        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_hops:
                continue

            # 隣接ノードを探索
            for neighbor_id, edge in self.get_related_nodes(current_id, relationship_type):
                if neighbor_id == target_id:
                    return path + [neighbor_id]

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None  # パスが見つからない

    def calculate_clustering_coefficient(self, character_id: str) -> float:
        """特定のノードのクラスタリング係数を計算"""
        neighbors = [nid for nid, _ in self.get_related_nodes(character_id)]
        if len(neighbors) < 2:
            return 0.0

        # 隣接ノード間の実際のエッジ数を数える
        actual_edges = 0
        possible_edges = len(neighbors) * (len(neighbors) - 1)  # 有向グラフの場合

        for i, neighbor_a in enumerate(neighbors):
            for neighbor_b in neighbors[i + 1 :]:
                # 両方向のエッジをチェック
                if self.has_edge(
                    neighbor_a, neighbor_b, RelationshipType.FRIENDSHIP
                ) or self.has_edge(neighbor_b, neighbor_a, RelationshipType.FRIENDSHIP):
                    actual_edges += 2  # 有向グラフなので両方向をカウント

        if possible_edges == 0:
            return 0.0

        return actual_edges / possible_edges

    def get_graph_statistics(self) -> dict[str, Any]:
        """グラフの統計情報を取得"""
        if not self.nodes:
            return {
                "node_count": 0,
                "edge_count": 0,
                "density": 0.0,
                "average_relationship_strength": 0.0,
                "relationship_type_distribution": {},
                "last_updated": self.stats["last_updated"],
            }

        node_count = len(self.nodes)
        edge_count = len(self.edges)

        # 有向グラフの密度: 実際のエッジ数 / 可能なエッジ数 (n*(n-1))
        max_possible_edges = node_count * (node_count - 1) if node_count > 1 else 0
        density = edge_count / max_possible_edges if max_possible_edges > 0 else 0.0

        # 関係タイプ別のエッジ数
        type_distribution = {}
        for rel_type in RelationshipType:
            count = len(self.get_edges_by_type(rel_type))
            if count > 0:
                type_distribution[rel_type.value] = count

        # 平均関係強度
        if self.edges:
            avg_strength = sum(abs(edge.level) for edge in self.edges.values()) / len(self.edges)
        else:
            avg_strength = 0.0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
            "average_relationship_strength": avg_strength,
            "relationship_type_distribution": type_distribution,
            "last_updated": self.stats["last_updated"],
        }

    def to_dict(self) -> dict[str, Any]:
        """グラフを辞書形式に変換（セーブ用）"""
        return {
            "nodes": {
                char_id: {
                    "character_id": node.character_id,
                    "name": node.name,
                    "personality_traits": node.personality_traits,
                    "faction_affiliations": {
                        fid: aff.value for fid, aff in node.faction_affiliations.items()
                    },
                    "memory_fragments": node.memory_fragments,
                    "created_at": node.created_at,
                }
                for char_id, node in self.nodes.items()
            },
            "edges": {
                f"{source_id}_{target_id}_{rel_type.value}": {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relationship_type": edge.relationship_type.value,
                    "level": edge.level,
                    "decay_rate": edge.decay_rate,
                    "last_interaction": edge.last_interaction,
                    "is_mutual": edge.is_mutual,
                    "modifiers": [
                        {
                            "interaction_type": mod.interaction_type.value,
                            "amount": mod.amount,
                            "multiplier": mod.multiplier,
                            "timestamp": mod.timestamp,
                            "context": mod.context,
                        }
                        for mod in edge.modifiers
                    ],
                }
                for (source_id, target_id, rel_type), edge in self.edges.items()
            },
            "stats": self.stats.copy(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipGraph:
        """辞書形式からグラフを復元（ロード用）"""
        graph = cls()

        # ノードを復元
        for node_data in data.get("nodes", {}).values():
            faction_affils = {}
            for fid, aff_str in node_data.get("faction_affiliations", {}).items():
                try:
                    faction_affils[fid] = FactionAffiliation(aff_str)
                except ValueError:
                    faction_affils[fid] = FactionAffiliation.NEUTRAL

            node = RelationshipNode(
                character_id=node_data["character_id"],
                name=node_data["name"],
                personality_traits=node_data.get("personality_traits", {}),
                faction_affiliations=faction_affils,
                memory_fragments=node_data.get("memory_fragments", []),
                created_at=node_data.get("created_at", time.time()),
            )
            graph.add_node(node)

        # エッジを復元
        for edge_data in data.get("edges", {}).values():
            try:
                rel_type = RelationshipType(edge_data["relationship_type"])
                edge = RelationshipEdge(
                    source_id=edge_data["source_id"],
                    target_id=edge_data["target_id"],
                    relationship_type=rel_type,
                    level=edge_data.get("level", 0),
                    decay_rate=edge_data.get("decay_rate", 0.01),
                    last_interaction=edge_data.get("last_interaction", time.time()),
                    is_mutual=edge_data.get("is_mutual", True),
                )

                # 修正子を復元
                for mod_data in edge_data.get("modifiers", []):
                    try:
                        interaction_type = InteractionType(mod_data["interaction_type"])
                        modifier = RelationshipModifier(
                            interaction_type=interaction_type,
                            amount=mod_data["amount"],
                            multiplier=mod_data.get("multiplier", 1.0),
                            timestamp=mod_data.get("timestamp", time.time()),
                            context=mod_data.get("context", {}),
                        )
                        edge.modifiers.append(modifier)
                    except (ValueError, KeyError):
                        # 無効な修正子データはスキップ
                        continue

                graph.add_edge(edge)
            except (ValueError, KeyError):
                # 無効なエッジデータはスキップ
                continue

        # 統計情報を復元
        graph.stats.update(
            data.get("stats", {"node_count": 0, "edge_count": 0, "last_updated": time.time()})
        )

        return graph
