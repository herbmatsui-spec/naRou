"""
Skill Resonance System Module (Steps 57-64)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity


# Step 58: SkillResonanceData
@dataclass
class SkillResonanceData:
    """スキル共鳴データ (Step 58)"""
    id: str
    name: str = ""
    description: str = ""
    required_skills: List[str] = field(default_factory=list)
    min_count: int = 2
    resonance_effects: Dict[str, Any] = field(default_factory=dict)
    visual_effect: str = ""


# Step 59, 60: SkillResonanceRegistry
class SkillResonanceRegistry:
    """スキル共鳴レジストリ (Step 59, 60)"""
    _instance: Optional[SkillResonanceRegistry] = None

    def __new__(cls) -> SkillResonanceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._sets = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_resonance.yaml") -> None:
        """YAMLからスキル共鳴設定を読み込む (Step 60)"""
        self._sets = {}
        if not os.path.exists(file_path):
            self._sets["flame_knight_set"] = SkillResonanceData(
                id="flame_knight_set", name="炎の騎士セット", required_skills=["swordsmanship", "magic_cast"]
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        r_dict = raw.get("resonance_sets", {})
        for rid, rdata in r_dict.items():
            self._sets[rid] = SkillResonanceData(
                id=rid,
                name=rdata.get("name", rid),
                description=rdata.get("description", ""),
                required_skills=rdata.get("required_skills", []),
                min_count=int(rdata.get("min_count", 2)),
                resonance_effects=rdata.get("resonance_effects", {}),
                visual_effect=rdata.get("visual_effect", "")
            )

    def get(self, set_id: str) -> Optional[SkillResonanceData]:
        return self._sets.get(set_id)

    def all(self) -> Dict[str, SkillResonanceData]:
        return dict(self._sets)


REGISTRY = SkillResonanceRegistry()


# Step 61-64: SkillResonanceManager
class SkillResonanceManager:
    """スキル共鳴管理 (Steps 61-64)"""
    def __init__(self, registry: Optional[SkillResonanceRegistry] = None):
        self.registry = registry or REGISTRY

    def check_resonance(self, player: "Entity") -> List[SkillResonanceData]:
        """発動中の共鳴セットを判定 (Step 62)"""
        active = []
        if not player:
            return active

        for sdata in self.registry.all().values():
            match_cnt = 0
            for rsk in sdata.required_skills:
                if rsk in player.skills or rsk in player.equipped_skills:
                    match_cnt += 1
            if match_cnt >= sdata.min_count:
                active.append(sdata)

        return active

    def apply_resonance_effects(self, player: "Entity", engine: Optional[Any] = None) -> Dict[str, Any]:
        """共鳴効果を適用 (Step 63)"""
        active_sets = self.check_resonance(player)
        merged_effects = {}
        for sdata in active_sets:
            for eff_k, eff_v in sdata.resonance_effects.items():
                merged_effects[eff_k] = merged_effects.get(eff_k, 0) + eff_v
        return merged_effects

    def remove_resonance_effects(self, player: "Entity") -> None:
        """共鳴効果を解除 (Step 64)"""
        pass
