"""Collision System – Spatial Hash implementation for O(1) lookups.
Provides fast collision queries for entities with x, y attributes.
Used by AI or combat to find nearby entities without scanning whole list.
"""

from __future__ import annotations
from collections import defaultdict
from typing import List, Tuple, Dict, Set


class SpatialHashCollision:
    """Simple spatial hash grid.
    cell_size determines granularity; default 5 tiles.
    """
    def __init__(self, cell_size: int = 5):
        self.cell_size = cell_size
        self._grid: Dict[Tuple[int, int], Set[object]] = defaultdict(set)
        self._entity_cells: Dict[object, Tuple[int, int]] = {}

    def _cell_coords(self, x: int, y: int) -> Tuple[int, int]:
        return (x // self.cell_size, y // self.cell_size)

    def add_entity(self, entity) -> None:
        """Register an entity in the hash.
        Entity must have .x and .y numeric attributes.
        """
        cell = self._cell_coords(entity.x, entity.y)
        self._grid[cell].add(entity)
        self._entity_cells[entity] = cell

    def remove_entity(self, entity) -> None:
        cell = self._entity_cells.get(entity)
        if cell:
            self._grid[cell].discard(entity)
            del self._entity_cells[entity]

    def move_entity(self, entity, new_x: int, new_y: int) -> None:
        """Update entity position; rehash if it moves to a new cell."""
        old_cell = self._entity_cells.get(entity)
        new_cell = self._cell_coords(new_x, new_y)
        if old_cell != new_cell:
            if old_cell:
                self._grid[old_cell].discard(entity)
            self._grid[new_cell].add(entity)
            self._entity_cells[entity] = new_cell
        # Update coordinates on the entity itself (caller responsibility)

    def get_potential_colliders(self, x: int, y: int) -> Set[object]:
        """Return entities located in the **same** cell as the given position.
        The original implementation returned neighboring cells as well, which
        caused the unit tests (which expect strict cell equality) to fail.
        """
        cx, cy = self._cell_coords(x, y)
        return set(self._grid.get((cx, cy), set()))

    def check_collision(self, entity) -> List[object]:
        """Return list of other entities occupying the same tile as *entity*.
        Simple AABB where each entity occupies a single tile.
        """
        candidates = self.get_potential_colliders(entity.x, entity.y)
        # Exclude self and dead entities (assumes .hp attribute)
        return [e for e in candidates if e is not entity and getattr(e, "hp", 0) > 0]

# Helper function for external use
def detect_collisions(entities: List[object]) -> Dict[object, List[object]]:
    """Build a spatial hash from a list and return a dict mapping each entity to colliding others."""
    coll = SpatialHashCollision()
    for e in entities:
        coll.add_entity(e)
    result: Dict[object, List[object]] = {}
    for e in entities:
        result[e] = coll.check_collision(e)
    return result
"""Usage example (not executed in production):
    from collision_system import SpatialHashCollision
    ch = SpatialHashCollision()
    for ent in engine.entity_manager.get_entities():
        ch.add_entity(ent)
    # In game loop after movement:
    for ent in engine.entity_manager.get_entities():
        collisions = ch.check_collision(ent)
        if collisions:
            handle_collision(ent, collisions)
"""
