from __future__ import annotations

from typing import Any

from data.generated.item.enchantment import EnchantmentDefinition
from data.repositories.base import CachedRepository


class EnchantmentRepository(CachedRepository[EnchantmentDefinition, str]):
    """エンチャントリポジトリ"""

    def __init__(self, enchantments: dict[str, EnchantmentDefinition]):
        super().__init__(enchantments)
        self._by_category: dict[str, list[EnchantmentDefinition]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for ench in self._data.values():
            for cat in getattr(ench, "applicable_categories", []) or []:
                self._by_category.setdefault(cat, []).append(ench)

    def get_for_category(self, category: str) -> list[EnchantmentDefinition]:
        """カテゴリに適用可能なエンチャント一覧を取得"""
        return self._by_category.get(category, [])

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_category.clear()
        self._build_indexes()


__all__ = ["EnchantmentRepository"]
