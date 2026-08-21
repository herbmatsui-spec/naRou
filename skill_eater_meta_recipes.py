"""Meta-Knowledge Shortcut and Hidden Recipe System for Skill Eater World.

Handles junk item combinations, secret explosive recipes, and meta shortcuts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class JunkItem:
    """A scavenged piece of slum garbage used in meta crafting."""

    item_id: str
    name: str
    category: str  # 'CHEMICAL', 'MINERAL', 'METALLIC', 'ORGANIC'
    description: str


class MetaRecipeCraftingEngine:
    """Combines junk materials using isekai meta knowledge to create overpowered items."""

    def __init__(self) -> None:
        self.known_recipes: Dict[frozenset[str], Dict[str, Any]] = {}
        self.meta_score: int = 0
        self.register_default_recipes()

    def award_meta_points(self, points: int) -> int:
        self.meta_score += points
        return self.meta_score

    def register_default_recipes(self) -> None:
        # C4 equivalent magic bomb
        self.known_recipes[frozenset(["SLIME_MUCUS", "FLINT_STONE", "SULFUR_POWDER"])] = {
            "result_id": "ITEM_C4_MAGIC_BOMB",
            "name": "即席C4魔力爆弾",
            "power": 350,
            "effect": "AOE_EXPLOSION_DEFENSE_PIERCE",
            "meta_bonus": 150,
        }
    def craft_with_meta_knowledge(self, item_ids: List[str]) -> Dict[str, Any]:
        """Synthesizes items using isekai chemistry knowledge."""
        key = frozenset(item_ids)
        if key in self.known_recipes:
            recipe = self.known_recipes[key]
            return {
                "success": True,
                "item_id": recipe["result_id"],
                "name": recipe["name"],
                "power": recipe["power"],
                "effect": recipe["effect"],
                "meta_bonus": recipe["meta_bonus"],
                "message": f"【メタ調合成功！】現代知識の応用で【{recipe['name']}】を生成！",
            }
        # Penalty / explosion on invalid mix
    def negotiate_with_meta_secrets(self, npc_id: str, choice_id: str) -> Dict[str, Any]:
        """Negotiates discounts with black market brokers using meta insider knowledge."""
        if choice_id == "CHOICE_EXPOSE_SLUM_EXPLOITATION":
            return {
                "success": True,
                "discount_percent": 40,
                "reaction": "『ヒッ…！な、なぜ新入りのあんたが上層部との裏帳簿ルートを知ってるんだ…！？安くする、安くするから黙っててくれ！』",
            }
    def get_meta_item_fx(self, item_id: str) -> Dict[str, Any]:
        """Provides dynamic sound and animation configurations for meta crafted items."""
        if item_id == "ITEM_C4_MAGIC_BOMB":
            return {
                "sound": "se_heavy_explosion_c4.ogg",
                "screen_shake": "SHAKE_EXTREME",
                "particles": "FIERY_DEBRIS_SMOKE",
            }
    def get_slum_foraging_nodes(self) -> List[Dict[str, Any]]:
        """Provides resource foraging spawn points in Slum alleys."""
        return [
            {"node_id": "NODE_SLIME_PIPE", "pos": (1, 3), "yield_item": "SLIME_MUCUS", "label": "魔導下水パイプの滲み"},
            {"node_id": "NODE_RUBBLE_FLINT", "pos": (4, 1), "yield_item": "FLINT_STONE", "label": "崩れた魔導外壁の残骸"},
            {"node_id": "NODE_CHEMICAL_DUMP", "pos": (8, 4), "yield_item": "SULFUR_POWDER", "label": "不法投棄された化学薬品樽"},
        ]
