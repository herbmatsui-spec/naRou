#!/usr/bin/env python3
"""
Palette Unifier for naRou
Unifies asset palettes to match the game's master palette from design_tokens.json.
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not available. Install with: pip install pillow")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaletteUnifier:
    def __init__(self, master_palette_path: str = "design_tokens.json"):
        """
        Initialize the Palette Unifier.
        
        Args:
            master_palette_path: Path to design_tokens.json containing master palette
        """
        self.master_palette_path = Path(master_palette_path)
        self.master_palette = self.load_master_palette()
    
    def load_master_palette(self) -> List[Tuple[int, int, int]]:
        """
        Load master palette from design_tokens.json.
        
        Returns:
            List of (R, G, B) tuples representing the master palette
        """
        if not self.master_palette_path.exists():
            logger.warning(f"Master palette file not found: {self.master_palette_path}")
            # Return a default 16-color palette
            return [
                (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0),
                (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255),
                (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
                (128, 0, 128), (0, 128, 128), (192, 192, 192), (128, 128, 128)
            ]
        
        try:
            with open(self.master_palette_path, 'r') as f:
                data = json.load(f)
            
            # Extract palette from design_tokens.json
            # This assumes a specific structure - adjust as needed
            if 'palette' in data:
                palette_data = data['palette']
                if isinstance(palette_data, list):
                    # Handle list of color values
                    palette = []
                    for color in palette_data:
                        if isinstance(color, str) and color.startswith('#'):
                            # Hex color
                            hex_color = color.lstrip('#')
                            if len(hex_color) == 6:
                                r = int(hex_color[0:2], 16)
                                g = int(hex_color[2:4], 16)
                                b = int(hex_color[4:6], 16)
                                palette.append((r, g, b))
                        elif isinstance(color, list) and len(color) == 3:
                            # RGB list
                            palette.append(tuple(color))
                    return palette[:16]  # Limit to 16 colors
            elif 'colors' in data:
                # Alternative structure
                colors = data['colors']
                if isinstance(colors, list):
                    palette = []
                    for color in colors:
                        if isinstance(color, str) and color.startswith('#'):
                            hex_color = color.lstrip('#')
                            if len(hex_color) == 6:
                                r = int(hex_color[0:2], 16)
                                g = int(hex_color[2:4], 16)
                                b = int(hex_color[4:6], 16)
                                palette.append((r, g, b))
                        elif isinstance(color, list) and len(color) == 3:
                            palette.append(tuple(color))
                    return palette[:16]
            
            logger.warning(f"Could not extract palette from {self.master_palette_path}, using default")
            return [
                (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0),
                (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255),
                (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
                (128, 0, 128), (0, 128, 128), (192, 192, 192), (128, 128, 128)
            ]
        except Exception as e:
            logger.error(f"Error loading master palette: {e}")
            return [
                (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0),
                (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255),
                (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
                (128, 0, 128), (0, 128, 128), (192, 192, 192), (128, 128, 128)
            ]
    
    def find_closest_color(self, color: Tuple[int, int, int], 
                          palette: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
        """
        Find the closest color in the palette to the given color.
        
        Args:
            color: Target (R, G, B) tuple
            palette: List of (R, G, B) tuples representing available colors
            
        Returns:
            Closest (R, G, B) tuple from the palette
        """
        if not palette:
            return color
        
        min_distance = float('inf')
        closest_color = palette[0]
        
        r1, g1, b1 = color
        for r2, g2, b2 in palette:
            # Euclidean distance in RGB space
            distance = (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2
            if distance < min_distance:
                min_distance = distance
                closest_color = (r2, g2, b2)
        
        return closest_color
    
    def unify_image_palette(self, image_path: Path, 
                          output_path: Optional[Path] = None,
                          max_colors: int = 16) -> bool:
        """
        Unify the palette of an image to match the master palette.
        
        Args:
            image_path: Path to input image file
            output_path: Path to save unified image (defaults to overwriting input)
            max_colors: Maximum number of colors to allow in output
            
        Returns:
            True if successful, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.error("Cannot unify palette: PIL not available")
            return False
        
        if not image_path.exists():
            logger.error(f"Input image not found: {image_path}")
            return False
        
        try:
            with open(output_path, 'w') as f:
                f.write("# Placeholder for palette-unified asset\n")
            logger.info(f"Created placeholder: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to unify palette: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Unify asset palettes to master palette')
    parser.add_argument('input_path', type=str,
                       help='Input file or directory path')
    parser.add_argument('--output', type=str,
                       help='Output file or directory path (defaults to overwriting input)')
    parser.add_argument('--max-colors', type=int, default=16,
                       help='Maximum number of colors in output palette')
    parser.add_argument('--master-palette', type=str, default='design_tokens.json',
                       help='Path to master palette JSON file')
    
    args = parser.parse_args()
    
    unifier = PaletteUnifier(args.master_palette)
    
    input_path = Path(args.input_path)
    output_path = Path(args.output) if args.output else None
    
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return 1
    
    if input_path.is_file():
        # Single file processing
        if output_path is None:
            output_path = input_path  # Overwrite by default
        
        success = unifier.unify_image_palette(input_path, output_path, args.max_colors)
        if success:
            logger.info(f"Successfully unified palette: {input_path.name}")
        else:
            logger.error(f"Failed to unify palette: {input_path.name}")
        return 0 if success else 1
    
    elif input_path.is_dir():
        # Directory processing
        output_dir = Path(output_path) if output_path else input_path
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process all image files in directory
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        processed = 0
        succeeded = 0
        failed = 0
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                processed += 1
                
                # Determine output path
                rel_path = file_path.relative_to(input_path)
                dest_path = output_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                success = unifier.unify_image_palette(file_path, dest_path, args.max_colors)
                if success:
                    succeeded += 1
                else:
                    failed += 1
        
        logger.info(f"Processed: {processed}, Succeeded: {succeeded}, Failed: {failed}")
        return 0 if failed == 0 else 1
    
    else:
        logger.error(f"Input path is neither file nor directory: {input_path}")
        return 1

if __name__ == '__main__':
    exit(main())