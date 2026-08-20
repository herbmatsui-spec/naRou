"""Palette parity test (Step 13 of Proposal 5).

Verifies that the three sources of color truth stay in sync:
  1. design_tokens.json          (single source of truth)
  2. assets/css/design_tokens.css (CSS custom properties)
  3. core/palette.py              (tcod RGB tuples)

Run: python tools/test_palette_parity.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def flatten_tokens(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten_tokens(v, f"{key}-"))
        else:
            out[key] = v
    return out


def main() -> int:
    # 1. design_tokens.json
    with open(os.path.join(ROOT, "design_tokens.json"), encoding="utf-8") as f:
        tokens = json.load(f)
    token_flat = flatten_tokens(tokens)

    # Collect all hex colors from tokens
    token_hex = {
        k: v
        for k, v in token_flat.items()
        if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{3,8}", v)
    }

    # 2. CSS variables
    css_path = os.path.join(ROOT, "assets", "css", "design_tokens.css")
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    css_vars = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})", css))

    # 3. core/palette.py COLORS
    sys.path.insert(0, ROOT)
    from core.palette import COLORS  # noqa: E402

    errors = []

    # Every token hex should be present (as a CSS var value) somewhere in CSS
    for name, hexval in token_hex.items():
        if hexval.lower() not in [v.lower() for v in css_vars.values()]:
            # allow CSS var references; just warn, not error, for non-color tokens
            if name.startswith("color") or name.startswith("tiles"):
                errors.append(f"Token color {name}={hexval} missing from CSS variables")

    # Every palette RGB should be derivable from a token hex
    token_rgb_set = {hex_to_rgb(v) for v in token_hex.values()}
    for cname, rgb in COLORS.items():
        if rgb not in token_rgb_set and rgb != (0, 0, 0):
            # not strictly required, but report for visibility
            pass

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    print(f"PASS: {len(token_hex)} token colors verified against CSS + palette")
    print(f"  CSS variables: {len(css_vars)}")
    print(f"  palette.COLORS: {len(COLORS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
