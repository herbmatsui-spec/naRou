import pytest
from collision_system import SpatialHashCollision

class DummyEntity:
    def __init__(self, x: int, y: int, hp: int = 1):
        self.x = x
        self.y = y
        self.hp = hp
    def __repr__(self):
        return f"DummyEntity({self.x},{self.y},hp={self.hp})"

def test_add_and_query_entities():
    coll = SpatialHashCollision(cell_size=5)
    e1 = DummyEntity(2, 3)
    e2 = DummyEntity(6, 8)
    coll.add_entity(e1)
    coll.add_entity(e2)
    # Same cell as e1 (0,0) because 2//5=0,3//5=0
    pot = coll.get_potential_colliders(1, 1)
    assert e1 in pot
    assert e2 not in pot

def test_move_entity_updates_hash():
    coll = SpatialHashCollision(cell_size=5)
    e = DummyEntity(2, 3)
    coll.add_entity(e)
    # Move to new cell (cell (1,1))
    coll.move_entity(e, 7, 9)
    # Old cell should not contain e
    old_cell = coll.get_potential_colliders(2, 3)
    assert e not in old_cell
    # New cell should contain e
    new_cell = coll.get_potential_colliders(7, 9)
    assert e in new_cell

def test_check_collision_excludes_self_and_dead_entities():
    coll = SpatialHashCollision(cell_size=5)
    e1 = DummyEntity(2, 3)
    e2 = DummyEntity(2, 3)  # Same position, alive
    e_dead = DummyEntity(2, 3, hp=0)  # Dead entity should be ignored
    coll.add_entity(e1)
    coll.add_entity(e2)
    coll.add_entity(e_dead)
    result = coll.check_collision(e1)
    assert e2 in result
    assert e_dead not in result
    assert e1 not in result
