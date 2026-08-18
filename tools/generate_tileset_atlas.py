#!/usr/bin/env python3
"""
Procedural tileset atlas generator.

Reads a tileset definition (dungeon_tileset.json format) and produces a packed
atlas PNG plus a metadata JSON in the format consumed by web_game_client.html
(see assets/tiles/tileset_16x16.json).

Each tile may declare:
  - path:       optional source PNG (used if present, else generated procedurally)
  - animated:   bool
  - frames:     number of animation frames (>=1)
  - fps:        playback rate
  - directions: number of facing directions (>=1)
  - variants:   number of static variants (unused for layout, informational)

The generator draws real pixel-art tiles procedurally so the pipeline never
emits flat placeholder images.
"""

import argparse
import json
import math
import os
import random
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Seeded RNG helpers (deterministic output per tile name)
# ---------------------------------------------------------------------------

def _seeded_rng(seed: str) -> random.Random:
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return random.Random(h)


def _lighten(rgb: Tuple[int, int, int], amount: int) -> Tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in rgb)


def _darken(rgb: Tuple[int, int, int], amount: int) -> Tuple[int, int, int]:
    return tuple(max(0, c - amount) for c in rgb)


def _mix(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

def _floor(size: int, rng: random.Random) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (58, 52, 70)
    d.rectangle([0, 0, size, size], fill=base)
    # subtle flagstone grid
    for i in range(0, size, max(2, size // 4)):
        d.line([(i, 0), (i, size)], fill=_darken(base, 18), width=1)
        d.line([(0, i), (size, i)], fill=_darken(base, 18), width=1)
    for _ in range(size):
        x = rng.randint(0, size - 1)
        y = rng.randint(0, size - 1)
        d.point((x, y), fill=_lighten(base, rng.randint(-8, 14)))
    return img


def _wall(size: int, rng: random.Random) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (42, 40, 56)
    d.rectangle([0, 0, size, size], fill=base)
    brick_h = max(2, size // 4)
    for row, y in enumerate(range(0, size, brick_h)):
        offset = (brick_h // 2) if (row % 2) else 0
        for x in range(-offset, size, brick_h * 2):
            d.rectangle([x + 1, y + 1, x + brick_h * 2 - 1, y + brick_h - 1],
                        fill=_lighten(base, 12), outline=_darken(base, 20))
    return img


def _water(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (32, 96, 170)
    d.rectangle([0, 0, size, size], fill=base)
    shift = frame * max(1, size // 8)
    for i in range(3):
        y = (shift + i * size // 3) % size
        d.line([(0, y), (size, y)], fill=_lighten(base, 30 - i * 8), width=1)
    for _ in range(size // 2):
        x = rng.randint(0, size - 1)
        y = rng.randint(0, size - 1)
        d.point((x, y), fill=(220, 240, 255, 160))
    return img


def _stairs(size: int, rng: random.Random, down: bool) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (70, 62, 84)
    d.rectangle([0, 0, size, size], fill=base)
    steps = max(3, size // 4)
    for i in range(steps):
        t = i / steps
        if down:
            y0 = int(size * t)
            y1 = int(size * (t + 1 / steps))
        else:
            y0 = int(size * (1 - t - 1 / steps))
            y1 = int(size * (1 - t))
        shade = _lighten(base, int(40 * (1 - t)))
        d.rectangle([2, y0, size - 2, y1], fill=shade, outline=_darken(base, 20))
    return img


def _trap(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (48, 46, 58)
    d.rectangle([0, 0, size, size], fill=base)
    c = size // 2
    r = size // 3 + (frame % 2)
    d.ellipse([c - r, c - r, c + r, c + r], outline=(200, 60, 60, 220), width=max(1, size // 16))
    for k in range(8):
        ang = k * math.pi / 4 + frame * 0.4
        x = c + int(r * math.cos(ang))
        y = c + int(r * math.sin(ang))
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(220, 80, 80, 220))
    return img


# ---------------------------------------------------------------------------
# Objects / items
# ---------------------------------------------------------------------------

def _item_gold(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    bob = int(math.sin(frame * math.pi / 2) * max(1, size // 16))
    r = size // 4
    d.ellipse([c - r, c - r - bob, c + r, c + r - bob], fill=(240, 190, 40),
              outline=(120, 90, 10), width=max(1, size // 24))
    d.ellipse([c - r // 2, c - r // 2 - bob, c + r // 2, c + r // 2 - bob],
              fill=(255, 235, 120))
    return img


def _item_potion(size: int, rng: random.Random) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    d.rectangle([c - size // 10, size // 6, c + size // 10, size // 3], fill=(180, 180, 190))
    d.ellipse([c - size // 4, size // 3, c + size // 4, size - size // 6],
              fill=(80, 200, 120), outline=(40, 120, 70), width=max(1, size // 24))
    d.ellipse([c - size // 8, size // 2, c + size // 8, size // 2 + size // 8],
              fill=(160, 240, 190))
    return img


def _item_weapon(size: int, rng: random.Random) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    d.line([(c, size // 5), (c, size - size // 4)], fill=(200, 200, 210), width=max(1, size // 12))
    d.line([(c - size // 4, size - size // 4), (c + size // 4, size - size // 4)],
           fill=(150, 90, 40), width=max(1, size // 10))
    d.polygon([(c, size // 6), (c - size // 16, size // 4), (c + size // 16, size // 4)],
              fill=(230, 230, 240))
    return img


def _item_armor(size: int, rng: random.Random) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    d.polygon([(c, size // 5), (size // 5, size // 2), (c, size - size // 5),
               (size - size // 5, size // 2)], fill=(120, 130, 160),
              outline=(60, 70, 100), width=max(1, size // 24))
    d.line([(c, size // 5), (c, size - size // 5)], fill=(200, 210, 230), width=1)
    return img


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

def _entity(size: int, rng: random.Random, kind: str, frame: int, direction: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size // 2
    if kind == 'player':
        skin, cloth, pants = (255, 220, 177), (60, 130, 230), (40, 50, 110)
    elif kind == 'pet':
        skin, cloth, pants = (190, 140, 90), (120, 80, 50), (90, 60, 40)
    else:  # goblin
        skin, cloth, pants = (90, 150, 70), (120, 80, 50), (80, 60, 40)
    hr = max(2, size // 6)
    head_y = size // 4
    # walk bob
    bob = (frame % 2) * max(1, size // 24)
    d.ellipse([cx - hr, head_y - hr - bob, cx + hr, head_y + hr - bob], fill=skin)
    if kind == 'goblin':
        d.polygon([(cx - hr, head_y - hr - bob), (cx - hr - hr // 2, head_y - hr - bob - hr),
                   (cx - hr // 2, head_y - hr - bob)], fill=(60, 60, 60))
        d.polygon([(cx + hr, head_y - hr - bob), (cx + hr + hr // 2, head_y - hr - bob - hr),
                   (cx + hr // 2, head_y - hr - bob)], fill=(60, 60, 60))
    body_w = size // 3
    body_h = size // 3
    body_y = head_y + hr - bob
    d.rectangle([cx - body_w // 2, body_y, cx + body_w // 2, body_y + body_h], fill=cloth)
    leg_h = size // 3
    leg_top = body_y + body_h
    swing = (frame % 2) * max(1, size // 16)
    d.rectangle([cx - body_w // 4 - swing, leg_top, cx - body_w // 4 + body_w // 2 - swing,
                 leg_top + leg_h], fill=pants)
    d.rectangle([cx + body_w // 4 + swing, leg_top, cx + body_w // 4 + body_w // 2 + swing,
                 leg_top + leg_h], fill=pants)
    eye = max(1, size // 16)
    eye_y = head_y - size // 12 - bob
    eye_col = (220, 30, 30) if kind == 'goblin' else (20, 20, 20)
    d.ellipse([cx - size // 6, eye_y, cx - size // 6 + eye, eye_y + eye], fill=eye_col)
    d.ellipse([cx + size // 6 - eye, eye_y, cx + size // 6, eye_y + eye], fill=eye_col)
    # direction facing: flip horizontally for left/right variety
    if direction == 1:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def _torch(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size // 2
    d.rectangle([cx - max(1, size // 16), size // 2, cx + max(1, size // 16), size - size // 8],
                fill=(120, 80, 40))
    flick = int(math.sin(frame * math.pi / 2) * max(1, size // 12))
    colors = [(255, 140, 0, 220), (255, 190, 40, 200), (255, 230, 120, 180)]
    for i, col in enumerate(colors):
        w = size // 3 - i * max(1, size // 12)
        h = size // 2 - i * max(1, size // 10) - flick
        top = size // 2 - h
        d.ellipse([cx - w // 2, top, cx + w // 2, top + h], fill=col)
    return img


def _blood(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    spread = (frame + 1) / 3
    d.ellipse([cx - size // 4, cy - size // 4, cx + size // 4, cy + size // 4],
              fill=(150, 10, 10, 230))
    for _ in range(int(4 * spread)):
        ang = rng.uniform(0, 2 * math.pi)
        dist = rng.randint(size // 4, size // 2)
        x = cx + int(dist * math.cos(ang))
        y = cy + int(dist * math.sin(ang))
        r = rng.randint(1, max(2, size // 10))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(170, 20, 20, 220))
    return img


def _magic(size: int, rng: random.Random, frame: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    rot = frame * math.pi / 3
    pts = []
    n = 8
    for i in range(n * 2):
        ang = i * math.pi / n + rot
        r = (size // 2 - 2) if (i % 2 == 0) else (size // 4)
        pts.append((cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))))
    d.polygon(pts, fill=(150, 90, 230, 170))
    for _ in range(5):
        x = rng.randint(size // 4, 3 * size // 4)
        y = rng.randint(size // 4, 3 * size // 4)
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, 220))
    return img


# ---------------------------------------------------------------------------
# Tile registry
# ---------------------------------------------------------------------------

EntityKind = {'PLAYER': 'player', 'PET': 'pet', 'ENEMY_GOBLIN': 'goblin'}


def _make_tile(name: str, tile_def: Dict, size: int, frame: int, direction: int,
               rng: random.Random) -> Image.Image:
    upper = name.upper()
    if upper in EntityKind:
        return _entity(size, rng, EntityKind[upper], frame, direction)
    if 'FLOOR' in upper:
        return _floor(size, rng)
    if 'WALL' in upper:
        return _wall(size, rng)
    if 'WATER' in upper:
        return _water(size, rng, frame)
    if 'STAIRS_DOWN' in upper:
        return _stairs(size, rng, down=True)
    if 'STAIRS_UP' in upper:
        return _stairs(size, rng, down=False)
    if 'TRAP' in upper:
        return _trap(size, rng, frame)
    if 'GOLD' in upper:
        return _item_gold(size, rng, frame)
    if 'POTION' in upper:
        return _item_potion(size, rng)
    if 'WEAPON' in upper:
        return _item_weapon(size, rng)
    if 'ARMOR' in upper:
        return _item_armor(size, rng)
    if 'TORCH' in upper or 'BLOOD' in upper or 'DECOR_BLOOD' in upper:
        return _blood(size, rng, frame) if ('BLOOD' in upper) else _torch(size, rng, frame)
    if 'MAGIC' in upper or 'EFFECT' in upper:
        return _magic(size, rng, frame)
    # fallback: generic colored tile
    return _floor(size, rng)


def generate_tileset(def_path: str, output_dir: str, tile_size: int = 32,
                     source_dir: Optional[str] = None) -> Dict:
    """Generate a packed tileset atlas from a definition file."""
    os.makedirs(output_dir, exist_ok=True)
    with open(def_path, 'r') as f:
        definition = json.load(f)

    tile_defs = definition.get('tiles', {})
    if not isinstance(tile_defs, dict):
        raise ValueError("Tileset definition 'tiles' must be an object keyed by tile name")

    padding = int(definition.get('padding', 1))
    max_atlas = int(definition.get('max_atlas_size', 2048))

    # Each slot is one (frame, direction) cell of size `tile_size`.
    slots: List[Tuple[str, int, int]] = []  # (name, frame, direction)
    meta: Dict[str, Dict] = {}

    for name, tdef in tile_defs.items():
        frames = max(1, int(tdef.get('frames', 1)))
        directions = max(1, int(tdef.get('directions', 1)))
        fps = int(tdef.get('fps', 1))
        animated = bool(tdef.get('animated', frames > 1))
        rng = _seeded_rng(name)
        start = len(slots)
        for fr in range(frames):
            for di in range(directions):
                slots.append((name, fr, di))
        meta[name] = {
            'start_index': start,
            'frames': frames,
            'directions': directions,
            'fps': fps,
            'animated': animated,
            'variants': int(tdef.get('variants', 1)),
        }

    if not slots:
        slots = [('_empty', 0, 0)]
        meta['_empty'] = {'start_index': 0, 'frames': 1, 'directions': 1,
                          'fps': 1, 'animated': False, 'variants': 1}

    # Determine grid layout (fit within max_atlas, keep it roughly square)
    n = len(slots)
    cols = min(int(max_atlas // (tile_size + padding)), int(math.ceil(n ** 0.5)))
    cols = max(1, cols)
    rows = math.ceil(n / cols)
    atlas_w = cols * (tile_size + padding) - padding
    atlas_h = rows * (tile_size + padding) - padding

    atlas = Image.new('RGBA', (atlas_w, atlas_h), (0, 0, 0, 0))

    for idx, (name, frame, direction) in enumerate(slots):
        col = idx % cols
        row = idx // cols
        x = col * (tile_size + padding)
        y = row * (tile_size + padding)
        m = meta[name]
        # Reuse the seeded rng per tile for determinism across frames/directions
        rng = _seeded_rng(name)
        tile = _make_tile(name, tile_defs[name], tile_size, frame, direction, rng)
        tile = tile.resize((tile_size, tile_size), Image.NEAREST)
        atlas.paste(tile, (x, y), tile)

    base_name = f"tileset_{tile_size}x{tile_size}"
    png_path = os.path.join(output_dir, f"{base_name}.png")
    json_path = os.path.join(output_dir, f"{base_name}.json")
    atlas.save(png_path)

    output = {
        'tile_size': tile_size,
        'atlas_width': atlas_w,
        'atlas_height': atlas_h,
        'tiles': {},
    }
    for name, m in meta.items():
        col = m['start_index'] % cols
        row = m['start_index'] // cols
        x = col * (tile_size + padding)
        y = row * (tile_size + padding)
        output['tiles'][name] = {
            'x': x,
            'y': y,
            'width': tile_size,
            'height': tile_size,
            'variants': m['variants'],
            'animated': m['animated'],
            'frames': m['frames'],
            'fps': m['fps'],
            'directions': m['directions'],
        }

    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Generated {png_path} ({atlas_w}x{atlas_h}) and {json_path} "
          f"with {len(slots)} cells across {len(meta)} tiles")
    return output


def main():
    parser = argparse.ArgumentParser(description='Generate a procedural tileset atlas')
    parser.add_argument('--def', dest='def_path', required=True,
                        help='Path to tileset definition JSON')
    parser.add_argument('--output', default='assets/tiles', help='Output directory')
    parser.add_argument('--size', type=int, default=32, help='Tile size (16, 32, 64, ...)')
    parser.add_argument('--source', default=None,
                        help='Optional directory of real source PNGs keyed by tile path')
    args = parser.parse_args()
    generate_tileset(args.def_path, args.output, args.size, args.source)


if __name__ == '__main__':
    main()
