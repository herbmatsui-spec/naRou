#!/usr/bin/env python3
"""
Generate web/theme.css from design_tokens.json.

Emits:
  1. Design-system custom properties under :root (single source of truth).
  2. Brand UI variables (the variables the game client actually consumes) as
     the default (dark) theme.
  3. Theme variant overrides for [data-theme="dark" | "light" | "high-contrast"
     | "colorblind" | "sepia"], switchable at runtime by setting
     document.documentElement.dataset.theme.

Run as part of the asset pipeline / a build step so theme.css is always derived
from design_tokens.json.
"""

import json
from pathlib import Path


def load_design_tokens(filepath: str = "design_tokens.json") -> dict:
    with open(filepath) as f:
        return json.load(f)


def generate_token_variables(tokens: dict) -> str:
    """Emit design-system custom properties from tokens."""
    lines = []
    c = tokens.get("color", {})
    if "semantic" in c:
        for name, value in c["semantic"].items():
            if isinstance(value, dict):
                for sub, subv in value.items():
                    lines.append(f"  --color-{name}-{sub}: {subv};")
            else:
                lines.append(f"  --color-{name}: {value};")
    if "system" in c:
        for name, value in c["system"].items():
            lines.append(f"  --color-{name}: {value};")
    for group in ("spacing", "radius"):
        for name, value in tokens.get(group, {}).items():
            lines.append(f"  --{group}-{name}: {value};")
    typ = tokens.get("typography", {})
    for name, value in typ.get("fontFamily", {}).items():
        lines.append(f"  --font-{name}: {value};")
    for name, value in typ.get("fontSize", {}).items():
        lines.append(f"  --font-size-{name}: {value};")
    for name, value in typ.get("fontWeight", {}).items():
        lines.append(f"  --font-weight-{name}: {value};")
    for name, value in typ.get("lineHeight", {}).items():
        lines.append(f"  --line-height-{name}: {value};")
    for name, value in tokens.get("shadow", {}).items():
        lines.append(f"  --shadow-{name}: {value};")
    for name, value in tokens.get("zIndex", {}).items():
        lines.append(f"  --zindex-{name}: {value};")
    anim = tokens.get("animation", {})
    for name, value in anim.get("duration", {}).items():
        lines.append(f"  --animation-duration-{name}: {value};")
    for name, value in anim.get("easing", {}).items():
        lines.append(f"  --animation-easing-{name}: {value};")
    return "\n".join(lines)


# Brand UI variables consumed directly by web_game_client.html, expressed as the
# default (dark) theme. Each theme variant below overrides a subset of these.
BRAND_DARK = {
    "--bg-dark": "#0a0b10",
    "--bg-gradient": "radial-gradient(circle at 50% 20%, #151b2e 0%, #080a10 100%)",
    "--panel-bg": "rgba(18, 22, 36, 0.75)",
    "--panel-border": "rgba(99, 130, 210, 0.25)",
    "--panel-border-glow": "rgba(99, 130, 210, 0.5)",
    "--primary-accent": "#e5a93b",
    "--hp-color": "#2ecc71",
    "--mp-color": "#3498db",
    "--sp-color": "#f39c12",
    "--text-main": "#f0f4fc",
    "--text-muted": "#8b9bb4",
    "--font-main": "'Noto Sans JP', 'Outfit', sans-serif",
    "--font-title": "'Cinzel', serif",
}

# Light theme: bright surfaces, dark text.
BRAND_LIGHT = {
    "--bg-dark": "#eef1f7",
    "--bg-gradient": "radial-gradient(circle at 50% 20%, #ffffff 0%, #dde3ee 100%)",
    "--panel-bg": "rgba(255, 255, 255, 0.85)",
    "--panel-border": "rgba(40, 60, 110, 0.25)",
    "--panel-border-glow": "rgba(40, 60, 110, 0.5)",
    "--primary-accent": "#b9791e",
    "--hp-color": "#1f9e54",
    "--mp-color": "#2274c4",
    "--sp-color": "#c87a07",
    "--text-main": "#1b2233",
    "--text-muted": "#5a6b85",
}

# High contrast: pure black/white with vivid yellow accents and hard borders.
BRAND_HIGH_CONTRAST = {
    "--bg-dark": "#000000",
    "--bg-gradient": "#000000",
    "--panel-bg": "#000000",
    "--panel-border": "#ffffff",
    "--panel-border-glow": "#ffff00",
    "--primary-accent": "#ffff00",
    "--hp-color": "#00ff00",
    "--mp-color": "#00bfff",
    "--sp-color": "#ffae00",
    "--text-main": "#ffffff",
    "--text-muted": "#cccccc",
}

# Colorblind-safe (protan/deutan/tritan friendly): blue/orange/white palette,
# avoiding red-green confusion.
BRAND_COLORBLIND = {
    "--bg-dark": "#0c0f1a",
    "--bg-gradient": "radial-gradient(circle at 50% 20%, #16233b 0%, #070a12 100%)",
    "--panel-bg": "rgba(20, 30, 52, 0.8)",
    "--panel-border": "rgba(120, 170, 255, 0.4)",
    "--panel-border-glow": "rgba(120, 170, 255, 0.8)",
    "--primary-accent": "#ffb000",
    "--hp-color": "#0072ff",  # blue instead of green/red
    "--mp-color": "#ff8c00",  # orange
    "--sp-color": "#e0e0e0",  # white/grey
    "--text-main": "#f2f6ff",
    "--text-muted": "#9fb4d6",
}

# Sepia: warm, low-blue reading theme.
BRAND_SEPIA = {
    "--bg-dark": "#e9dcc3",
    "--bg-gradient": "radial-gradient(circle at 50% 20%, #f3e9d2 0%, #d8c4a0 100%)",
    "--panel-bg": "rgba(245, 233, 210, 0.85)",
    "--panel-border": "rgba(120, 90, 50, 0.3)",
    "--panel-border-glow": "rgba(120, 90, 50, 0.6)",
    "--primary-accent": "#9c6b1f",
    "--hp-color": "#3f7d3f",
    "--mp-color": "#2f6d9c",
    "--sp-color": "#a9711a",
    "--text-main": "#3b2f1d",
    "--text-muted": "#7a6849",
}

# data-theme selector -> brand variable overrides. "dark" is the :root default
# and is therefore omitted from the variant list below.
THEME_VARIANTS = {
    "light": BRAND_LIGHT,
    "high-contrast": BRAND_HIGH_CONTRAST,
    "colorblind": BRAND_COLORBLIND,
    "sepia": BRAND_SEPIA,
}


def render_block(selector: str, vars_dict: dict) -> str:
    body = "\n".join(f"  {k}: {v};" for k, v in vars_dict.items())
    return f"{selector} {{\n{body}\n}}"


def _brand_body(vars_dict: dict) -> str:
    return "\n".join(f"  {k}: {v};" for k, v in vars_dict.items())


def generate_css(tokens: dict) -> str:
    parts = [
        "/* AUTO-GENERATED from design_tokens.json by tools/generate_theme.py.",
        "   Do not edit by hand; edit design_tokens.json and re-run. */",
        ":root {",
        generate_token_variables(tokens),
        _brand_body(BRAND_DARK),
        "}",
    ]
    for name, vars_dict in THEME_VARIANTS.items():
        parts.append("")
        parts.append(render_block(f'[data-theme="{name}"]', vars_dict))
    return "\n".join(parts)


def main():
    try:
        tokens = load_design_tokens()
        css = generate_css(tokens)
        Path("web").mkdir(exist_ok=True)
        with open("web/theme.css", "w") as f:
            f.write(css + "\n")
        print(
            f"Generated web/theme.css from design_tokens.json "
            f"({len(THEME_VARIANTS) + 1} theme variants)"
        )
        return True
    except Exception as e:
        print(f"Error generating theme.css: {e}")
        return False


if __name__ == "__main__":
    main()
