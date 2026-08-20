#!/usr/bin/env python3
"""Inventory all emote PNGs grouped by style."""
import os
from pathlib import Path

def main():
    emote_root = Path('assets/emote/pixel')
    if not emote_root.exists():
        print(f'Directory not found: {emote_root}')
        return

    total = 0
    for style_dir in sorted(emote_root.iterdir()):
        if not style_dir.is_dir():
            continue
        pngs = sorted(style_dir.glob('*.png'))
        print(f'{style_dir.name}: {len(pngs)} files')
        for png in pngs:
            print(f'  {png.name}')
        total += len(pngs)
    
    print(f'\nTotal: {total} emote PNGs')

if __name__ == '__main__':
    main()