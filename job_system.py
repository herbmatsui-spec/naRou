#!/usr/bin/env python3
"""
Job System for naRou
Manages jobs, job changes, stat modifiers, and unlock conditions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class JobEffect:
    """Represents a single job effect."""

    type: str
    value: int | float | str
    target: str | None = None


@dataclass
class JobData:
    """Represents a job definition."""

    id: str
    name: str
    tier: int
    description: str
    description_en: str = ""
    stat_modifiers: dict[str, int] = field(default_factory=dict)
    equipment_restrictions: dict[str, bool] = field(default_factory=dict)
    exclusive_skills: list[str] = field(default_factory=list)
    unlock_conditions: dict[str, Any] = field(default_factory=dict)


class JobRegistry:
    """Singleton registry for loading and accessing jobs."""

    _instance: JobRegistry | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._jobs: dict[str, JobData] = {}
        self._initialized = True

    def load(self, path: str = "data/jobs.yaml") -> None:
        """Load jobs from YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Job file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")
            return

        if not data or "jobs" not in data:
            logger.warning("No jobs key found in YAML")
            return

        self._jobs.clear()
        for job_id, job_data in data["jobs"].items():
            if not isinstance(job_data, dict):
                continue

            job = JobData(
                id=job_id,
                name=job_data.get("name", ""),
                tier=job_data.get("tier", 0),
                description=job_data.get("description", ""),
                description_en=job_data.get("description_en", ""),
                stat_modifiers=job_data.get("stat_modifiers", {}),
                equipment_restrictions=job_data.get("equipment_restrictions", {}),
                exclusive_skills=job_data.get("exclusive_skills", []),
                unlock_conditions=job_data.get("unlock_conditions", {}),
            )
            self._jobs[job_id] = job

        logger.info(f"Loaded {len(self._jobs)} jobs")

    def all(self) -> dict[str, JobData]:
        """Return all loaded jobs."""
        return self._jobs.copy()

    def get(self, job_id: str) -> JobData | None:
        """Get a specific job by ID."""
        return self._jobs.get(job_id)


class JobManager:
    """Manages player job changes and job progression."""

    def __init__(self, registry: JobRegistry):
        self.registry = registry

    def check_unlock_conditions(self, player, job_data: JobData) -> bool:
        """
        Check if player meets all unlock conditions for a job.

        Args:
            player: Player entity
            job_data: JobData to check

        Returns:
            True if all conditions are met, False otherwise
        """
        conditions = job_data.unlock_conditions
        if not conditions:
            return True

        # Level check
        if "level" in conditions and player.level < conditions["level"]:
            return False

        # Skill requirements
        if "skills" in conditions:
            for skill_id, required_level in conditions["skills"].items():
                player_skill_level = 0
                if hasattr(player, "skills") and skill_id in player.skills:
                    player_skill_level = player.skills[skill_id].level
                if player_skill_level < required_level:
                    return False

        # Stat requirements
        if "stats" in conditions:
            for stat, required_value in conditions["stats"].items():
                player_stat = getattr(player.attributes, stat, 0)
                if player_stat < required_value:
                    return False

        # Job requirement (must have previous job)
        if "job" in conditions:
            required_job = conditions["job"]
            if hasattr(player, "mastered_jobs"):
                if required_job not in player.mastered_jobs:
                    return False
            elif hasattr(player, "job"):
                if player.job != required_job:
                    return False
            else:
                return False

        return True

    def change_job(self, player, job_id: str) -> bool:
        """
        Change player's job.

        Args:
            player: Player entity
            job_id: Target job ID

        Returns:
            True if job changed successfully, False otherwise
        """
        job_data = self.registry.get(job_id)
        if not job_data:
            return False

        # Check unlock conditions
        if not self.check_unlock_conditions(player, job_data):
            return False

        # Add current job to previous_jobs
        current_job = getattr(player, "job", "novice")
        if not hasattr(player, "previous_jobs"):
            player.previous_jobs = []
        if current_job not in player.previous_jobs:
            player.previous_jobs.append(current_job)

        # Add to mastered_jobs if not already
        if not hasattr(player, "mastered_jobs"):
            player.mastered_jobs = []
        if current_job not in player.mastered_jobs:
            player.mastered_jobs.append(current_job)

        # Change job
        player.job = job_id
        player.job_level = 1
        player.job_exp = 0

        # Apply job stats (will be recalculated)
        if hasattr(player, "recalculate_stats"):
            player.recalculate_stats()

        return True

    def get_available_jobs(self, player) -> list[JobData]:
        """Get list of available jobs for player."""
        available = []

        for job_id, job_data in self.registry.all().items():
            # Skip if already mastered
            if hasattr(player, "mastered_jobs") and job_id in player.mastered_jobs:
                continue

            # Skip current job
            if getattr(player, "job", "novice") == job_id:
                continue

            # Check unlock conditions
            if self.check_unlock_conditions(player, job_data):
                available.append(job_data)

        return available

    def apply_job_stats(self, player, job_data: JobData) -> None:
        """
        Apply job stat modifiers to player.
        This is typically called from entity.recalculate_stats().
        """
        if not job_data:
            return

        for stat, modifier in job_data.stat_modifiers.items():
            if hasattr(player.attributes, stat):
                current = getattr(player.attributes, stat)
                setattr(player.attributes, stat, current + modifier)


# Module-level registry instance
_job_registry: JobRegistry | None = None


def get_job_registry(path: str = "data/jobs.yaml") -> JobRegistry:
    """Get or create the default JobRegistry instance."""
    global _job_registry
    if _job_registry is None:
        _job_registry = JobRegistry()
        _job_registry.load(path)
    return _job_registry


def get_job_manager() -> JobManager:
    """Get a JobManager with the default registry."""
    registry = get_job_registry()
    return JobManager(registry)


__all__ = [
    "JobData",
    "JobEffect",
    "JobManager",
    "JobRegistry",
]
