from __future__ import annotations

from typing import Any

from data.generated.item.item import ItemDefinition
from data.repositories.base import CachedRepository


class ItemRepository(CachedRepository[ItemDefinition, str]):
    """アイテムリポジトリ"""

    def __init__(self, items: dict[str, ItemDefinition]):
        super().__init__(items)
        self._by_category: dict[str, list[ItemDefinition]] = {}
        self._by_material: dict[str, list[ItemDefinition]] = {}
        self._by_quality: dict[str, list[ItemDefinition]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for item in self._data.values():
            self._by_category.setdefault(item.category, []).append(item)
            if item.material:
                self._by_material.setdefault(item.material, []).append(item)

    def get_by_category(self, category: str) -> list[ItemDefinition]:
        return self._by_category.get(category, [])

    def get_by_material(self, material: str) -> list[ItemDefinition]:
        return self._by_material.get(material, [])

    def get_weapons(self) -> list[ItemDefinition]:
        return self.get_by_category("weapon")

    def get_armor(self) -> list[ItemDefinition]:
        cats = ["helm", "armor", "shield", "ring"]
        result = []
        for cat in cats:
            result.extend(self.get_by_category(cat))
        return result

    def get_consumables(self) -> list[ItemDefinition]:
        cats = ["potion", "scroll", "food", "spellbook"]
        result = []
        for cat in cats:
            result.extend(self.get_by_category(cat))
        return result

    def query_by_price_range(self, min_value: int, max_value: int) -> list[ItemDefinition]:
        return [item for item in self._data.values() if min_value <= item.base_value <= max_value]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_category.clear()
        self._by_material.clear()
        self._build_indexes()


class RecipeRepository(CachedRepository[Any, str]):
    """クラフトレシピリポジトリ (PR #8 integration: origin/main より移植)"""

    def __init__(self, recipes: dict[str, Any]):
        super().__init__(recipes)
        self._by_category: dict[str, list[Any]] = {}
        self._by_result_item: dict[str, list[Any]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for recipe in self._data.values():
            cat = getattr(recipe, "category", "")
            if cat:
                self._by_category.setdefault(cat, []).append(recipe)
            res_id = getattr(recipe, "result_item_id", "")
            if res_id:
                self._by_result_item.setdefault(res_id, []).append(recipe)

    def get_by_category(self, category: str) -> list[Any]:
        return self._by_category.get(category, [])

    def get_by_result_item(self, result_item_id: str) -> list[Any]:
        return self._by_result_item.get(result_item_id, [])


__all__ = ["ItemRepository", "RecipeRepository"]
