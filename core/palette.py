"""
Color palette conversion from design tokens to tcod RGB tuples.
Provides consistent color definitions between web and tcod rendering.
"""

# RGB Color tuple for tcod (values 0-255)
from __future__ import annotations

RGB = tuple[int, int, int]

# Terminal 16-color palette generated from design_tokens.json (Step 11/12).
# Regenerate with: python tools/generate_palette.py > core/palette_generated.py
from core.palette_generated import PALETTE_16  # noqa: F401

# Semantic colors from design_tokens.json
COLORS: dict[str, RGB] = {
    # Danger/Severity
    "danger": (220, 38, 38),  # #dc2626
    "warning": (217, 119, 6),  # #d97706
    "success": (22, 163, 74),  # #16a34a
    "info": (37, 99, 235),  # #2563eb
    # Resources
    "mana": (59, 130, 246),  # #3b82f6
    "stamina": (239, 68, 68),  # #ef4444
    "health": (16, 185, 129),  # #10b981
    "gold": (245, 158, 11),  # #f59e0b
    "experience": (99, 102, 241),  # #6366f1
    # Rarity
    "legendary": (212, 175, 55),  # #d4af37
    "epic": (168, 85, 247),  # #a855f7
    "rare": (59, 130, 246),  # #3b82f6
    "uncommon": (16, 185, 129),  # #10b981
    "common": (107, 114, 128),  # #6b7280
    # Text
    "text_primary": (31, 41, 55),  # #1f2937
    "text_secondary": (107, 114, 128),  # #6b7280
    "text_muted": (156, 163, 175),  # #9ca3af
    "text_inverse": (255, 255, 255),  # #ffffff
    # Background
    "bg_primary": (255, 255, 255),  # #ffffff
    "bg_secondary": (249, 250, 251),  # #f9fafb
    "bg_muted": (243, 244, 246),  # #f3f4f6
    "bg_dark": (17, 24, 39),  # #111827
    # Border
    "border_light": (229, 231, 235),  # #e5e7eb
    "border_medium": (209, 213, 219),  # #d1d5db
    "border_dark": (156, 163, 175),  # #9ca3af
}


def get_color(name: str) -> RGB:
    """
    Get color by name from the palette.

    Args:
        name: Color name (e.g., 'danger', 'health', 'text_primary')

    Returns:
        RGB tuple (r, g, b) with values 0-255

    Raises:
        KeyError: If color name is not found
    """
    if name not in COLORS:
        raise KeyError(f"Color '{name}' not found in palette")
    return COLORS[name]


def get_rgba(name: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    """
    Get color with alpha value.

    Args:
        name: Color name
        alpha: Alpha value (0.0-1.0)

    Returns:
        RGBA tuple (r, g, b, a) with values 0-255
    """
    rgb = get_color(name)
    return (*rgb, int(alpha * 255))


def get_all_colors() -> dict[str, RGB]:
    """Get a copy of all defined colors."""
    return COLORS.copy()


# Convenience exports for common colors
RED = COLORS["danger"]
GREEN = COLORS["success"]
BLUE = COLORS["info"]
YELLOW = COLORS["gold"]
PURPLE = COLORS["mana"]
ORANGE = COLORS["warning"]
WHITE = COLORS["text_inverse"]
BLACK = (0, 0, 0)
GRAY = COLORS["text_secondary"]
