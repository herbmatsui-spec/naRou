from __future__ import annotations

from data.generated.quest.quest import QuestDefinition
from data.repositories.base import CachedRepository


class QuestRepository(CachedRepository[QuestDefinition, str]):
    """クエスト・リポジトリ"""

    def __init__(self, quests: dict[str, QuestDefinition]):
        super().__init__(quests)
        self._by_type: dict[str, list[QuestDefinition]] = {}
        self._by_level_range: dict[str, list[QuestDefinition]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for quest in self._data.values():
            self._by_type.setdefault(quest.type, []).append(quest)
            if quest.level_range and len(quest.level_range) == 2:
                key = f"{quest.level_range[0]}-{quest.level_range[1]}"
                self._by_level_range.setdefault(key, []).append(quest)

    def get_by_type(self, quest_type: str) -> list[QuestDefinition]:
        return self._by_type.get(quest_type, [])

    def get_available_for_level(self, player_level: int) -> list[QuestDefinition]:
        """プレイヤーレベルで利用可能なクエスト"""
        available = []
        for quest in self._data.values():
            if quest.level_range and len(quest.level_range) == 2:
                if quest.level_range[0] <= player_level <= quest.level_range[1]:
                    available.append(quest)
            else:
                available.append(quest)
        return available

    def get_repeatable(self) -> list[QuestDefinition]:
        return [q for q in self._data.values() if q.repeatable]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_type.clear()
        self._by_level_range.clear()
        self._build_indexes()


__all__ = ["QuestRepository"]
