from __future__ import annotations

from data.generated.faction.factions import Faction
from data.repositories.base import CachedRepository


class FactionRepository(CachedRepository[Faction, str]):
    """派閥・リポジトリ"""

    def __init__(self, factions: dict[str, Faction]):
        super().__init__(factions)
        self._by_territory: dict[str, list[Faction]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for faction in self._data.values():
            for territory in faction.territories:
                self._by_territory.setdefault(territory, []).append(faction)

    def get_by_territory(self, territory: str) -> list[Faction]:
        return self._by_territory.get(territory, [])

    def get_allies(self, faction_id: str) -> list[Faction]:
        faction = self.get(faction_id)
        if not faction:
            return []
        return [self.get(aid) for aid in faction.allied_factions if self.get(aid)]

    def get_rivals(self, faction_id: str) -> list[Faction]:
        faction = self.get(faction_id)
        if not faction:
            return []
        return [self.get(rid) for rid in faction.rival_factions if self.get(rid)]

    def get_by_influence_range(self, min_inf: int, max_inf: int) -> list[Faction]:
        return [f for f in self._data.values() if min_inf <= f.influence <= max_inf]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_territory.clear()
        self._build_indexes()


__all__ = ["FactionRepository"]
