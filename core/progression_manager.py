"""Progression system for tracking unlocked game systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProgressionFlagComponent:
    """システムアンロックフラグを管理するコンポーネント"""
    skill_eater: bool = False
    base_defense: bool = False
    archaeology: bool = False
    crafting: bool = False
    arena: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "skill_eater": self.skill_eater,
            "base_defense": self.base_defense,
            "archaeology": self.archaeology,
            "crafting": self.crafting,
            "arena": self.arena,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProgressionFlagComponent":
        return cls(
            skill_eater=data.get("skill_eater", False),
            base_defense=data.get("base_defense", False),
            archaeology=data.get("archaeology", False),
            crafting=data.get("crafting", False),
            arena=data.get("arena", False),
        )


def is_unlocked(flags: ProgressionFlagComponent, system: str) -> bool:
    """Check if a given system is unlocked."""
    return getattr(flags, system, False)


def unlock_system(flags: ProgressionFlagComponent, system: str) -> None:
    """Unlock a system."""
    if hasattr(flags, system):
        setattr(flags, system, True)
