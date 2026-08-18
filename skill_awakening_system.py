"""
Skill Awakening System Module (Steps 43-49)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity


# Step 44: SkillAwakeningData
@dataclass
class SkillAwakeningData:
    """スキル覚醒データ (Step 44)"""
    id: str
    name: str = ""
    description: str = ""
    base_skill: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    awakened_skill: str = ""
    visual_effect: str = ""
    passive_effects: Dict[str, Any] = field(default_factory=dict)


# Step 45, 46: SkillAwakeningRegistry
class SkillAwakeningRegistry:
    """スキル覚醒レジストリ (Step 45, 46)"""
    _instance: Optional[SkillAwakeningRegistry] = None

    def __new__(cls) -> SkillAwakeningRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._awakenings = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_awakening.yaml") -> None:
        """YAMLからスキル覚醒設定を読み込む (Step 46)"""
        self._awakenings = {}
        if not os.path.exists(file_path):
            self._awakenings["dragon_slaying_awakening"] = SkillAwakeningData(
                id="dragon_slaying_awakening", name="竜殺しの覚醒", base_skill="swordsmanship", awakened_skill="true_dragon_slayer"
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        a_dict = raw.get("awakenings", {})
        for aid, adata in a_dict.items():
            self._awakenings[aid] = SkillAwakeningData(
                id=aid,
                name=adata.get("name", aid),
                description=adata.get("description", ""),
                base_skill=adata.get("base_skill", ""),
                requirements=adata.get("requirements", {}),
                awakened_skill=adata.get("awakened_skill", ""),
                visual_effect=adata.get("visual_effect", ""),
                passive_effects=adata.get("passive_effects", {})
            )

    def get(self, a_id: str) -> Optional[SkillAwakeningData]:
        return self._awakenings.get(a_id)

    def all(self) -> Dict[str, SkillAwakeningData]:
        return dict(self._awakenings)


REGISTRY = SkillAwakeningRegistry()


# Step 47-49: SkillAwakeningManager
class SkillAwakeningManager:
    """スキル覚醒管理 (Steps 47-49)"""
    def __init__(self, registry: Optional[SkillAwakeningRegistry] = None):
        self.registry = registry or REGISTRY

    def can_awaken(self, player: "Entity", awakening_id: str) -> bool:
        """スキル覚醒が可能かを判定 (Step 48)"""
        data = self.registry.get(awakening_id)
        if not data or not player:
            return False

        if awakening_id in player.awakened_skills:
            return False

        req = data.requirements
        # スキルレベルチェック
        req_sk = req.get("skill_level", {})
        for sk_name, req_slvl in req_sk.items():
            if sk_name not in player.skills or player.skills[sk_name].level < req_slvl:
                return False

        # 竜討伐数チェック
        if "dragon_kills" in req:
            dk = player.monster_killed_types.get("dragon", 0)
            if dk < req["dragon_kills"]:
                return False

        # 信仰値チェック
        if "piety" in req and player.piety < req["piety"]:
            return False

        return True

    def awaken_skill(self, player: "Entity", awakening_id: str, engine: Optional[Any] = None) -> bool:
        """スキルを覚醒させる (Step 49)"""
        if not self.can_awaken(player, awakening_id):
            return False

        data = self.registry.get(awakening_id)
        if not data:
            return False

        player.awakened_skills.append(awakening_id)
        from entity import Skill
        player.skills[data.awakened_skill] = Skill(data.awakened_skill, level=1)

        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"★真の力が目覚めた！ 【{data.name}】が覚醒！", (255, 215, 0))

        return True
