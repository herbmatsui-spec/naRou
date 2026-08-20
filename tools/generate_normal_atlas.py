#!/usr/bin/env python3
"""
Generate normal_atlas.png for 2.5D normal mapped lighting.
Creates normal maps matching the layout in demos/assets/font_atlas.json
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image


def generate_normal_atlas():
    with open("demos/assets/font_atlas.json", encoding="utf-8") as f:
        meta = json.load(f)

    tw = meta["textureSize"]["width"]
    th = meta["textureSize"]["height"]

    # Flat normal: RGB(128, 128, 255) -> (0, 0, 1) vector
    img_data = np.full((th, tw, 4), [128, 128, 255, 255], dtype=np.uint8)

    glyphs = meta.get("glyphs", {})
    for char, frame in glyphs.items():
        x, y, w, h = frame["x"], frame["y"], frame["width"], frame["height"]

        # Create normal patch
        patch = np.full((h, w, 4), [128, 128, 255, 255], dtype=np.uint8)

        if char == "#":
            # Beveled brick normal for wall
            for py in range(h):
                for px in range(w):
                    nx, ny, nz = 0.0, 0.0, 1.0
                    # Bevel borders
                    if px < 3:
                        nx += (3 - px) * 0.25
                    elif px >= w - 3:
                        nx -= (px - (w - 3) + 1) * 0.25
                    if py < 3:
                        ny += (3 - py) * 0.25
                    elif py >= h - 3:
                        ny -= (py - (h - 3) + 1) * 0.25

                    # Normalize
                    length = max(0.001, np.sqrt(nx * nx + ny * ny + nz * nz))
                    nx, ny, nz = nx / length, ny / length, nz / length

                    r = int((nx * 0.5 + 0.5) * 255)
                    g = int((ny * 0.5 + 0.5) * 255)
                    b = int((nz * 0.5 + 0.5) * 255)
                    patch[py, px] = [r, g, b, 255]
        elif char in (".", " "):
            # Subtle cobblestone noise for floor
            for py in range(h):
                for px in range(w):
                    noise_x = np.sin(px * 1.2 + py * 0.8) * 0.15
                    noise_y = np.cos(px * 0.8 + py * 1.2) * 0.15
                    nz = 0.98
                    r = int((noise_x * 0.5 + 0.5) * 255)
                    g = int((noise_y * 0.5 + 0.5) * 255)
                    b = int((nz * 0.5 + 0.5) * 255)
                    patch[py, px] = [r, g, b, 255]
        else:
            # Hemispherical normal for characters/items
            cx, cy = w / 2.0, h / 2.0
            radius = min(cx, cy) - 1.0
            for py in range(h):
                for px in range(w):
                    dx = (px - cx) / radius
                    dy = (py - cy) / radius
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < 1.0:
                        nz = np.sqrt(1.0 - dist_sq)
                        nx = dx
                        ny = dy
                        r = int((nx * 0.5 + 0.5) * 255)
                        g = int((ny * 0.5 + 0.5) * 255)
                        b = int((nz * 0.5 + 0.5) * 255)
                        patch[py, px] = [r, g, b, 255]

        img_data[y : y + h, x : x + w] = patch

    normal_img = Image.fromarray(img_data, "RGBA")
    normal_img.save("demos/assets/normal_atlas.png")
    print("Generated demos/assets/normal_atlas.png successfully")


if __name__ == "__main__":
    generate_normal_atlas()
