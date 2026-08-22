"""ECS query helpers for filtering entities by component membership."""

from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def entities_with(entities: Iterable[T], *component_types: type) -> list[T]:
    """Return entities that have all of the given components registered."""
    return [e for e in entities if all(e.has_component(c) for c in component_types)]
