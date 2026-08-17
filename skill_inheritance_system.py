"""
Skill Inheritance System Module (Steps 65-69)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


# Step 66: SkillInheritanceData
@dataclass
class SkillInheritanceData:
    """スキル継承データ (Step 66)"""
    id: str
    name: str = ""
    description: str = ""
    inheritance_type: str = ""
    eligible_skills: List[str] = field(default_factory=list)
    inheritance_rate: float = 0.50
    level_bonus: int = 5
    requirements: Dict[str, Any] = field(default_factory=dict)


# Step 67, 68: SkillInheritanceRegistry
class SkillInheritanceRegistry:
    """スキル継承レジストリ (Step 67, 68)"""
    _instance: Optional[SkillInheritanceRegistry] = None

    def __new__(cls) -> SkillInheritanceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._rules = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_inheritance.yaml") -> None:
        """YAMLからスキル継承設定を読み込む (Step 68)"""
        self._rules = {}
        if not os.path.exists(file_path):
            self._rules["bloodline_skills"] = SkillInheritanceData(
                id="bloodline_skills", name="血統スキル継承", eligible_skills=["martial_arts", "swordsmanship"]
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        r_dict = raw.get("inheritance_rules", {})
        for rid, rdata in r_dict.items():
            self._rules[rid] = SkillInheritanceData(
                id=rid,
                name=rdata.get("name", rid),
                description=rdata.get("description", ""),
                inheritance_type=rdata.get("inheritance_type", ""),
                eligible_skills=rdata.get("eligible_skills", []),
                inheritance_rate=float(rdata.get("inheritance_rate", 0.50)),
                level_bonus=int(rdata.get("level_bonus", 5)),
                requirements=rdata.get("requirements", {})
            )

    def get(self, rule_id: str) -> Optional[SkillInheritanceData]:
        return self._rules.get(rule_id)

    def all(self) -> Dict[str, SkillInheritanceData]:
        return dict(self._rules)


REGISTRY = SkillInheritanceRegistry()


# Step 69: SkillInheritanceManager
class SkillInheritanceManager:
    """スキル継承管理 (Step 69)"""
    def __init__(self, registry: Optional[SkillInheritanceRegistry] = None):
        self.registry = registry or REGISTRY

    def get_inheritable_skills(self, player: "Entity", rule_id: str = "bloodline_skills") -> List[str]:
        """継承可能なスキル一覧を取得 (Step 69)"""
        rule = self.registry.get(rule_id)
        if not rule or not player:
            return []

        return [sk for sk in rule.eligible_skills if sk in player.skills]

    def inherit_skill(self, player: "Entity", skill_name: str, rule_id: str = "bloodline_skills") -> bool:
        """スキル継承を実行 (Step 69)"""
        rule = self.registry.get(rule_id)
        if not rule or skill_name not in rule.eligible_skills:
            return False

        if skill_name not in player.inheritable_skills:
            player.inheritable_skills.append(skill_name)
        return True
