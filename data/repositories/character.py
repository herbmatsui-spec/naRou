from __future__ import annotations

from data.generated.character.gods import God
from data.generated.character.jobs import Job
from data.generated.dungeon.dungeon import DungeonThemeDefinition
from data.generated.social.guilds import Guild
from data.repositories.base import CachedRepository


class JobRepository(CachedRepository[Job, str]):
    """職業・リポジトリ"""

    def __init__(self, jobs: dict[str, Job]):
        super().__init__(jobs)
        self._by_tier: dict[int, list[Job]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for job in self._data.values():
            self._by_tier.setdefault(job.tier, []).append(job)

    def get_by_tier(self, tier: int) -> list[Job]:
        return self._by_tier.get(tier, [])

    def get_unlocked_for(
        self,
        player_level: int,
        player_skills: dict[str, int],
        player_stats: dict[str, int],
        current_job: str,
    ) -> list[Job]:
        """プレイヤーが転職可能な職業一覧"""
        available = []
        for job in self._data.values():
            if job.id == current_job:
                continue
            cond = job.unlock_conditions
            if cond.level and player_level < cond.level:
                continue
            if cond.skills:
                skill_ok = all(
                    player_skills.get(s, 0) >= req for s, req in cond.skills.items()
                )
                if not skill_ok:
                    continue
            if cond.stats:
                stat_ok = all(
                    player_stats.get(s, 0) >= req for s, req in cond.stats.items()
                )
                if not stat_ok:
                    continue
            available.append(job)
        return available

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_tier.clear()
        self._build_indexes()


class GodRepository(CachedRepository[God, str]):
    """神・リポジトリ"""

    def __init__(self, gods: dict[str, God]):
        super().__init__(gods)
        self._by_domain: dict[str, list[God]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for god in self._data.values():
            for domain in god.domain.split("・"):
                self._by_domain.setdefault(domain.strip(), []).append(god)

    def get_by_domain(self, domain: str) -> list[God]:
        return self._by_domain.get(domain, [])

    def get_by_favored_offer(self, offer_type: str) -> list[God]:
        return [g for g in self._data.values() if offer_type in g.favored_offer]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_domain.clear()
        self._build_indexes()


class DungeonThemeRepository(CachedRepository[DungeonThemeDefinition, str]):
    """ダンジョンテーマ・リポジトリ"""

    def __init__(self, themes: dict[str, DungeonThemeDefinition]):
        super().__init__(themes)
        self._by_level_range: dict[str, list[DungeonThemeDefinition]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for theme in self._data.values():
            key = f"{theme.min_level}-{theme.max_level}"
            self._by_level_range.setdefault(key, []).append(theme)

    def get_for_level(self, level: int) -> list[DungeonThemeDefinition]:
        """指定レベルで利用可能なテーマ"""
        return [t for t in self._data.values() if t.min_level <= level <= t.max_level]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_level_range.clear()
        self._build_indexes()


class GuildRepository(CachedRepository[Guild, str]):
    """ギルド・リポジトリ"""

    def __init__(self, guilds: dict[str, Guild]):
        super().__init__(guilds)
        self._by_location: dict[str, list[Guild]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for guild in self._data.values():
            self._by_location.setdefault(guild.hall_location, []).append(guild)

    def get_by_location(self, location: str) -> list[Guild]:
        return self._by_location.get(location, [])

    def get_available_for_rank(self, current_rank: str) -> list[Guild]:
        """現在のランクで昇格可能なギルド"""
        rank_order = ["novice", "member", "veteran", "officer", "leader"]
        try:
            current_idx = rank_order.index(current_rank)
        except ValueError:
            return []
        available = []
        for guild in self._data.values():
            ranks = list(guild.rank_requirements.keys())
            if current_idx + 1 < len(ranks):
                next_rank = ranks[current_idx + 1]
                if next_rank in guild.rank_requirements:
                    available.append(guild)
        return available

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_location.clear()
        self._build_indexes()


__all__ = [
    "DungeonThemeRepository",
    "GodRepository",
    "GuildRepository",
    "JobRepository",
]
