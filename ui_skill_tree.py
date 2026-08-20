"""Proposal 9: Skill Tree Visualization / UI data.

Produces structured progress info and an ASCII visualization of a player's
skill tree, mirroring the spec's UI layout.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class SkillNodeView:
    tier_id: str
    name: str
    learned: bool
    available: bool
    prerequisites: List[str]
    progress_pct: int  # 0-100, based on cost vs earned points (for display)


class SkillTreeRenderer:
    """Builds view models and ASCII art for the skill tree UI."""

    def __init__(self, registry, manager):
        self.registry = registry
        self.manager = manager

    def build_nodes(self, player) -> Dict[str, List[SkillNodeView]]:
        result: Dict[str, List[SkillNodeView]] = {}
        for tree_id, tree in self.registry.all().items():
            earned = player.total_skill_points_earned
            nodes = []
            for tier in tree.tiers:
                learned = tier.id in player.skill_tree_progress.get(tree_id, [])
                available = (not learned) and self.manager.check_prerequisites(player, tier)
                pct = 100 if learned else (int(min(100, earned / tier.cost * 100)) if tier.cost else 0)
                nodes.append(SkillNodeView(
                    tier_id=tier.id,
                    name=tier.name,
                    learned=learned,
                    available=available,
                    prerequisites=list(tier.prerequisites),
                    progress_pct=pct,
                ))
            result[tree_id] = nodes
        return result

    def render_text(self, player, tree_id: str) -> str:
        tree = self.registry.get(tree_id)
        if tree is None:
            return f"(unknown tree: {tree_id})"
        nodes = self.build_nodes(player).get(tree_id, [])
        lines = [f"┌─ {tree.name} ─{'─' * 40}┐"]
        for n in nodes:
            mark = "[●]" if n.learned else ("[○]" if n.available else "[✗]")
            bar = "▓" * (n.progress_pct // 10) + "░" * (10 - n.progress_pct // 10)
            pre = ",".join(n.prerequisites) if n.prerequisites else "-"
            status = "習得済み" if n.learned else ("習得可能" if n.available else "🔒")
            lines.append(f"│ {mark} {n.name} ({n.progress_pct}%) {bar} {status}")
            lines.append(f"│   └─ 前提: {pre}")
        lines.append("└" + "─" * 48 + "┘")
        return "\n".join(lines)
