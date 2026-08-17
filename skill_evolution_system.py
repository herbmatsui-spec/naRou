"""
Skill Evolution System Module (Steps 36-42)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


# Step 37: SkillEvolutionData
@dataclass
class SkillEvolutionData:
    """スキル進化チェーンデータ (Step 37)"""
    id: str
    name: str = ""
    description: str = ""
    stages: List[Dict[str, Any]] = field(default_factory=list)


# Step 38, 39: SkillEvolutionRegistry
class SkillEvolutionRegistry:
    """スキル進化レジストリ (Step 38, 39)"""
    _instance: Optional[SkillEvolutionRegistry] = None

    def __new__(cls) -> SkillEvolutionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._chains = {}
        return cls._instance

    def load(self, file_path: str = "data/skill_evolution.yaml") -> None:
        """YAMLからスキル進化チェーンを読み込む (Step 39)"""
        self._chains = {}
        if not os.path.exists(file_path):
            self._chains["sword_mastery"] = SkillEvolutionData(
                id="sword_mastery", name="剣術の進化の道", stages=[{"id": "sword_stage_1", "name": "剣術の心得"}]
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        c_dict = raw.get("evolution_chains", {})
        for cid, cdata in c_dict.items():
            self._chains[cid] = SkillEvolutionData(
                id=cid,
                name=cdata.get("name", cid),
                description=cdata.get("description", ""),
                stages=cdata.get("stages", [])
            )

    def get(self, chain_id: str) -> Optional[SkillEvolutionData]:
        return self._chains.get(chain_id)

    def all(self) -> Dict[str, SkillEvolutionData]:
        return dict(self._chains)


REGISTRY = SkillEvolutionRegistry()


# Step 40-42: SkillEvolutionManager
class SkillEvolutionManager:
    """スキル進化管理 (Steps 40-42)"""
    def __init__(self, registry: Optional[SkillEvolutionRegistry] = None):
        self.registry = registry or REGISTRY

    def check_evolution(self, player: "Entity", chain_id: str) -> Optional[Dict[str, Any]]:
        """進化可能な次のステージを取得 (Step 41)"""
        chain = self.registry.get(chain_id)
        if not chain or not player:
            return None

        cur_stage_id = player.skill_evolution.get(chain_id)
        # 次のステージを探索
        stages = chain.stages
        next_stage = None
        if not cur_stage_id:
            next_stage = stages[0] if stages else None
        else:
            for idx, st in enumerate(stages):
                if st.get("id") == cur_stage_id and idx + 1 < len(stages):
                    next_stage = stages[idx + 1]
                    break

        if not next_stage:
            return None

        # 条件チェック
        cond = next_stage.get("unlock_condition", {})
        req_p_lvl = cond.get("player_level", 1)
        if player.level < req_p_lvl:
            return None

        req_sk = cond.get("skill_level", {})
        for sk_name, req_slvl in req_sk.items():
            if sk_name not in player.skills or player.skills[sk_name].level < req_slvl:
                return None

        return next_stage

    def evolve_skill(self, player: "Entity", chain_id: str, engine: Optional[Any] = None) -> bool:
        """スキルを進化させる (Step 42)"""
        next_stage = self.check_evolution(player, chain_id)
        if not next_stage:
            return False

        stage_id = next_stage["id"]
        player.skill_evolution[chain_id] = stage_id

        # ステータス/特性ボーナス適用
        bonuses = next_stage.get("bonuses", {})
        for b_name, b_val in bonuses.items():
            if hasattr(player.attributes, b_name):
                setattr(player.attributes, b_name, getattr(player.attributes, b_name) + int(b_val))

        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"★スキルが進化！ 【{next_stage.get('name', stage_id)}】に覚醒・深化！", (255, 215, 0))

        return True
