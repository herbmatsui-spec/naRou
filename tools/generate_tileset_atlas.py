#!/usr/bin/env python3
"""
Tile Atlas Generator
Packs individual tile PNGs into texture atlases for efficient rendering.
"""

import json
from pathlib import Path
from typing import Dict, List
from PIL import Image

def create_atlas(tile_size: int, output_dir: str = "assets/tiles"):
    """
    Create texture atlases for 16x16 and 32x32 tile sets.
    
    Args:
        tile_size: Base tile size (16 or 32)
        output_dir: Directory containing tile folders and where to output atlases
    """
    output_path = Path(output_dir)
    size_dir = f"{tile_size}x{tile_size}"
    
    # Read tileset definition
    defs_path = output_path / "tileset_def.json"
    if not defs_path.exists():
        print(f"Error: {defs_path} not found")
        return
    
    with open(defs_path) as f:
        defs = json.load(f)
    
    # Collect all tile images
    tiles: Dict[str, List[Image.Image]] = {}
    tile_info: Dict[str, Dict] = {}
    
    for tile_id, tile_def in defs["tiles"].items():
        file_path = output_path / size_dir / tile_def["file"]
        if not file_path.exists():
            print(f"Warning: Tile image not found: {file_path}")
            # Create a placeholder image for now
            img = Image.new('RGBA', (tile_size, tile_size), (255, 0, 255, 255))  # Magenta placeholder
        else:
            img = Image.open(file_path).convert('RGBA')
        
        # Handle variants
        variant_count = tile_def.get("variants", 1)
        if variant_count > 1:
            # For now, assume variants are separate files or we'll duplicate
            # In a real implementation, variants might be in a strip or separate files
            frames = [img] * variant_count
        else:
            frames = [img]
        
        # Handle animation frames
        if "frames" in tile_def:
            frame_count = tile_def["frames"]
            # For now, duplicate the image for animation frames
            # In reality, these would be separate files or a sprite strip
            frames = [img] * frame_count
        
        tiles[tile_id] = frames
        tile_info[tile_id] = tile_def
    
    # Calculate atlas dimensions
    # Simple grid packing: organize by tile type
    max_cols = 16  # Arbitrary, can be adjusted
    cols_needed = min(max_cols, len(tiles))
    rows_needed = (len(tiles) + max_cols - 1) // max_cols
    
    atlas_width = cols_needed * tile_size
    atlas_height = rows_needed * tile_size
    
    # Create atlas image
    atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
    
    # Metadata for tile lookup
    metadata = {
        "tile_size": tile_size,
        "atlas_width": atlas_width,
        "atlas_height": atlas_height,
        "tiles": {}
    }
    
    # Pack tiles into atlas
    for idx, (tile_id, frames) in enumerate(tiles.items()):
        row = idx // max_cols
        col = idx % max_cols
        x_offset = col * tile_size
        y_offset = row * tile_size
        
        # Use first frame for atlas (variants/animation handled via UV offsets)
        atlas.paste(frames[0], (x_offset, y_offset))
        
        # Store UV information
        metadata["tiles"][tile_id] = {
            "x": x_offset,
            "y": y_offset,
            "width": tile_size,
            "height": tile_size,
            "variants": tile_info[tile_id].get("variants", 1),
            "animated": "frames" in tile_info[tile_id],
            "frames": tile_info[tile_id].get("frames", 1),
            "fps": tile_info[tile_id].get("fps", 1),
            "directions": tile_info[tile_id].get("directions", 1)
        }
    
    # Save atlas
    atlas_path = output_path / f"tileset_{tile_size}x{tile_size}.png"
    atlas.save(atlas_path)
    print(f"Saved atlas: {atlas_path}")
    
    # Save metadata
    meta_path = output_path / f"tileset_{tile_size}x{tile_size}.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata: {meta_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate tile atlases")
    parser.add_argument("--size", type=int, choices=[16, 32], required=True,
                       help="Tile size to generate atlas for")
    parser.add_argument("--input", type=str, default="assets/tiles",
                       help="Input directory containing tile folders")
    parser.add_argument("--output", type=str, default="assets/tiles",
                       help="Output directory for atlases")
    
    args = parser.parse_args()
    create_atlas(args.size, args.output)

if __name__ == "__main__":
    main()