import pytest
from render_system import RenderSystem
from types import SimpleNamespace

class DummyContext:
    def __init__(self, inventory_tab, inventory, pet_inventory=None, inventory_target="player"):
        self.inventory_tab = inventory_tab
        self.inventory = inventory
        self.pet_inventory = pet_inventory if pet_inventory else inventory
        self.inventory_target = inventory_target

class DummyItem:
    def __init__(self, category):
        self.category = category

def test_get_tabbed_items_filters_by_category():
    # Prepare items
    items = [DummyItem('weapon'), DummyItem('shield'), DummyItem('armor'), DummyItem('potion'), DummyItem('food'), DummyItem('other')]
    ctx = DummyContext(inventory_tab=1, inventory=SimpleNamespace(items=items))
    result = RenderSystem.get_tabbed_items(ctx)
    assert all(i.category in ('weapon',) for i in result)

    ctx.inventory_tab = 2
    result = RenderSystem.get_tabbed_items(ctx)
    assert all(i.category in ('shield', 'armor') for i in result)

    ctx.inventory_tab = 3
    result = RenderSystem.get_tabbed_items(ctx)
    assert all(i.category in ('potion', 'food') for i in result)

    ctx.inventory_tab = 4
    result = RenderSystem.get_tabbed_items(ctx)
    assert all(i.category not in ('weapon', 'shield', 'armor', 'potion', 'food') for i in result)
