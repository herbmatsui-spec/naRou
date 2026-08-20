from __future__ import annotations

from data.generated.monster.monster import MonsterDefinition
from data.repositories.base import CachedRepository


class MonsterRepository(CachedRepository[MonsterDefinition, str]):
    """モンスター・リポジトリ"""

    def __init__(self, monsters: dict[str, MonsterDefinition]):
        super().__init__(monsters)
        self._by_level: dict[int, list[MonsterDefinition]] = {}
        self._by_faction: dict[str, list[MonsterDefinition]] = {}
        self._by_ai_type: dict[str, list[MonsterDefinition]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for monster in self._data.values():
            if monster.level:
                self._by_level.setdefault(monster.level, []).append(monster)
            if monster.faction:
                self._by_faction.setdefault(monster.faction, []).append(monster)
            if monster.ai_type:
                self._by_ai_type.setdefault(monster.ai_type, []).append(monster)

    def get_by_level(self, level: int) -> list[MonsterDefinition]:
        return self._by_level.get(level, [])

    def get_by_level_range(
        self, min_level: int, max_level: int
    ) -> list[MonsterDefinition]:
        result = []
        for level in range(min_level, max_level + 1):
            result.extend(self._by_level.get(level, []))
        return result

    def get_by_faction(self, faction: str) -> list[MonsterDefinition]:
        return self._by_faction.get(faction, [])

    def get_by_ai_type(self, ai_type: str) -> list[MonsterDefinition]:
        return self._by_ai_type.get(ai_type, [])

    def get_bosses(self) -> list[MonsterDefinition]:
        """ボス級モンスター (レベル50以上)"""
        return self.get_by_level_range(50, 999)

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_level.clear()
        self._by_faction.clear()
        self._by_ai_type.clear()
        self._build_indexes()


__all__ = ["MonsterRepository"]
