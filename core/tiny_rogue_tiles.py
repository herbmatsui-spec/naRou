"""
Tiny Rogue tile mapping utilities.
Provides functions to map standard tile IDs to Tiny Rogue tile IDs.
"""
from __future__ import annotations
from typing import Dict, Optional
import yaml
from pathlib import Path


_MAPPINGS_CACHE: Optional[Dict] = None


def load_tiny_rogue_mappings() -> Dict:
    """Load tile mappings from YAML file."""
    global _MAPPINGS_CACHE
    if _MAPPINGS_CACHE is not None:
        return _MAPPINGS_CACHE
    
    path = Path("data/tile_mappings/tiny_rogue_dungeon.yaml")
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _MAPPINGS_CACHE = yaml.safe_load(f)
    else:
        _MAPPINGS_CACHE = {}
    return _MAPPINGS_CACHE


def get_tiny_rogue_tile_id(standard_tile_id: str, fallback: str = None) -> str:
    """
    Get the Tiny Rogue tile ID for a standard tile ID.
    
    Args:
        standard_tile_id: The standard tile ID (e.g., "TILE_FLOOR")
        fallback: Fallback tile ID if mapping not found
        
    Returns:
        Tiny Rogue tile ID or fallback/standard ID
    """
    try:
        from feature_flags import is_enabled
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return standard_tile_id
    except ImportError:
        pass
    
    mappings = load_tiny_rogue_mappings()
    standard_map = mappings.get("standard_to_tiny_rogue", {})
    return standard_map.get(standard_tile_id, fallback or standard_tile_id)


def get_item_tile_id(item_category: str) -> str:
    """Get Tiny Rogue tile ID for an item category."""
    try:
        from feature_flags import is_enabled
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return "TR_ITEM_12"
    except ImportError:
        pass
    
    mappings = load_tiny_rogue_mappings()
    item_map = mappings.get("items", {})
    return item_map.get(item_category, item_map.get("default", "TR_ITEM_12"))


def get_decoration_tile_id(decor_type: str) -> str:
    """Get Tiny Rogue tile ID for a decoration type."""
    try:
        from feature_flags import is_enabled
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return decor_type
    except ImportError:
        pass
    
    mappings = load_tiny_rogue_mappings()
    decor_map = mappings.get("decorations", {})
    return decor_map.get(decor_type, decor_type)


def get_effect_tile_id(effect_type: str) -> str:
    """Get Tiny Rogue tile ID for an effect type."""
    try:
        from feature_flags import is_enabled
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return effect_type
    except ImportError:
        pass
    
    mappings = load_tiny_rogue_mappings()
    effect_map = mappings.get("effects", {})
    return effect_map.get(effect_type, effect_type)


def get_ui_tile_id(ui_type: str) -> str:
    """Get Tiny Rogue tile ID for a UI element."""
    try:
        from feature_flags import is_enabled
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return ui_type
    except ImportError:
        pass
    
    mappings = load_tiny_rogue_mappings()
    ui_map = mappings.get("ui", {})
    return ui_map.get(ui_type, ui_type)


def get_terrain_config() -> Dict:
    """Get terrain autotile configuration."""
    mappings = load_tiny_rogue_mappings()
    return mappings.get("terrain", {})


# Convenience function for dungeon generation
def get_dungeon_tile_id(tile_type: str) -> str:
    """
    Get the appropriate tile ID for dungeon generation.
    Uses Tiny Rogue tiles when feature flag is enabled.
    
    Args:
        tile_type: One of "floor", "wall", "stairs_up", "stairs_down", 
                   "water", "trap", "wall_variant"
    """
    mapping = {
        "floor": "TILE_FLOOR",
        "wall": "TILE_WALL",
        "stairs_up": "TILE_STAIRS_UP",
        "stairs_down": "TILE_STAIRS_DOWN",
        "water": "TILE_WATER",
        "trap": "TILE_TRAP",
        "wall_variant": "TILE_WALL_VAR",
    }
    standard_id = mapping.get(tile_type, tile_type)
    return get_tiny_rogue_tile_id(standard_id)