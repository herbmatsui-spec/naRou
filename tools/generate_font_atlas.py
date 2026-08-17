#!/usr/bin/env python3
"""
フォントテクスチャアトラス生成スクリプト
PIL/Pillowを使用して、指定された文字からテクスチャアトラスを生成
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

# 対象文字リスト
CHARACTERS = [
    # 基本タイル文字
    '@', 'p', '#', '.', '>', '⛩️',
    # アイテム文字
    '%', '?', '$', '*', '!',
    # 数字
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    # 大文字アルファベット
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    # 小文字アルファベット
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
]

def get_font(size):
    """フォントを取得"""
    try:
        # システムフォントを試す
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", size)
        except Exception:
            try:
                return ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", size)
            except Exception:
                # デフォルトフォントにフォールバック
                return ImageFont.load_default()

def generate_font_atlas(atlas_size=512, glyph_size=24, padding=2, output_dir="demos/assets"):
    """フォントテクスチャアトラスを生成"""
    
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # フォントを取得
    font = get_font(glyph_size)
    
    # キャンバスを作成（透明背景）
    atlas = Image.new('RGBA', (atlas_size, atlas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(atlas)
    
    # グリフマップを初期化
    glyph_map = {}
    
    # 1行に配置可能なグリフ数を計算
    glyphs_per_row = (atlas_size + padding) // (glyph_size + padding)
    
    # グリフを配置
    for i, char in enumerate(CHARACTERS):
        row = i // glyphs_per_row
        col = i % glyphs_per_row
        
        x = col * (glyph_size + padding) + padding
        y = row * (glyph_size + padding) + padding
        
        # グリフの位置とサイズを記録
        glyph_map[char] = {
            "x": x,
            "y": y,
            "width": glyph_size,
            "height": glyph_size
        }
        
        # グリフを描画
        draw.text((x + glyph_size // 2, y + glyph_size // 2), char, 
                 fill=(255, 255, 255, 255), font=font, anchor="mm")
    
    # アトラス画像を保存
    atlas_path = os.path.join(output_dir, "font_atlas.png")
    atlas.save(atlas_path)
    print(f"Font atlas saved to: {atlas_path}")
    
    # メタデータを生成
    metadata = {
        "format": "font_atlas",
        "textureSize": {
            "width": atlas_size,
            "height": atlas_size
        },
        "glyphSize": {
            "width": glyph_size,
            "height": glyph_size
        },
        "padding": padding,
        "glyphs": glyph_map
    }
    
    # メタデータを保存
    metadata_path = os.path.join(output_dir, "font_atlas.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Font atlas metadata saved to: {metadata_path}")
    
    return atlas_path, metadata_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate font texture atlas")
    parser.add_argument("--size", type=int, default=512, help="Atlas size in pixels (default: 512)")
    parser.add_argument("--glyph-size", type=int, default=24, help="Glyph size in pixels (default: 24)")
    parser.add_argument("--padding", type=int, default=2, help="Padding between glyphs in pixels (default: 2)")
    parser.add_argument("--output", type=str, default="demos/assets", help="Output directory (default: demos/assets)")
    
    args = parser.parse_args()
    
    print("Generating font texture atlas...")
    atlas_path, metadata_path = generate_font_atlas(
        atlas_size=args.size,
        glyph_size=args.glyph_size,
        padding=args.padding,
        output_dir=args.output
    )
    print("Done!")
    print(f"  Atlas image: {atlas_path}")
    print(f"  Metadata: {metadata_path}")