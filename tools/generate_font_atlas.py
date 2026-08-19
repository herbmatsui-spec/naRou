#!/usr/bin/env python3
"""
Font atlas generator for rendering text with bitmap fonts.
Generates font atlases with character metrics and UV coordinates.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


def generate_font_atlas(
    font_path: str,
    output_dir: str,
    font_size: int = 16,
    chars: str = None,
    padding: int = 2
) -> Dict:
    """Generate a font atlas from a TrueType font."""
    os.makedirs(output_dir, exist_ok=True)
    
    if chars is None:
        chars = ''.join(chr(i) for i in range(32, 127))  # ASCII printable
    
    font = ImageFont.truetype(font_path, font_size)
    
    char_images = {}
    max_width = 0
    max_height = 0
    
    for char in chars:
        try:
            bbox = font.getbbox(char)
            if bbox[2] > 0 and bbox[3] > 0:
                img = Image.new('RGBA', (bbox[2], bbox[3]), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.text((0, 0), char, font=font, fill=(255, 255, 255, 255))
                char_images[char] = img
                max_width = max(max_width, bbox[2])
                max_height = max(max_height, bbox[3])
            else:
                char_images[char] = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        except Exception:
            char_images[char] = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    
    cols = int(len(chars) ** 0.5) + 1
    rows = (len(chars) + cols - 1) // cols
    
    cell_width = max_width + padding
    cell_height = max_height + padding
    
    atlas_width = cols * cell_width
    atlas_height = rows * cell_height
    
    atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
    metrics = {}
    
    for idx, char in enumerate(chars):
        row = idx // cols
        col = idx % cols
        x = col * cell_width
        y = row * cell_height
        
        char_img = char_images[char]
        atlas.paste(char_img, (x + padding // 2, y + padding // 2))
        
        u = x / atlas_width
        v = y / atlas_height
        uw = cell_width / atlas_width
        vh = cell_height / atlas_height
        
        bbox = font.getbbox(char)
        advance = font.getlength(char) if hasattr(font, 'getlength') else cell_width
        
        metrics[char] = {
            'x': x,
            'y': y,
            'width': char_img.width,
            'height': char_img.height,
            'u': u,
            'v': v,
            'uw': uw,
            'vh': vh,
            'advance': advance,
            'bearing_x': bbox[0] if bbox else 0,
            'bearing_y': bbox[1] if bbox else 0
        }
    
    font_name = Path(font_path).stem
    base_name = f"font_{font_name}_{font_size}"
    
    png_path = os.path.join(output_dir, f"{base_name}.png")
    json_path = os.path.join(output_dir, f"{base_name}.json")
    
    atlas.save(png_path)
    
    output_data = {
        'font_path': font_path,
        'font_size': font_size,
        'atlas_width': atlas_width,
        'atlas_height': atlas_height,
        'cell_width': cell_width,
        'cell_height': cell_height,
        'padding': padding,
        'chars': chars,
        'metrics': metrics
    }
    
    with open(json_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Generated {png_path} and {json_path}")
    return output_data


def main():
    parser = argparse.ArgumentParser(description='Generate font atlas')
    parser.add_argument('--font', required=True, help='Path to TTF font file')
    parser.add_argument('--output', default='assets/fonts', help='Output directory')
    parser.add_argument('--size', type=int, default=16, help='Font size in pixels')
    parser.add_argument('--chars', default='', help='Characters to include (default: ASCII printable)')
    parser.add_argument('--padding', type=int, default=2, help='Padding between characters')
    parser.add_argument('--msdf', action='store_true', help='Generate MSDF atlas with distance field')
    
    args = parser.parse_args()
    
    chars = args.chars if args.chars else ''.join(chr(i) for i in range(32, 127))
    
    if args.msdf:
        from core.msdf_atlas import MSDFAtlas
        os.makedirs(args.output, exist_ok=True)
        font_name = Path(args.font).stem
        base_name = f"msdf_{font_name}_{args.size}"
        png_path = os.path.join(args.output, f"{base_name}.png")
        json_path = os.path.join(args.output, f"{base_name}.json")
        
        atlas = MSDFAtlas(padding=args.padding)
        atlas.generate_atlas(args.font, chars, args.size, padding=args.padding)
        atlas.save_atlas(png_path, json_path)
        print(f"Generated MSDF {png_path} and {json_path}")
    else:
        generate_font_atlas(args.font, args.output, args.size, chars, args.padding)


if __name__ == '__main__':
    main()