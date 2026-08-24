from __future__ import annotations

from typing import Any
from pydantic import ConfigDict, Field

from data.schemas._base import DataModel


class RecipeDefinition(DataModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str = Field(..., description="Unique recipe identifier")
    name: str = Field(..., min_length=1, description="Display name of the recipe")
    result_item_id: str = Field(..., description="Item ID produced by crafting")
    result_count: int = Field(1, ge=1, description="Number of items produced")
    category: str = Field("weapon", description="Recipe category (weapon, armor, potion, etc.)")
    required_materials: dict[str, int] = Field(..., description="Map of item_id/material to required quantity")
    difficulty: int = Field(10, ge=1, description="Crafting difficulty")
    description: str | None = None
