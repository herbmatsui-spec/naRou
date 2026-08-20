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
            cond = ach.condition
            if cond:
                c_type = getattr(cond, "type", None)
                if c_type is None and isinstance(cond, dict):
                    c_type = cond.get("type")
                if c_type:
                    c_val = getattr(c_type, "value", str(c_type))
                    self._by_type.setdefault(c_val, []).append(ach)
            if ach.hidden:
                self._hidden.append(ach)
    
    def get_by_condition_type(self, cond_type: str) -> list[Achievement]:
        return self._by_type.get(cond_type, [])
    
    def get_visible(self) -> list[Achievement]:
        return [a for a in self._data.values() if not a.hidden]
    
    def get_hidden(self) -> list[Achievement]:
        return self._hidden[:]
    
    def get_by_reward_type(self, reward_type: str) -> list[Achievement]:
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
    
    def __init__(self, titles: dict[str, Title]):
        super().__init__(titles)
        self._by_category: dict[str, list[Title]] = {}
        self._hidden: list[Title] = []
        self._build_indexes()
    
    def _build_indexes(self):
        for title in self._data.values():
            cat = getattr(title.category, "value", str(title.category)) if title.category else ""
            if cat:
                self._by_category.setdefault(cat, []).append(title)
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