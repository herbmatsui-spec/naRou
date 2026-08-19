from __future__ import annotations

from data.generated.meta.achievements import Achievement
from data.generated.meta.titles import Title
from data.repositories.base import CachedRepository


class AchievementRepository(CachedRepository[Achievement, str]):
    """実績・リポジトリ"""
    
    def __init__(self, achievements: dict[str, AchievementDefinition]):
        super().__init__(achievements)
        self._by_type: dict[str, list[AchievementDefinition]] = {}
        self._hidden: list[AchievementDefinition] = []
        self._build_indexes()
    
    def _build_indexes(self):
        for ach in self._data.values():
            if ach.condition and ach.condition.type:
                self._by_type.setdefault(ach.condition.type, []).append(ach)
            if ach.hidden:
                self._hidden.append(ach)
    
    def get_by_condition_type(self, cond_type: str) -> list[AchievementDefinition]:
        return self._by_type.get(cond_type, [])
    
    def get_visible(self) -> list[AchievementDefinition]:
        return [a for a in self._data.values() if not a.hidden]
    
    def get_hidden(self) -> list[AchievementDefinition]:
        return self._hidden[:]
    
    def get_by_reward_type(self, reward_type: str) -> list[AchievementDefinition]:
        result = []
        for ach in self._data.values():
            if reward_type == "title" and ach.reward_title or reward_type == "gold" and ach.reward_gold or reward_type == "item" and ach.reward_item or reward_type == "skill_point" and ach.reward_skill_points:
                result.append(ach)
        return result
    
    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_type.clear()
        self._hidden.clear()
        self._build_indexes()


class TitleRepository(CachedRepository[Title, str]):
    """称号・リポジトリ"""
    
    def __init__(self, titles: dict[str, TitleDefinition]):
        super().__init__(titles)
        self._by_category: dict[str, list[TitleDefinition]] = {}
        self._hidden: list[TitleDefinition] = []
        self._build_indexes()
    
    def _build_indexes(self):
        for title in self._data.values():
            self._by_category.setdefault(title.category, []).append(title)
            if title.is_hidden:
                self._hidden.append(title)
    
    def get_by_category(self, category: str) -> list[TitleDefinition]:
        return self._by_category.get(category, [])
    
    def get_visible(self) -> list[TitleDefinition]:
        return [t for t in self._data.values() if not t.is_hidden]
    
    def get_hidden(self) -> list[TitleDefinition]:
        return self._hidden[:]
    
    def get_by_condition_type(self, cond_type: str) -> list[TitleDefinition]:
        result = []
        for title in self._data.values():
            if title.condition and title.condition.type == cond_type:
                result.append(title)
        return result
    
    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_category.clear()
        self._hidden.clear()
        self._build_indexes()


__all__ = ["AchievementRepository", "TitleRepository"]