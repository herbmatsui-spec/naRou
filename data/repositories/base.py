from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

T = TypeVar("T")
ID = TypeVar("ID", bound=str)


@dataclass
class QueryFilter:
    """汎用クエリフィルタ"""

    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains
    value: Any


class Repository(Protocol[T, ID]):
    """リポジトリパターンインターフェース"""

    @abstractmethod
    def get(self, id: ID) -> T | None: ...

    @abstractmethod
    def get_all(self) -> list[T]: ...

    @abstractmethod
    def query(self, filters: list[QueryFilter], limit: int = 100, offset: int = 0) -> list[T]: ...

    @abstractmethod
    def count(self, filters: list[QueryFilter]) -> int: ...

    def find_one(self, filters: list[QueryFilter]) -> T | None:
        results = self.query(filters, limit=1)
        return results[0] if results else None

    def exists(self, id: ID) -> bool:
        return self.get(id) is not None


class InMemoryRepository(Generic[T, ID]):
    """インメモリ実装（DataManager用）"""

    def __init__(self, data: dict[ID, T]):
        self._data = data
        self._indexes: dict[str, dict[Any, set]] = {}

    def get(self, id: ID) -> T | None:
        return self._data.get(id)

    def get_all(self) -> list[T]:
        return list(self._data.values())

    def query(self, filters: list[QueryFilter], limit: int = 100, offset: int = 0) -> list[T]:
        results = list(self._data.values())
        for f in filters:
            results = [r for r in results if self._match(getattr(r, f.field, None), f)]
        return results[offset : offset + limit]

    def count(self, filters: list[QueryFilter]) -> int:
        return len(self.query(filters, limit=1000000))

    def _match(self, value: Any, f: QueryFilter) -> bool:
        if value is None:
            return False
        ops = {
            "eq": lambda v: v == f.value,
            "ne": lambda v: v != f.value,
            "gt": lambda v: v > f.value,
            "lt": lambda v: v < f.value,
            "gte": lambda v: v >= f.value,
            "lte": lambda v: v <= f.value,
            "in": lambda v: v in f.value,
            "not_in": lambda v: v not in f.value,
            "contains": lambda v: f.value in str(v),
        }
        return ops.get(f.operator, lambda v: False)(value)

    def invalidate_cache(self) -> None:
        """キャッシュ無効化（サブクラスでオーバーライド）"""


class CachedRepository(InMemoryRepository[T, ID]):
    """LRUキャッシュ付きリポジトリ"""

    def __init__(self, data: dict[ID, T], cache_size: int = 128):
        super().__init__(data)
        self._cache_size = cache_size
        self._cache: dict[ID, T | None] = {}

    def get(self, id: ID) -> T | None:
        if id in self._cache:
            return self._cache[id]
        val = self._data.get(id)
        if len(self._cache) >= self._cache_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[id] = val
        return val

    def invalidate_cache(self) -> None:
        self._cache.clear()


__all__ = [
    "CachedRepository",
    "InMemoryRepository",
    "QueryFilter",
    "Repository",
]
