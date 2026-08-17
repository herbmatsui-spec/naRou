"""
Elona Roguelike - Advanced Systems Compatibility Hub
Re-exports modularized classes for backward compatibility.
"""

from __future__ import annotations

# Re-exporting from split modules to maintain 100% backward compatibility
from crafting_system import ResourceNode, Recipe, CRAFTING_RECIPES, try_craft
from debug_system import WishParser, UniqueItemManager, DebugConsole
from save_system import SaveSystem

__all__ = [
    "ResourceNode",
    "Recipe",
    "CRAFTING_RECIPES",
    "try_craft",
    "WishParser",
    "UniqueItemManager",
    "DebugConsole",
    "SaveSystem",
]
