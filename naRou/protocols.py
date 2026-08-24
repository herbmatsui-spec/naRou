"""
Protocols and interfaces for naRou subsystems.
Provides decoupling and avoids circular imports.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NPCMemoryManagerProtocol(Protocol):
    npc: Any

    def record_reputation_event(
        self,
        subject_id: str,
        event_type: str,
        delta: int,
        source: str = "faction_system",
        importance: Any = None,
    ) -> None: ...


@runtime_checkable
class MemoryRegistryProtocol(Protocol):
    def all_managers(self) -> dict[str, NPCMemoryManagerProtocol]: ...
