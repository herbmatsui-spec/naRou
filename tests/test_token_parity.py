"""
Verify visual token parity across platforms (Plan 1-B acceptance):
the tcod palette (core/palette.py) and the generated web theme must derive from
the same design_tokens.json values.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _load_tokens():
    with open(os.path.join(ROOT, "design_tokens.json")) as f:
        return json.load(f)


# palette key -> dotted path into design_tokens.color.semantic
PARITY_MAP = {
    "danger": "danger",
    "warning": "warning",
    "success": "success",
    "info": "info",
    "mana": "mana",
    "stamina": "stamina",
    "health": "health",
    "gold": "gold",
    "experience": "experience",
    "legendary": "legendary",
    "epic": "epic",
    "rare": "rare",
    "uncommon": "uncommon",
    "common": "common",
    "text_primary": "text.primary",
    "text_secondary": "text.secondary",
    "text_muted": "text.muted",
    "text_inverse": "text.inverse",
    "bg_primary": "background.primary",
    "bg_secondary": "background.secondary",
    "bg_muted": "background.muted",
    "bg_dark": "background.dark",
    "border_light": "border.light",
    "border_medium": "border.medium",
    "border_dark": "border.dark",
}


def _resolve(d, dotted):
    cur = d
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def test_palette_matches_design_tokens():
    sys.path.insert(0, ROOT)
    from core.palette import COLORS

    tokens = _load_tokens()["color"]["semantic"]
    for palette_key, dotted in PARITY_MAP.items():
        expected = _hex_to_rgb(_resolve(tokens, dotted))
        assert palette_key in COLORS, f"palette missing {palette_key}"
        assert COLORS[palette_key] == expected, (
            f"{palette_key}: palette={COLORS[palette_key]} token={expected}"
        )


def test_theme_css_derives_from_tokens():
    """theme.css must contain the design tokens and the theme variant hooks."""
    theme_path = os.path.join(ROOT, "web", "theme.css")
    assert os.path.exists(theme_path), (
        "web/theme.css missing (run tools/generate_theme.py)"
    )
    css = open(theme_path).read()
    # A representative token and all variant hooks must be present.
    assert "--color-danger: #dc2626;" in css
    for variant in ("light", "high-contrast", "colorblind", "sepia"):
        assert f'[data-theme="{variant}"]' in css


def test_tileset_def_has_atlas():
    """Every tile defined in the tileset def must exist in the generated atlas."""

    src = os.path.join(ROOT, "assets", "source", "tilesets")
    if not os.path.isdir(src):
        src = os.path.join(ROOT, "assets", "src", "tilesets")
    def_files = (
        [f for f in os.listdir(src) if f.endswith(".json")]
        if os.path.isdir(src)
        else []
    )
    assert def_files, "no tileset definition found"
    for df in def_files:
        with open(os.path.join(src, df)) as f:
            definition = json.load(f)
        size = definition.get("tile_size", 16)
        atlas_json = os.path.join(
            ROOT, "assets", "tiles", f"tileset_{size}x{size}.json"
        )
        assert os.path.exists(atlas_json), f"missing atlas {atlas_json}"
        with open(atlas_json) as f:
            atlas = json.load(f)
        for name in definition["tiles"]:
            assert name in atlas["tiles"], f"tile '{name}' missing from atlas"
