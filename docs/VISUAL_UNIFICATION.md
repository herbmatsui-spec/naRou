# Visual Unification — Implementation Summary (Proposal 5)

This document tracks the completion of Proposal 5 (Visual Style Unification)
across the demo HTML files, the web game client, and the terminal tcod renderer.

## Single Source of Truth
- `design_tokens.json` — all colors, fonts, spacing, radii, shadows, and
  accessibility variants (color-blind + high-contrast) live here.
- `tools/tokens_to_css.py` — converts the JSON tokens into CSS custom
  properties written to `assets/css/design_tokens.css`.
- `tools/generate_palette.py` — converts the JSON tokens into a 16-color tcod
  `PALETTE_16` written to `core/palette_generated.py`.

## Deliverables
| File | Purpose |
|------|---------|
| `assets/css/design_tokens.css` | CSS variables for web UIs |
| `assets/css/components.css` | Shared component classes + responsive + reduced-motion |
| `assets/css/themes.css` | Dark / light / high-contrast theme support |
| `templates/base.html` | Shared Jinja2 HTML base template |
| `demos/*.html` | All demos now extend `templates/base.html` |
| `web_game_client.html` | Links shared CSS (design tokens, components, themes) |
| `core/palette_generated.py` | Generated terminal palette (from tokens) |
| `core/palette.py` | Exposes `PALETTE_16` alongside `COLORS` |
| `tools/test_palette_parity.py` | Verifies token ↔ CSS ↔ palette consistency |
| `design_tokens.protan.json` / `.deutan.json` / `.tritan.json` | Color-blind variants |
| `design_audit.md` | Step 1 style audit of demo classes |
| `class_mapping.json` | Step 5 Tailwind → token alias mapping |
| `tools/replace_classes.py` | Step 5 applies the class mapping to demos |
| `assets/css/demo.css` | Token-based utilities + custom demo classes (no Tailwind) |

## Completion Checklist
- [x] `design_tokens.json` is the single source for all colors / fonts / spacing
- [x] All demo HTML files are based on the shared template
- [x] `web_game_client.html` uses the shared CSS variables
- [x] Terminal `palette.py` is synced with the web palette
- [x] Color-blind palette variants generated
- [x] Responsive breakpoints, dark/light/high-contrast, reduced-motion supported
- [x] Style audit completed (`design_audit.md`)
- [x] Tailwind utility classes replaced with token aliases (`class_mapping.json`, `tools/replace_classes.py`, `assets/css/demo.css`)
- [x] Palette parity test passes

## How to Regenerate
```bash
python tools/tokens_to_css.py > assets/css/design_tokens.css
python tools/generate_palette.py > core/palette_generated.py
python tools/generate_colorblind_palettes.py
python tools/test_palette_parity.py
```
