"""
ペット融合システム
融合レシピの管理・融合可否判定・融合実行
Steps 59-64
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import yaml
import random
from pathlib import Path

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class PetFusionData:
    """ペット融合レシピデータ (Step 60)"""
    id: str
    name: str
    description: str = ""
    icon: str = "🔬"
    required_pets: List[str] = field(default_factory=list)
    required_bond: List[int] = field(default_factory=list)
    required_level: List[int] = field(default_factory=list)
    required_items: List[str] = field(default_factory=list)
    required_facility: Optional[str] = None
    result_pet: str = ""
    inheritance_rate: float = 0.70
    mutation_chance: float = 0.15
    stat_template: Dict[str, int] = field(default_factory=dict)
    skill_inheritance: List[Dict[str, Any]] = field(default_factory=list)
    possible_mutations: List[Dict[str, Any]] = field(default_factory=list)


class PetFusionRegistry:
    """ペット融合レジストリ (シングルトン) (Steps 61, 62)"""
    _instance: Optional['PetFusionRegistry'] = None
    _recipes: Dict[str, PetFusionData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._recipes = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/pet_fusion.yaml") -> None:
        """YAMLからペット融合定義をロード (Step 62)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            f_list = data.get('pet_fusion', {}).get('fusion_recipes', [])
            for r in f_list:
                fid = r.get('id', '')
                recipe = PetFusionData(
                    id=fid,
                    name=r.get('name', fid),
                    description=r.get('description', ''),
                    icon=r.get('icon', '🔬'),
                    required_pets=r.get('required_pets') or [],
                    required_bond=r.get('required_bond') or [],
                    required_level=r.get('required_level') or [],
                    required_items=r.get('required_items') or [],
                    required_facility=r.get('required_facility'),
                    result_pet=r.get('result_pet', fid),
                    inheritance_rate=float(r.get('inheritance_rate', 0.7)),
                    mutation_chance=float(r.get('mutation_chance', 0.15)),
                    stat_template=r.get('stat_template') or {},
                    skill_inheritance=r.get('skill_inheritance') or [],
                    possible_mutations=r.get('possible_mutations') or []
                )
                self._recipes[fid] = recipe
            self._loaded = True
        except Exception:
            self._loaded = True

    def get(self, fusion_id: str) -> Optional[PetFusionData]:
        """特定融合レシピを取得 (Step 61)"""
        return self._recipes.get(fusion_id)

    def all(self) -> Dict[str, PetFusionData]:
        """すべての融合レシピ辞書を返す (Step 61)"""
        return self._recipes


REGISTRY = PetFusionRegistry()


class PetFusionManager:
    """ペット融合管理マネージャー (Steps 63, 64)"""

    def __init__(self, registry: Optional[PetFusionRegistry] = None):
        self.registry = registry or REGISTRY

    def can_fuse(self, pets: List['Entity'], player: Optional['Entity'] = None) -> Optional[str]:
        """融合可能かチェックし、可能なら結果ペットIDを返す (Step 64)"""
        if len(pets) < 2:
            return None

        pet1, pet2 = pets[0], pets[1]
        p1_type = getattr(pet1, 'pet_type', 'puppy')
        p2_type = getattr(pet2, 'pet_type', 'puppy')
        # 進化後のIDも考慮
        if pet1.pet_ai and pet1.pet_ai.evolution_path:
            p1_type = pet1.pet_ai.evolution_path[-1]
        if pet2.pet_ai and pet2.pet_ai.evolution_path:
            p2_type = pet2.pet_ai.evolution_path[-1]

        p1_bond = pet1.pet_ai.bond if pet1.pet_ai else 0
        p2_bond = pet2.pet_ai.bond if pet2.pet_ai else 0
        p1_level = getattr(pet1, 'level', 1)
        p2_level = getattr(pet2, 'level', 1)

        for fid, recipe in self.registry.all().items():
            req_pets = recipe.required_pets
            if len(req_pets) >= 2:
                match_direct = (p1_type == req_pets[0] and p2_type == req_pets[1])
                match_reverse = (p1_type == req_pets[1] and p2_type == req_pets[0])

                if match_direct or match_reverse:
                    req_b1 = recipe.required_bond[0] if len(recipe.required_bond) > 0 else 0
                    req_b2 = recipe.required_bond[1] if len(recipe.required_bond) > 1 else 0
                    req_l1 = recipe.required_level[0] if len(recipe.required_level) > 0 else 1
                    req_l2 = recipe.required_level[1] if len(recipe.required_level) > 1 else 1

                    if match_direct and p1_bond >= req_b1 and p2_bond >= req_b2 and p1_level >= req_l1 and p2_level >= req_l2:
                        return recipe.result_pet
                    elif match_reverse and p1_bond >= req_b2 and p2_bond >= req_b1 and p1_level >= req_l2 and p2_level >= req_l1:
                        return recipe.result_pet

        return None

    def execute_fusion(self, pets: List['Entity'], player: 'Entity', result_pet_id: str) -> Optional['Entity']:
        """ペット融合を実行 (Step 63)"""
        from entity import Entity, Attributes
        recipe = next((r for r in self.registry.all().values() if r.result_pet == result_pet_id), None)
        if not recipe:
            return None

        # 新ペット生成
        template = recipe.stat_template
        new_pet = Entity(
            x=player.x, y=player.y,
            char="D",
            color=(255, 100, 100),
            name=recipe.name,
            is_pet=True,
            speed=95,
            attributes=Attributes(
                strength=template.get("strength", 15),
                endurance=template.get("constitution", 12),
                dexterity=template.get("agility", 15),
                perception=12,
                learning=template.get("intelligence", 10),
                will=12,
                magic=12,
                charisma=15
            )
        )
        new_pet.max_hp = template.get("hp", 100)
        new_pet.hp = new_pet.max_hp
        new_pet.max_mp = template.get("mp", 30)
        new_pet.mp = new_pet.max_mp
        new_pet.pet_type = recipe.result_pet
        new_pet.pet_ai.bond = 100

        # スキル継承
        for inherit in recipe.skill_inheritance:
            for s in inherit.get("skills", []):
                if random.random() <= inherit.get("rate", 0.7):
                    new_pet.gene_skills.append(s)

        # 融合記録をプレイヤーに追加 (Step 69)
        if hasattr(player, 'pet_fusion_history'):
            player.pet_fusion_history.append({
                "recipe_id": recipe.id,
                "result_pet": recipe.result_pet,
                "parent_pets": [p.name for p in pets]
            })

        return new_pet

    def generate_fusion_quest(self, pet1: 'Entity', pet2: 'Entity', result_pet: 'Entity', player: Optional['Entity'] = None) -> Optional[Dict[str, Any]]:
        """融合後に関連クエストを生成"""
        from pet_quest_analyzer import analyze_active_pet
        if player is None:
            return None
        pet_profile = analyze_active_pet(player)
        if pet_profile is None:
            return None
        # ここで pet_profile に基づいてクエストを生成するロジックを書く
        # 簡易的には、固定のクエストを返す
        return {
            "quest_id": f"fusion_quest_{pet_profile.species}_{result_pet.pet_type}",
            "title": f"{pet_profile.species}の融合の試練",
            "description": f"融合によって生まれた新たな力を{10}体の敵に試せ。",
            "objective_type": "kill",
            "required_count": 10,
            "reward": {
                "gold": 200,
                "exp": 500,
                "item": "fusion_core"
            }
        }

    def apply_quest_completion_reward(self, pet: 'Entity', quest_reward: Dict[str, Any]) -> None:
        """クエスト完了報酬をペットに適用"""
        if pet is None:
            return
        # 経験値をペットに与える（簡易実装）
        if "exp" in quest_reward:
            pet_exp = getattr(pet, 'exp', 0)
            pet.exp = pet_exp + quest_reward["exp"]
        # アイテムをペットのインベントリに与える（簡易実装）
        if "item" in quest_reward:
            # ペットにアイテムを与えるロジック（省略）
            pass
