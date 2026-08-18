"""
Skill Specialization System Module (Steps 70, 71)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity


# Step 71: SkillSpecializationData
@dataclass
class SkillSpecializationData:
    """スキル専門化データ (Step 71)"""
    id: str
    name: str = ""
    description: str = ""
    base_skill: str = ""
    branches: List[Dict[str, Any]] = field(default_factory=list)


# SkillSpecializationRegistry
class SkillSpecializationRegistry:
    """スキル専門化レジストリ"""
    _instance: Optional[SkillSpecializationRegistry] = None

    def __new__(cls) -> SkillSpecializationRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._paths = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_specialization.yaml") -> None:
        """YAMLからスキル専門化設定を読み込む"""
        self._paths = {}
        if not os.path.exists(file_path):
            self._paths["fireball_specialization"] = SkillSpecializationData(
                id="fireball_specialization", name="火炎魔導専門化パス", base_skill="magic_cast"
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        p_dict = raw.get("specialization_paths", {})
        for pid, pdata in p_dict.items():
            self._paths[pid] = SkillSpecializationData(
                id=pid,
                name=pdata.get("name", pid),
                description=pdata.get("description", ""),
                base_skill=pdata.get("base_skill", ""),
                branches=pdata.get("branches", [])
            )

    def get(self, path_id: str) -> Optional[SkillSpecializationData]:
        return self._paths.get(path_id)

    def all(self) -> Dict[str, SkillSpecializationData]:
        return dict(self._paths)


REGISTRY = SkillSpecializationRegistry()


# SkillSpecializationManager
class SkillSpecializationManager:
    """スキル専門化管理"""
    def __init__(self, registry: Optional[SkillSpecializationRegistry] = None):
        self.registry = registry or REGISTRY

    def can_specialize(self, player: "Entity", path_id: str, branch_id: str) -> bool:
        path = self.registry.get(path_id)
        if not path or not player:
            return False

        if path.base_skill not in player.skills:
            return False

        for b in path.branches:
            if b.get("id") == branch_id:
                return True
        return False

    def specialize_skill(self, player: "Entity", path_id: str, branch_id: str, engine: Optional[Any] = None) -> bool:
        if not self.can_specialize(player, path_id, branch_id):
            return False

        player.skill_specialization[path_id] = branch_id
        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"★専門化完了！ 【{path_id}】を【{branch_id}】へ特化！", (255, 215, 0))

        return True
