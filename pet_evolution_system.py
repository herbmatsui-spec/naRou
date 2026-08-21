"""
ペット進化システム
進化データの管理・利用可能進化一覧・進化適用
Steps 37-43
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity, PetAI


@dataclass
class PetEvolutionData:
    """ペット進化データ (Step 38)"""

    id: str
    name: str
    requirements: dict[str, Any] = field(default_factory=dict)
    stat_changes: dict[str, int] = field(default_factory=dict)
    skill_changes: dict[str, list[str]] = field(default_factory=dict)
    evolution_bonus: dict[str, Any] = field(default_factory=dict)


class PetEvolutionRegistry:
    """ペット進化レジストリ (シングルトン) (Steps 39, 40)"""

    _instance: PetEvolutionRegistry | None = None
    _evolutions: dict[
        str, list[PetEvolutionData]
    ] = {}  # pet_type -> [PetEvolutionData]
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._evolutions = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/pet_evolutions.yaml") -> None:
        """YAMLからペット進化定義をロード (Step 40)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            evolutions_data = data.get("pet_evolutions", {})
            for pet_type, p_dict in evolutions_data.items():
                evo_list = []
                for e in p_dict.get("evolutions", []):
                    evo = PetEvolutionData(
                        id=e.get("id", ""),
                        name=e.get("name", ""),
                        requirements=e.get("requirements") or {},
                        stat_changes=e.get("stat_changes") or {},
                        skill_changes=e.get("skill_changes") or {},
                        evolution_bonus=e.get("evolution_bonus") or {},
                    )
                    evo_list.append(evo)
                self._evolutions[pet_type] = evo_list
            self._loaded = True
        except Exception as e:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            self._loaded = True

    def get(self, pet_type: str) -> list[PetEvolutionData]:
        """ペット種別ごとの進化リストを取得 (Step 39)"""
        return self._evolutions.get(pet_type, [])

    def all(self) -> dict[str, list[PetEvolutionData]]:
        """すべてのペット進化辞書を返す (Step 39)"""
        return self._evolutions


REGISTRY = PetEvolutionRegistry()


class PetEvolutionManager:
    """ペット進化管理マネージャー (Steps 41-43)"""

    def __init__(self, registry: PetEvolutionRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_available_evolutions(
        self, pet_type: str, pet: PetAI, pet_entity: Entity | None = None
    ) -> list[PetEvolutionData]:
        """利用可能な進化オプション一覧を取得 (Step 42)"""
        evos = self.registry.get(pet_type)
        if not evos:
            return []

        from pet_contract_system import REGISTRY as CONTRACT_REG
        from pet_contract_system import PetContractManager

        CONTRACT_REG.load()
        PetContractManager(CONTRACT_REG)

        available = []
        cur_path = getattr(pet, "evolution_path", [])
        cur_bond = getattr(pet, "bond", 0)
        pet_level = getattr(pet_entity, "level", 1) if pet_entity else 1

        for evo in evos:
            if evo.id in cur_path:
                continue
            req = evo.requirements
            req_bond = req.get("bond", 0)
            req_level = req.get("level", 1)

            if cur_bond >= req_bond and pet_level >= req_level or cur_bond >= req_bond:
                available.append(evo)

        return available

    def apply_evolution(
        self,
        pet: PetAI,
        evolution_data: PetEvolutionData,
        pet_entity: Entity | None = None,
    ) -> bool:
        """進化を適用 (Step 43)"""
        # 1. 統計変更の適用
        if pet_entity and hasattr(pet_entity, "attributes"):
            stats = evolution_data.stat_changes
            for attr_name, boost in stats.items():
                if attr_name == "hp":
                    pet_entity.max_hp += boost
                    pet_entity.hp = min(pet_entity.max_hp, pet_entity.hp + boost)
                elif attr_name == "mp":
                    pet_entity.max_mp += boost
                    pet_entity.mp = min(pet_entity.max_mp, pet_entity.mp + boost)
                elif hasattr(pet_entity.attributes, attr_name):
                    setattr(
                        pet_entity.attributes,
                        attr_name,
                        getattr(pet_entity.attributes, attr_name) + boost,
                    )

        # 2. スキル変更の適用
        if pet_entity:
            adds = evolution_data.skill_changes.get("add", [])
            removes = evolution_data.skill_changes.get("remove", [])
            if hasattr(pet_entity, "gene_skills"):
                for a in adds:
                    if a not in pet_entity.gene_skills:
                        pet_entity.gene_skills.append(a)
                for r in removes:
                    if r in pet_entity.gene_skills:
                        pet_entity.gene_skills.remove(r)

        # 3. 進化パス・ステージ更新
        if not hasattr(pet, "evolution_path") or pet.evolution_path is None:
            pet.evolution_path = []
        pet.evolution_path.append(evolution_data.id)
        pet.evolution_stage = getattr(pet, "evolution_stage", 0) + 1

        if pet_entity:
            pet_entity.name = f"{evolution_data.name}（進化形態）"

        return True

    def generate_evolution_quest(
        self,
        pet: PetAI,
        evolution_data: PetEvolutionData,
        pet_entity: Entity | None = None,
    ) -> dict[str, Any] | None:
        """進化後に関連クエストを生成"""
        # 簡易実装：進化後のペットに基づいてクエストを生成
        # 実際には、pet_quest_analyzer と pet_quests.yaml を使用する
        from pet_quest_analyzer import analyze_active_pet

        if pet_entity is None:
            return None
        pet_profile = analyze_active_pet(pet_entity)
        if pet_profile is None:
            return None
        # ここで pet_profile に基づいてクエストを生成するロジックを書く
        # 簡易的には、固定のクエストを返す
        return {
            "quest_id": f"evolution_quest_{pet_profile.species}_{evolution_data.id}",
            "title": f"{pet_profile.species}の進化試練",
            "description": f"{pet_profile.species}としてさらに強くなるため、{evolution_data.name}の力を試せ。",
            "objective_type": "kill",
            "required_count": 5,
            "reward": {"gold": 100, "exp": 200, "item": "evolution_stone"},
        }

    def apply_quest_completion_reward(
        self, pet: PetAI, quest_reward: dict[str, Any], pet_entity: Entity | None = None
    ) -> None:
        """クエスト完了報酬をペットに適用"""
        if pet_entity is None:
            return
        # 経験値をペットに与える（簡易実装）
        if "exp" in quest_reward:
            pet_exp = getattr(pet, "exp", 0)
            pet.exp = pet_exp + quest_reward["exp"]
        # アイテムをペットのインベントリに与える（簡易実装）
        if "item" in quest_reward:
            # ペットにアイテムを与えるロジック（省略）
            pass

        return True
