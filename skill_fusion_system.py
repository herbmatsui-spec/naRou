"""
Skill Fusion Core System Module (Steps 29-35)
"""

from __future__ import annotations
import os
import yaml
import random
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


@dataclass
class FusionEffect:
    type: str
    value: int = 0


# Step 30: SkillFusionData
@dataclass
class SkillFusionData:
    """スキル融合レシピデータ (Step 30)"""
    id: str
    name: str = ""
    description: str = ""
    inputs: List[str] = field(default_factory=list)
    output: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 1.0
    failure_penalty: str = "lose_material"
    required_skills: List[str] = field(default_factory=list)
    required_job: Optional[str] = None
    required_level: int = 1
    results: List[str] = field(default_factory=list)
    effects: List[FusionEffect] = field(default_factory=list)


# Step 31, 32: SkillFusionRegistry
class SkillFusionRegistry:
    """スキル融合レジストリ (Step 31, 32)"""
    _instance: Optional[SkillFusionRegistry] = None

    def __new__(cls) -> SkillFusionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._recipes = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_fusion.yaml") -> None:
        """YAMLからスキル融合レシピを読み込む (Step 32)"""
        self._recipes = {}
        if not os.path.exists(file_path):
            self._recipes["fireball_fusion"] = SkillFusionData(
                id="fireball_fusion", name="火炎爆砕合成", inputs=["magic_dart", "fire_essence"], output="mega_fireball"
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        r_dict = raw.get("fusion_recipes", {})
        for rid, rdata in r_dict.items():
            self._recipes[rid] = SkillFusionData(
                id=rid,
                name=rdata.get("name", rid),
                description=rdata.get("description", ""),
                inputs=rdata.get("inputs", []),
                output=rdata.get("output", ""),
                requirements=rdata.get("requirements", {}),
                success_rate=float(rdata.get("success_rate", 1.0)),
                failure_penalty=rdata.get("failure_penalty", "lose_material")
            )

        f_dict = raw.get("fusions", {})
        for fid, fdata in f_dict.items():
            effs = [FusionEffect(e.get("type", ""), e.get("value", 0)) for e in fdata.get("effects", [])]
            self._recipes[fid] = SkillFusionData(
                id=fid,
                name=fdata.get("name", fid),
                description=fdata.get("description", ""),
                required_skills=fdata.get("required_skills", []),
                required_job=fdata.get("required_job"),
                required_level=fdata.get("required_level", 1),
                results=fdata.get("results", []),
                effects=effs
            )

    def get(self, recipe_id: str) -> Optional[SkillFusionData]:
        return self._recipes.get(recipe_id)

    def all(self) -> Dict[str, SkillFusionData]:
        return dict(self._recipes)


REGISTRY = SkillFusionRegistry()
FusionRegistry = SkillFusionRegistry
FusionData = SkillFusionData


# Step 33-35: SkillFusionManager
class SkillFusionManager:
    """スキル融合管理 (Steps 33-35)"""
    def __init__(self, registry: Optional[SkillFusionRegistry] = None):
        self.registry = registry or REGISTRY

    def can_fuse(self, player: "Entity", recipe_id: str) -> bool:
        """スキル融合が可能かを判定 (Step 34)"""
        recipe = self.registry.get(recipe_id)
        if not recipe or not player:
            return False

        req = recipe.requirements
        req_lvl = req.get("player_level", 1)
        if player.level < req_lvl:
            return False

        # 素材所持またはスキル習得チェック
        for inp in recipe.inputs:
            has_mat = player.skill_fusion_materials.get(inp, 0) > 0
            has_sk = inp in player.skills
            if not has_mat and not has_sk:
                return False

        # 必要スキルレベルチェック
        req_sk = req.get("skill_level", {})
        for sk_name, req_slvl in req_sk.items():
            if sk_name not in player.skills or player.skills[sk_name].level < req_slvl:
                return False

        return True

    def fuse_skills(self, player: "Entity", recipe_id: str, engine: Optional[Any] = None) -> Tuple[bool, str]:
        """スキル融合を実行 (Step 35)"""
        if not self.can_fuse(player, recipe_id):
            return False, "融合条件を満たしていません。"

        recipe = self.registry.get(recipe_id)
        if not recipe:
            return False, "無効なレシピです。"

        # 成功判定
        is_success = recipe.success_rate >= 0.8 or (random.random() <= recipe.success_rate)

        # 素材消費
        for inp in recipe.inputs:
            if inp in player.skill_fusion_materials and player.skill_fusion_materials[inp] > 0:
                player.skill_fusion_materials[inp] -= 1

        if is_success:
            from entity import Skill
            if recipe.output not in player.skills:
                player.skills[recipe.output] = Skill(recipe.output, level=1)
            player.fusion_chain_progress[recipe_id] = player.fusion_chain_progress.get(recipe_id, 0) + 1
            if engine:
                from sound_manager import SoundManager
                SoundManager.play_se("level_up")
                engine.log(f"★スキル融合成功！ 新スキル【{recipe.output}】を創出した！", (255, 215, 0))
            return True, f"スキル融合に成功し、【{recipe.output}】を獲得した！"
        else:
            if engine:
                engine.log(f"スキル融合に失敗した…素材が失われた。", (255, 100, 100))
            return False, "スキル融合に失敗しました。"
