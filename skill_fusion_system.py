#!/usr/bin/env python3
"""
Skill Fusion System for naRou
Manages skill fusion mechanics allowing combination of skills into new abilities.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union, Tuple
import yaml
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class FusionEffect:
    """Represents a bonus effect from a skill fusion."""
    type: str
    value: Union[int, float, str]


@dataclass
class FusionData:
    """Represents a skill fusion definition."""
    id: str
    name: str
    description: str
    required_skills: List[str] = field(default_factory=list)
    required_job: Optional[str] = None
    required_god: Optional[str] = None
    result_skills: List[str] = field(default_factory=list)
    bonus_effects: List[FusionEffect] = field(default_factory=list)


class FusionRegistry:
    """Singleton registry for loading and accessing skill fusions."""
    
    _instance: Optional['FusionRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._fusions: Dict[str, FusionData] = {}
        self._initialized = True
    
    def load(self, path: str = "data/skill_fusion.yaml") -> None:
        """Load skill fusions from YAML file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Skill fusion file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load skill fusions: {e}")
            return
        
        if not data or 'fusions' not in data:
            logger.warning("No fusions key found in YAML")
            return
        
        self._fusions.clear()
        for fusion_id, fusion_data in data['fusions'].items():
            if not isinstance(fusion_data, dict):
                continue
            
            effects = []
            for eff_data in fusion_data.get('bonus_effects', []):
                effects.append(FusionEffect(
                    type=eff_data.get('type', ''),
                    value=eff_data.get('value', 0)
                ))
            
            fusion = FusionData(
                id=fusion_id,
                name=fusion_data.get('name', ''),
                description=fusion_data.get('description', ''),
                required_skills=fusion_data.get('required_skills', []),
                required_job=fusion_data.get('required_job'),
                required_god=fusion_data.get('required_god'),
                result_skills=fusion_data.get('result_skills', []),
                bonus_effects=effects
            )
            self._fusions[fusion_id] = fusion
        
        logger.info(f"Loaded {len(self._fusions)} skill fusions")
    
    def all(self) -> Dict[str, FusionData]:
        """Return all loaded skill fusions."""
        return self._fusions.copy()
    
    def get(self, fusion_id: str) -> Optional[FusionData]:
        """Get a specific skill fusion by ID."""
        return self._fusions.get(fusion_id)


class FusionManager:
    """Manages skill fusion checking and application for players."""
    
    def __init__(self, registry: FusionRegistry, skill_registry=None, job_registry=None):
        self.registry = registry
        self.skill_registry = skill_registry
        self.job_registry = job_registry
    
    def check_fusion_conditions(self, player, fusion_data) -> bool:
        """
        Check if player meets all conditions for a skill fusion.
        
        Args:
            player: Player entity
            fusion_data: FusionData to check
            
        Returns:
            True if all conditions are met, False otherwise
        """
        # Check required skills
        for skill_id in fusion_data.required_skills:
            learned = False
            for tree_id, skills in player.skill_tree_progress.items():
                if skill_id in skills:
                    learned = True
                    break
            if not learned:
                return False
        
        # Check required job
        if fusion_data.required_job:
            if player.job != fusion_data.required_job:
                return False
        
        # Check required god
        if fusion_data.required_god:
            if getattr(player, 'god_id', '') != fusion_data.required_god:
                return False
        
        return True
    
    def perform_fusion(self, player, fusion_id: str) -> bool:
        """
        Perform a skill fusion for the player.
        
        Args:
            player: Player entity
            fusion_id: Fusion ID to perform
            
        Returns:
            True if fusion successful, False otherwise
        """
        fusion_data = self.registry.get(fusion_id)
        if not fusion_data:
            return False
        
        # Check conditions
        if not self.check_fusion_conditions(player, fusion_data):
            return False
        
        # Check if already fused
        if not hasattr(player, 'fused_skills'):
            player.fused_skills = []
        if fusion_id in player.fused_skills:
            return False
        
        # Perform fusion
        if not hasattr(player, 'fused_skills'):
            player.fused_skills = []
        player.fused_skills.append(fusion_id)
        
        # Grant result skills
        for skill_id in fusion_data.result_skills:
            # Add to player's skill tree progress (simplified)
            # In a full implementation, this would add to appropriate skill tree
            pass
        
        # Apply bonus effects
        for effect in fusion_id.bonus_effects:
            self._apply_fusion_effect(player, effect)
        
        return True
    
    def _apply_fusion_effect(self, player, effect) -> None:
        """Apply a fusion bonus effect to the player."""
        # This would apply passive bonuses, could be expanded
        pass
    
    def get_available_fusions(self, player) -> List[FusionData]:
        """Get list of available fusions for player."""
        available = []
        
        for fusion_id, fusion_data in self.registry.all().items():
            if hasattr(player, 'fused_skills') and fusion_id in player.fused_skills:
                continue
            
            if self.check_fusion_conditions(player, fusion_id):
                available.append(fusion_data)
        
        return available


@dataclass
class SkillFusionRecipe:
    """スキル融合レシピデータ (Step 30)"""
    id: str
    name: str = ""
    description: str = ""
    base_skill: str = ""
    materials: Dict[str, int] = field(default_factory=dict)
    output: str = ""
    required_level: int = 1
    success_rate: float = 1.0


# エイリアス
SkillFusionData = FusionData


class SkillFusionRegistry(FusionRegistry):
    """スキル融合レジストリ (Step 31, 32)"""
    def __init__(self):
        super().__init__()
        self._recipes: Dict[str, SkillFusionRecipe] = {}

    def load(self, path: str = "data/skill_fusion.yaml") -> None:
        super().load(path)
        self._recipes.clear()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            for rid, rdata in data.get('fusion_recipes', {}).items():
                self._recipes[rid] = SkillFusionRecipe(
                    id=rid,
                    name=rdata.get('name', rid),
                    description=rdata.get('description', ''),
                    base_skill=rdata.get('base_skill', ''),
                    materials=rdata.get('materials', {}),
                    output=rdata.get('output', ''),
                    required_level=rdata.get('required_level', 1),
                    success_rate=rdata.get('success_rate', 1.0)
                )
        except Exception:
            pass

    def get_recipe(self, recipe_id: str) -> Optional[SkillFusionRecipe]:
        return self._recipes.get(recipe_id)

    def all_recipes(self) -> Dict[str, SkillFusionRecipe]:
        return self._recipes.copy()


class SkillFusionManager(FusionManager):
    """スキル融合マネージャー (Step 33-35)"""
    def can_fuse(self, player, recipe_id: str) -> bool:
        recipe = getattr(self.registry, "_recipes", {}).get(recipe_id)
        if not recipe:
            # 汎用融合チェック
            f_data = self.registry.get(recipe_id)
            return self.check_fusion_conditions(player, f_data) if f_data else False

        if player.level < recipe.required_level:
            return False

        # 素材チェック
        mats = getattr(player, "skill_fusion_materials", {})
        for mat_id, count in recipe.materials.items():
            if mat_id in getattr(player, "skills", {}):
                if player.skills[mat_id].level < count:
                    return False
            elif mats.get(mat_id, 0) < count:
                return False

        return True

    def fuse_skills(self, player, recipe_id: str) -> Tuple[bool, str]:
        recipe = getattr(self.registry, "_recipes", {}).get(recipe_id)
        if not recipe:
            ok = self.perform_fusion(player, recipe_id)
            return ok, "融合完了" if ok else "融合失敗"

        if not self.can_fuse(player, recipe_id):
            return False, "融合条件を満たしていません"

        # 素材消費
        mats = getattr(player, "skill_fusion_materials", {})
        for mat_id, count in recipe.materials.items():
            if mat_id in mats:
                mats[mat_id] -= count

        # 出力スキル獲得
        from entity import Skill
        if not hasattr(player, "skills"):
            player.skills = {}
        player.skills[recipe.output] = Skill(recipe.output, level=1)

        return True, f"スキル【{recipe.name}】が完成しました！"


REGISTRY = SkillFusionRegistry()
_fusion_registry = REGISTRY


def get_fusion_registry(path: str = "data/skill_fusion.yaml") -> SkillFusionRegistry:
    """Get or create the default FusionRegistry instance."""
    global _fusion_registry
    if _fusion_registry is None:
        _fusion_registry = SkillFusionRegistry()
        _fusion_registry.load(path)
    return _fusion_registry


def get_fusion_manager() -> SkillFusionManager:
    """Get a FusionManager with the default registry."""
    registry = get_fusion_registry()
    return SkillFusionManager(registry)


__all__ = [
    "FusionEffect",
    "FusionData",
    "SkillFusionData",
    "FusionRegistry",
    "SkillFusionRegistry",
    "FusionManager",
    "SkillFusionManager",
    "REGISTRY",
]