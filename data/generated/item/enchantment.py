from __future__ import annotations

from typing import Any
from pydantic import ConfigDict, Field

from data.schemas._base import DataModel


class EnchantmentDefinition(DataModel):
    model_config = ConfigDict(
        extra="ignore",
    )
    id: str = Field(..., description="Unique enchantment ID")
    name: str = Field(..., description="Enchantment name in Japanese")
    description: str | None = Field(None, description="Flavor or effect explanation")
    type: str = Field(..., description="Enchantment type (stat_bonus, element_damage, resistance, combat_bonus, special)")
    target_stat: str | None = Field(None, description="Target attribute or combat stat")
    element: str | None = Field(None, description="Element type if elemental")
    power_range: list[int] = Field(default_factory=lambda: [1, 5], description="[min_power, max_power]")
    applicable_categories: list[str] = Field(default_factory=list, description="List of item categories")
    min_quality: str = Field("good", description="Minimum item quality required")


class ItemEnchantmentInstance(DataModel):
    """Specific instance of an enchantment attached to an item"""
    id: str
    name: str
    type: str
    power: int
    target_stat: str | None = None
    element: str | None = None

    def format_description(self) -> str:
        """Returns human-readable text like '剛力 [+3]' or '紅蓮 [火炎+5]'"""
        if self.type == "stat_bonus" and self.target_stat:
            stat_names = {
                "strength": "筋力",
                "endurance": "耐久",
                "dexterity": "器用",
                "perception": "感覚",
                "learning": "習得",
                "will": "意志",
                "magic": "魔力",
                "charisma": "魅力",
            }
            s_name = stat_names.get(self.target_stat, self.target_stat)
            return f"{self.name} [{s_name}+{self.power}]"
        elif self.type == "element_damage" and self.element:
            elem_names = {"fire": "火炎", "ice": "氷結", "lightning": "電撃", "poison": "毒"}
            e_name = elem_names.get(self.element, self.element)
            return f"{self.name} [{e_name}追加+{self.power}]"
        elif self.type == "resistance" and self.element:
            elem_names = {"fire": "火炎耐性", "ice": "氷結耐性", "lightning": "電撃耐性", "poison": "毒耐性"}
            e_name = elem_names.get(self.element, self.element)
            return f"{self.name} [{e_name}+{self.power}%]"
        elif self.type == "combat_bonus" and self.target_stat:
            return f"{self.name} [{self.target_stat.upper()}+{self.power}]"
        elif self.type == "special":
            return f"{self.name} [吸収+{self.power}%]"
        return f"{self.name} [+{self.power}]"
