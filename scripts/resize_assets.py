#!/usr/bin/env python3
"""
Image Resize Script for Asset Packs
Resizes images to target tile size using nearest-neighbor (preserves pixel art).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


def resize_image(input_path: Path, output_path: Path, target_size: int) -> bool:
    """Resize a single image to target_size x target_size using nearest-neighbor."""
    try:
        img = Image.open(input_path).convert("RGBA")
        if img.size == (target_size, target_size):
            return True  # Already correct size

        resized = img.resize((target_size, target_size), Image.NEAREST)
        resized.save(output_path)
        return True
    except Exception as e:
        print(f"Error resizing {input_path}: {e}")
        return False


def process_directory(
    input_dir: Path, output_dir: Path, target_size: int, recursive: bool = False
) -> int:
    """Process all images in a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.png" if recursive else "*.png"
    count = 0

    for img_path in input_dir.glob(pattern):
        if img_path.is_file():
            rel_path = img_path.relative_to(input_dir)
            out_path = output_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if resize_image(img_path, out_path, target_size):
                count += 1
                print(f"Resized: {rel_path}")

    return count


def main():
    parser = argparse.ArgumentParser(description="Resize images for asset packs")
    parser.add_argument("input", help="Input directory or file")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--size", type=int, default=16, help="Target tile size (default: 16)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_file():
        output_path.mkdir(parents=True, exist_ok=True)
        if resize_image(input_path, output_path / input_path.name, args.size):
            print(f"Resized: {input_path.name}")
            return 0
        else:
            return 1
    elif input_path.is_dir():
        count = process_directory(input_path, output_path, args.size, args.recursive)
        print(f"\nProcessed {count} images")
        return 0
    else:
        print(f"Input not found: {input_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
