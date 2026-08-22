"""
NPC Relationship Simulation - Visualization and Debug Tools
Step 15: Relationship visualization/debug tools
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import RelationshipType


class VisualizationFormat(Enum):
    """可視化フォーマット"""

    TEXT = "text"  # テキスト形式
    JSON = "json"  # JSON形式
    DOT = "dot"  # Graphviz DOT形式
    MERMAD = "mermaid"  # Mermaid形式


@dataclass
class RelationshipInsight:
    """関係の洞察"""

    character_id: str
    most_positive: list[tuple[str, RelationshipType, int]]
    most_negative: list[tuple[str, RelationshipType, int]]
    strongest_bonds: list[tuple[str, RelationshipType, int]]
    conflict_count: int
    romance_count: int
    mentorship_count: int


class RelationshipVisualizer:
    """
    関係可視化とデバッグツール
    関係グラフの視覚的表示、分析、デバッグ機能
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

    def visualize_as_text(self, character_id: str | None = None, detailed: bool = False) -> str:
        """テキスト形式で可視化"""
        lines = []
        lines.append("=" * 60)
        lines.append("NPC関係グラフ - 可視化（テキスト形式）")
        lines.append("=" * 60)

        if character_id:
            # 特定のキャラクターの関係を表示
            node = self.graph.get_node(character_id)
            if not node:
                return f"キャラクター {character_id} が見つかりません"

            lines.append(f"\n【{node.name}】（ID: {character_id}）")

            # パーソナリティ
            if node.personality_traits:
                traits_str = ", ".join(f"{k}: {v:.2f}" for k, v in node.personality_traits.items())
                lines.append(f"  パーソナリティ: {traits_str}")

            # 派閥所属
            if node.faction_affiliations:
                factions_str = ", ".join(
                    f"{k}={v.value}" for k, v in node.faction_affiliations.items()
                )
                lines.append(f"  派閥: {factions_str}")

            lines.append("\n  関係一覧:")
            related = self.graph.get_related_nodes(character_id)

            if not related:
                lines.append("    （関係なし）")
            else:
                for other_id, edge in related:
                    other_node = self.graph.get_node(other_id)
                    other_name = other_node.name if other_node else other_id
                    level = edge.level
                    category = edge.get_level_category()

                    bar = self._create_level_bar(level)
                    lines.append(f"    → {other_name} [{edge.relationship_type.value}]")
                    lines.append(f"       レベル: {level:3d} {category.name:15s} {bar}")

                    if detailed:
                        lines.append(f"       減衰率: {edge.decay_rate:.4f}")
                        lines.append(
                            f"       最終インタラクション: {time.strftime('%Y-%m-%d %H:%M', time.localtime(edge.last_interaction))}"
                        )
                        if edge.modifiers:
                            lines.append(f"       修正子数: {len(edge.modifiers)}")
        else:
            # 全体の概要を表示
            stats = self.graph.get_graph_statistics()
            lines.append(f"\nノード数: {stats['node_count']}")
            lines.append(f"エッジ数: {stats['edge_count']}")
            lines.append(f"グラフ密度: {stats['density']:.4f}")
            lines.append(f"平均関係強度: {stats['average_relationship_strength']:.2f}")

            lines.append("\n関係タイプ分布:")
            for rel_type, count in stats["relationship_type_distribution"].items():
                lines.append(f"  {rel_type}: {count}")

            lines.append("\nキャラクター一覧:")
            for char_id, node in self.graph.nodes.items():
                rel_count = len(self.graph.get_related_nodes(char_id))
                lines.append(f"  {node.name} (ID: {char_id}) - 関係数: {rel_count}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def _create_level_bar(self, level: int, width: int = 20) -> str:
        """レベルバーを作成（-100〜+100を-10〜+10のバーで表示）"""
        normalized = level / 10  # -10〜+10
        center = width // 2
        filled = int(abs(normalized))

        if level >= 0:
            return " " * center + "+" + "=" * filled
        else:
            return "-" * filled + "+" + " " * (center - 1)

    def visualize_as_json(self, character_id: str | None = None) -> str:
        """JSON形式で可視化"""
        if character_id:
            node = self.graph.get_node(character_id)
            if not node:
                return json.dumps({"error": "character_not_found"})

            data = {
                "character_id": character_id,
                "name": node.name,
                "relationships": [],
            }

            for other_id, edge in self.graph.get_related_nodes(character_id):
                other_node = self.graph.get_node(other_id)
                data["relationships"].append(
                    {
                        "other_id": other_id,
                        "other_name": other_node.name if other_node else other_id,
                        "relationship_type": edge.relationship_type.value,
                        "level": edge.level,
                        "category": edge.get_level_category().name,
                        "decay_rate": edge.decay_rate,
                    }
                )
        else:
            data = self.graph.to_dict()

        return json.dumps(data, indent=2, ensure_ascii=False)

    def visualize_as_dot(self, character_id: str | None = None) -> str:
        """Graphviz DOT形式で可視化"""
        lines = ["digraph RelationshipGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")

        if character_id:
            # 特定のキャラクターとその関係のみ
            related = self.graph.get_related_nodes(character_id)
            for other_id, edge in related:
                color = self._get_edge_color(edge.level)
                lines.append(
                    f'  "{character_id}" -> "{other_id}" [label="{edge.relationship_type.value}: {edge.level}", color={color}];'
                )
        else:
            # 全体
            for edge in self.graph.edges.values():
                color = self._get_edge_color(edge.level)
                lines.append(
                    f'  "{edge.source_id}" -> "{edge.target_id}" [label="{edge.relationship_type.value}: {edge.level}", color={color}];'
                )

        lines.append("}")
        return "\n".join(lines)

    def visualize_as_mermaid(self, character_id: str | None = None) -> str:
        """Mermaid形式で可視化"""
        lines = ["graph LR"]

        if character_id:
            related = self.graph.get_related_nodes(character_id)
            for other_id, edge in related:
                line_style = self._get_mermaid_style(edge.level)
                lines.append(
                    f"  {character_id}[{character_id}] {line_style} {other_id}[{other_id}]"
                )
                lines.append(f"  style {character_id} fill:#f9f,stroke:#333")
        else:
            for edge in self.graph.edges.values():
                line_style = self._get_mermaid_style(edge.level)
                lines.append(f"  {edge.source_id} {line_style} {edge.target_id}")

        return "\n".join(lines)

    def _get_edge_color(self, level: int) -> str:
        """レベルからエッジの色を決定"""
        if level >= 60:
            return "green"
        elif level >= 20:
            return "lightgreen"
        elif level > -20:
            return "gray"
        elif level > -60:
            return "orange"
        else:
            return "red"

    def _get_mermaid_style(self, level: int) -> str:
        """レベルからMermaidの線スタイルを決定"""
        if level >= 20:
            return "---"
        elif level > -20:
            return "-.-"
        else:
            return "==="

    def export_visualization(
        self,
        format: VisualizationFormat = VisualizationFormat.TEXT,
        character_id: str | None = None,
        filename: str | None = None,
    ) -> str:
        """可視化をエクスポート"""
        if format == VisualizationFormat.TEXT:
            content = self.visualize_as_text(character_id, detailed=True)
        elif format == VisualizationFormat.JSON:
            content = self.visualize_as_json(character_id)
        elif format == VisualizationFormat.DOT:
            content = self.visualize_as_dot(character_id)
        elif format == VisualizationFormat.MERMAD:
            content = self.visualize_as_mermaid(character_id)
        else:
            content = self.visualize_as_text(character_id)

        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

        return content

    def generate_insights(self, character_id: str) -> RelationshipInsight | None:
        """キャラクターの関係洞察を生成"""
        node = self.graph.get_node(character_id)
        if not node:
            return None

        related = self.graph.get_related_nodes(character_id)

        # 関係をリスト化
        relationships = []
        for other_id, edge in related:
            relationships.append((other_id, edge.relationship_type, edge.level))

        # 正の関係（上位5）
        positive = sorted([r for r in relationships if r[2] > 0], key=lambda x: x[2], reverse=True)[
            :5
        ]

        # 負の関係（下位5）
        negative = sorted([r for r in relationships if r[2] < 0], key=lambda x: x[2])[:5]

        # 最強の絆
        strongest = sorted(relationships, key=lambda x: abs(x[2]), reverse=True)[:5]

        # カウント
        conflict_count = sum(
            1 for r in relationships if r[1] == RelationshipType.ENMITY and r[2] < 0
        )
        romance_count = sum(
            1 for r in relationships if r[1] == RelationshipType.ROMANCE and r[2] > 20
        )
        mentorship_count = sum(
            1 for r in relationships if r[1] == RelationshipType.MENTORSHIP and r[2] > 20
        )

        return RelationshipInsight(
            character_id=character_id,
            most_positive=positive,
            most_negative=negative,
            strongest_bonds=strongest,
            conflict_count=conflict_count,
            romance_count=romance_count,
            mentorship_count=mentorship_count,
        )

    def analyze_graph_health(self) -> dict[str, Any]:
        """グラフの健全性を分析"""
        stats = self.graph.get_graph_statistics()

        # 孤立したノードを検出
        isolated_nodes = []
        for char_id in self.graph.nodes:
            if not self.graph.get_related_nodes(char_id):
                isolated_nodes.append(char_id)

        # 極端な関係を検出
        extreme_positive = []
        extreme_negative = []
        for edge in self.graph.edges.values():
            if edge.level >= 90:
                extreme_positive.append(
                    (
                        edge.source_id,
                        edge.target_id,
                        edge.relationship_type.value,
                        edge.level,
                    )
                )
            elif edge.level <= -90:
                extreme_negative.append(
                    (
                        edge.source_id,
                        edge.target_id,
                        edge.relationship_type.value,
                        edge.level,
                    )
                )

        return {
            "total_nodes": stats["node_count"],
            "total_edges": stats["edge_count"],
            "density": stats["density"],
            "average_strength": stats["average_relationship_strength"],
            "isolated_nodes": isolated_nodes,
            "extreme_positive_count": len(extreme_positive),
            "extreme_negative_count": len(extreme_negative),
            "health_score": self._calculate_health_score(stats, len(isolated_nodes)),
        }

    def _calculate_health_score(self, stats: dict[str, Any], isolated_count: int) -> float:
        """健全性スコアを計算（0-100）"""
        if stats["node_count"] == 0:
            return 100.0

        # 基本スコア：密度ベース（適度な密度が健全）
        density = stats["density"]
        if density == 0:
            base_score = 50.0
        else:
            base_score = min(100.0, density * 1000)  # 密度が高いほどスコア高（調整必要）

        # 孤立ノードによるペナルティ
        isolation_penalty = (isolated_count / stats["node_count"]) * 50.0

        return max(0.0, min(100.0, base_score - isolation_penalty))

    def trace_relationship_path(
        self, source_id: str, target_id: str, max_hops: int = 6
    ) -> list[tuple[str, str, str]] | None:
        """二つのキャラクター間の関係経路を追跡"""
        path = self.graph.find_path(source_id, target_id, max_hops=max_hops)
        if not path:
            return None

        # パスを関係エッジに変換
        edges_in_path = []
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]

            # 関係エッジを検索
            best_edge = None
            best_abs_level = -1
            for (s, t, rel_type), edge in self.graph.edges.items():
                if (s == from_id and t == to_id) or (s == to_id and t == from_id):
                    if abs(edge.level) > best_abs_level:
                        best_abs_level = abs(edge.level)
                        best_edge = (s, t, rel_type.value, edge.level)

            if best_edge:
                edges_in_path.append(best_edge)

        return edges_in_path

    def debug_relationship(
        self,
        character_a: str,
        character_b: str,
        relationship_type: RelationshipType | None = None,
    ) -> str:
        """関係の詳細デバッグ情報を出力"""
        lines = []
        lines.append(f"=== 関係デバッグ: {character_a} ↔ {character_b} ===")

        if relationship_type:
            edge = self.graph.get_edge(character_a, character_b, relationship_type)
            if not edge:
                return f"エッジが見つかりません: {relationship_type.value}"

            lines.append(f"関係タイプ: {edge.relationship_type.value}")
            lines.append(f"レベル: {edge.level} (カテゴリ: {edge.get_level_category().name})")
            lines.append(f"減衰率: {edge.decay_rate}")
            lines.append(f"相互関係: {edge.is_mutual}")
            lines.append(f"最終インタラクション: {edge.last_interaction}")
            lines.append(f"\n修正子履歴 ({len(edge.modifiers)}件):")
            for i, mod in enumerate(edge.modifiers[-10:], 1):  # 最新10件
                lines.append(
                    f"  {i}. {mod.interaction_type.value}: {mod.amount:+d} "
                    f"(x{mod.multiplier:.2f}) @ {time.strftime('%Y-%m-%d %H:%M', time.localtime(mod.timestamp))}"
                )
        else:
            edges = self.graph.get_edges_between(character_a, character_b)
            if not edges:
                return "関係が見つかりません"

            for edge in edges:
                lines.append(f"\n関係タイプ: {edge.relationship_type.value}")
                lines.append(f"  レベル: {edge.level} (カテゴリ: {edge.get_level_category().name})")
                lines.append(f"  減衰率: {edge.decay_rate}")
                lines.append(f"  修正子数: {len(edge.modifiers)}")

        return "\n".join(lines)

    def create_debug_report(self, character_id: str | None = None) -> str:
        """デバッグレポートを作成"""
        lines = []
        lines.append("=" * 70)
        lines.append("NPC関係システム - デバッグレポート")
        lines.append(f"生成時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # グラフ健全性
        health = self.analyze_graph_health()
        lines.append("\n【グラフ健全性】")
        lines.append(f"  健全性スコア: {health['health_score']:.1f}/100")
        lines.append(f"  総ノード数: {health['total_nodes']}")
        lines.append(f"  総エッジ数: {health['total_edges']}")
        lines.append(f"  孤立ノード数: {len(health['isolated_nodes'])}")

        # 統計
        rm_stats = self.rm.get_statistics()
        lines.append("\n【システム統計】")
        lines.append(f"  テンプレート数: {rm_stats['template_count']}")
        lines.append(f"  初期化済み: {rm_stats['initialized']}")

        # 特定キャラクターの洞察
        if character_id:
            insight = self.generate_insights(character_id)
            if insight:
                lines.append(f"\n【{character_id}の洞察】")
                lines.append(f"  最も良好な関係: {len(insight.most_positive)}件")
                lines.append(f"  最も敵対的な関係: {len(insight.most_negative)}件")
                lines.append(f"  対立数: {insight.conflict_count}")
                lines.append(f"  恋愛関係数: {insight.romance_count}")
                lines.append(f"  師弟関係数: {insight.mentorship_count}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


# デバッグコマンド用のヘルパー関数
def debug_command_visualize(
    rm: RelationshipManager, character_id: str | None = None, format: str = "text"
) -> str:
    """デバッグコマンド：可視化"""
    visualizer = RelationshipVisualizer(rm)
    fmt = VisualizationFormat(format)
    return visualizer.export_visualization(fmt, character_id)


def debug_command_analyze(rm: RelationshipManager) -> str:
    """デバッグコマンド：グラフ分析"""
    visualizer = RelationshipVisualizer(rm)
    health = visualizer.analyze_graph_health()
    return json.dumps(health, indent=2, ensure_ascii=False)


def debug_command_debug_relationship(
    rm: RelationshipManager, char_a: str, char_b: str, rel_type: str | None = None
) -> str:
    """デバッグコマンド：関係デバッグ"""
    visualizer = RelationshipVisualizer(rm)
    rel = RelationshipType(rel_type) if rel_type else None
    return visualizer.debug_relationship(char_a, char_b, rel)


def debug_command_report(rm: RelationshipManager, character_id: str | None = None) -> str:
    """デバッグコマンド：レポート作成"""
    visualizer = RelationshipVisualizer(rm)
    return visualizer.create_debug_report(character_id)
