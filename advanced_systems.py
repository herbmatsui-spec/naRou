"""
Elona Roguelike - Advanced Systems Compatibility Hub
Re-exports modularized classes for backward compatibility.
"""

from __future__ import annotations

# Re-exporting from split modules to maintain 100% backward compatibility
from crafting_system import CRAFTING_RECIPES, Recipe, ResourceNode, try_craft
from debug_system import DebugConsole, UniqueItemManager, WishParser
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
