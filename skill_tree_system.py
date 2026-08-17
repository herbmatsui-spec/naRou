"""
スキルツリーシステム
スキルツリー定義の読み込み・習得条件判定・効果適用・専用スキル管理
Steps 11-22, 59, 60
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
import yaml
from pathlib import Path

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class SkillTreeEffect:
    """スキルツリー効果 (Step 12)"""
    type: str                                    # damage_bonus, unlock_skill, crit_chance 等
    value: Union[int, float, str]               # 補正値または解放スキルID
    target: Optional[str] = None                # melee, magic, unarmed, active, passive 等


@dataclass
class SkillTreeTier:
    """スキルツリーのティア/ノード (Step 13)"""
    id: str
    name: str
    description: str
    cost: int = 5
    prerequisites: List[str] = field(default_factory=list)
    effects: List[SkillTreeEffect] = field(default_factory=list)


@dataclass
class SkillTree:
    """スキルツリー (Step 14)"""
    id: str
    name: str
    icon: str = "⚔"
    tiers: List[SkillTreeTier] = field(default_factory=list)


class SkillTreeRegistry:
    """スキルツリーレジストリ (シングルトン) (Steps 15-17)"""
    _instance: Optional['SkillTreeRegistry'] = None
    _trees: Dict[str, SkillTree] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._trees = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/skill_trees.yaml") -> None:
        """YAMLからスキルツリー定義をロード (Step 16)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            trees_data = data.get('skill_trees', {})
            for tree_id, t in trees_data.items():
                tier_objs = []
                for tier in t.get('tiers', []):
                    effects = [
                        SkillTreeEffect(
                            type=e.get('type', ''),
                            value=e.get('value', 0),
                            target=e.get('target')
                        )
                        for e in tier.get('effects', [])
                    ]
                    tier_objs.append(
                        SkillTreeTier(
                            id=tier.get('id', ''),
                            name=tier.get('name', ''),
                            description=tier.get('description', ''),
                            cost=tier.get('cost', 5),
                            prerequisites=tier.get('prerequisites', []),
                            effects=effects
                        )
                    )
                self._trees[tree_id] = SkillTree(
                    id=tree_id,
                    name=t.get('name', tree_id),
                    icon=t.get('icon', '⚔'),
                    tiers=tier_objs
                )
            self._loaded = True
        except Exception:
            self._loaded = True

    def get(self, tree_id: str) -> Optional[SkillTree]:
        """特定ツリーを取得 (Step 17)"""
        return self._trees.get(tree_id)

    def all(self) -> Dict[str, SkillTree]:
        """すべてのスキルツリー辞書を返す (Step 17)"""
        return self._trees


REGISTRY = SkillTreeRegistry()


class SkillTreeManager:
    """スキルツリー管理・習得判定マネージャー (Steps 18-22, 59, 60)"""

    def __init__(self, registry: Optional[SkillTreeRegistry] = None):
        self.registry = registry or REGISTRY

    def check_prerequisites(self, player: 'Entity', tier: SkillTreeTier) -> bool:
        """前提スキルの習得状況をチェック (Step 19)"""
        if not tier.prerequisites:
            return True
        learned = self.get_learned_skills(player)
        return all(req in learned for req in tier.prerequisites)

    def learn_skill(self, player: 'Entity', tree_id: str, tier_id: str) -> bool:
        """スキルツリーのティアを習得 (Step 20)"""
        tree = self.registry.get(tree_id)
        if not tree:
            return False

        tier = next((t for t in tree.tiers if t.id == tier_id), None)
        if not tier:
            return False

        # 既に習得済みか確認
        if tree_id not in player.skill_tree_progress:
            player.skill_tree_progress[tree_id] = []
        if tier_id in player.skill_tree_progress[tree_id]:
            return False

        # 前提条件チェック
        if not self.check_prerequisites(player, tier):
            return False

        # スキルポイント消費チェック
        if player.skill_points < tier.cost:
            return False

        player.skill_points -= tier.cost
        player.skill_tree_progress[tree_id].append(tier_id)

        # パッシブ/アクティブ効果適用
        for eff in tier.effects:
            if eff.type == "unlock_skill" and isinstance(eff.value, str):
                if eff.value not in player.gene_skills:
                    player.gene_skills.append(eff.value)

        return True

    def get_available_skills(self, player: 'Entity') -> List[Dict[str, Any]]:
        """未習得かつ前提条件を満たしている習得可能なスキル一覧を取得 (Step 21)"""
        available = []
        for tree_id, tree in self.registry.all().items():
            learned_in_tree = player.skill_tree_progress.get(tree_id, [])
            for tier in tree.tiers:
                if tier.id not in learned_in_tree and self.check_prerequisites(player, tier):
                    available.append({
                        "tree_id": tree_id,
                        "tree": tree.name,
                        "tier_id": tier.id,
                        "tier": tier.name,
                        "cost": tier.cost,
                        "description": tier.description,
                        "effects": tier.effects,
                        "can_afford": player.skill_points >= tier.cost
                    })
        return available

    def get_learned_skills(self, player: 'Entity') -> List[str]:
        """習得済みスキルIDリストをフラットにして返す (Step 22)"""
        learned: List[str] = []
        for skills in getattr(player, 'skill_tree_progress', {}).values():
            learned.extend(skills)
        return learned

    # === エクスクルーシブスキル関連 (Steps 59, 60) ===
    def check_exclusive_learnable(self, player: 'Entity', exclusive_skill_data: Any) -> bool:
        """エクスクルーシブスキル習得可否判定 (Step 59, 60)"""
        if not exclusive_skill_data:
            return False
        # ジョブ一致チェック
        req_job = getattr(exclusive_skill_data, 'job', None) or (exclusive_skill_data.get('job') if isinstance(exclusive_skill_data, dict) else None)
        if req_job and player.job != req_job and req_job not in getattr(player, 'mastered_jobs', []):
            return False
        return True

    def learn_exclusive_skill(self, player: 'Entity', skill_id: str, cost: int = 15) -> bool:
        """エクスクルーシブスキルの習得 (Step 60)"""
        if skill_id in getattr(player, 'mastered_exclusive_skills', []):
            return False
        if player.skill_points < cost:
            return False
        player.skill_points -= cost
        player.mastered_exclusive_skills.append(skill_id)
        return True

    def get_learned_exclusive_skills(self, player: 'Entity') -> List[str]:
        """習得済みエクスクルーシブスキル一覧を取得 (Step 59)"""
        return list(getattr(player, 'mastered_exclusive_skills', []))
