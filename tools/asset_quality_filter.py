#!/usr/bin/env python3
"""
Asset Quality Filter for naRou
Filters and validates generated assets based on quality criteria.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not available. Install with: pip install pillow")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssetQualityFilter:
    def __init__(self):
        """Initialize the Asset Quality Filter."""

    def check_resolution(self, image_path: Path, expected_size: tuple[int, int]) -> bool:
        """
        Check if image has the expected resolution.

        Args:
            image_path: Path to image file
            expected_size: Expected (width, height) tuple

        Returns:
            True if resolution matches, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.warning("Cannot check resolution: PIL not available")
            return True  # Assume OK if we can't check

        try:
            with Image.open(image_path) as img:
                width, height = img.size
                expected_width, expected_height = expected_size
                return width == expected_width and height == expected_height
        except Exception as e:
            logger.error(f"Error checking resolution for {image_path}: {e}")
            return False

    def check_transparency(self, image_path: Path, min_transparent_ratio: float = 0.0) -> bool:
        """
        Check if image has sufficient transparency (for assets that should be transparent).

        Args:
            image_path: Path to image file
            min_transparent_ratio: Minimum ratio of transparent pixels (0.0 to 1.0)

        Returns:
            True if transparency meets threshold, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.warning("Cannot check transparency: PIL not available")
            return True  # Assume OK if we can't check

        try:
            with Image.open(image_path) as img:
                # Convert to RGBA if not already
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Get alpha channel
                alpha = img.split()[-1]  # Alpha channel is last

                # Count transparent pixels (alpha = 0)
                total_pixels = alpha.width * alpha.height
                transparent_pixels = sum(1 for pixel in alpha.getdata() if pixel == 0)
                transparent_ratio = transparent_pixels / total_pixels

                return transparent_ratio >= min_transparent_ratio
        except Exception as e:
            logger.error(f"Error checking transparency for {image_path}: {e}")
            return False

    def check_color_count(self, image_path: Path, max_colors: int) -> bool:
        """
        Check if image uses no more than the specified number of colors.

        Args:
            image_path: Path to image file
            max_colors: Maximum allowed number of colors

        Returns:
            True if color count is within limit, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.warning("Cannot check color count: PIL not available")
            return True  # Assume OK if we can't check

        try:
            with Image.open(image_path) as img:
                # Convert to mode 'P' (palette) to get color count
                if img.mode != "P":
                    img_p = img.convert("P")
                else:
                    img_p = img

                # Get the palette and count unique colors
                colors = img_p.getcolors(maxcolors=max_colors + 1)
                if colors is None:
                    # More than max_colors colors
                    return False
                else:
                    # Count non-zero entries in the color list
                    color_count = len([c for c in colors if c[0] > 0])
                    return color_count <= max_colors
        except Exception as e:
            logger.error(f"Error checking color count for {image_path}: {e}")
            return False

    def check_seamless_tiling(self, image_path: Path, tolerance: int = 2) -> bool:
        """
        Check if image tiles seamlessly (for terrain textures).

        Args:
            image_path: Path to image file
            tolerance: Tolerance for pixel differences (0-255)

        Returns:
            True if image tiles seamlessly, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.warning("Cannot check seamless tiling: PIL not available")
            return True  # Assume OK if we can't check

        try:
            with Image.open(image_path) as img:
                width, height = img.size

                # Check horizontal tiling (left edge vs right edge)
                left_edge = img.crop((0, 0, 1, height))
                right_edge = img.crop((width - 1, 0, width, height))

                # Check vertical tiling (top edge vs bottom edge)
                top_edge = img.crop((0, 0, width, 1))
                bottom_edge = img.crop((0, height - 1, width, height))

                # Compare edges
                h_diff = self._image_difference(left_edge, right_edge)
                v_diff = self._image_difference(top_edge, bottom_edge)

                return h_diff <= tolerance and v_diff <= tolerance
        except Exception as e:
            logger.error(f"Error checking seamless tiling for {image_path}: {e}")
            return False

    def _image_difference(self, img1: Image.Image, img2: Image.Image) -> int:
        """
        Calculate difference between two images.

        Args:
            img1: First image
            img2: Second image

        Returns:
            Sum of pixel differences
        """
        if img1.size != img2.size:
            # Resize to match
            width = min(img1.width, img2.width)
            height = min(img1.height, img2.height)
            img1 = img1.crop((0, 0, width, height))
            img2 = img2.crop((0, 0, width, height))

        # Convert to grayscale for simpler comparison
        if img1.mode != "L":
            img1 = img1.convert("L")
        if img2.mode != "L":
            img2 = img2.convert("L")

        # Calculate difference
        diff = 0
        pixels1 = list(img1.getdata())
        pixels2 = list(img2.getdata())

        for p1, p2 in zip(pixels1, pixels2):
            diff += abs(p1 - p2)

        return diff

    def validate_asset(
        self,
        image_path: Path,
        expected_size: tuple[int, int] | None = None,
        check_transparency: bool = False,
        min_transparent_ratio: float = 0.0,
        max_colors: int | None = None,
        check_seamless: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        Validate an asset against multiple quality criteria.

        Args:
            image_path: Path to image file to validate
            expected_size: Expected (width, height) tuple, or None to skip resolution check
            check_transparency: Whether to check transparency
            min_transparent_ratio: Minimum transparent pixel ratio (0.0 to 1.0)
            max_colors: Maximum allowed number of colors, or None to skip color check
            check_seamless: Whether to check seamless tiling

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not image_path.exists():
            issues.append(f"File does not exist: {image_path}")
            return False, issues

        # Resolution check
        if expected_size is not None:
            if not self.check_resolution(image_path, expected_size):
                issues.append(f"Resolution mismatch: expected {expected_size}")

        # Transparency check
        if check_transparency:
            if not self.check_transparency(image_path, min_transparent_ratio):
                issues.append(
                    f"Insufficient transparency: minimum {min_transparent_ratio * 100}% required"
                )

        # Color count check
        if max_colors is not None:
            if not self.check_color_count(image_path, max_colors):
                issues.append(f"Too many colors: maximum {max_colors} allowed")

        # Seamless tiling check
        if check_seamless and not self.check_seamless_tiling(image_path):
            issues.append("Image does not tile seamlessly")

        is_valid = len(issues) == 0
        return is_valid, issues


def main():
    parser = argparse.ArgumentParser(description="Asset Quality Filter for naRou")
    parser.add_argument("action", choices=["check", "filter"], help="Action to perform")
    parser.add_argument("input_path", type=str, help="Input file or directory path")
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for filtered assets (for filter action)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["terrain", "entity", "effect", "ui", "portrait", "background"],
        help="Asset category for specific checks",
    )
    parser.add_argument("--reject-dir", type=str, help="Directory to move rejected assets to")

    args = parser.parse_args()

    filter_tool = AssetQualityFilter()

    input_path = Path(args.input_path)

    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return 1

    if args.action == "check":
        # Single file check
        if input_path.is_file():
            is_valid, issues = filter_tool.validate_asset(
                input_path,
                expected_size=(16, 16),  # Default, can be overridden by category
                check_transparency=False,
                max_colors=16,
                check_seamless=False,
            )

            if is_valid:
                print(f"✓ {input_path.name}: VALID")
            else:
                print(f"✗ {input_path.name}: INVALID")
                for issue in issues:
                    print(f"  - {issue}")
        else:
            logger.error("For 'check' action, input_path must be a file")
            return 1

    elif args.action == "filter":
        # Directory filtering
        if not input_path.is_dir():
            logger.error("For 'filter' action, input_path must be a directory")
            return 1

        output_dir = Path(args.output) if args.output else input_path / "filtered"
        reject_dir = Path(args.reject_dir) if args.reject_dir else input_path / "rejected"

        output_dir.mkdir(parents=True, exist_ok=True)
        if reject_dir:
            reject_dir.mkdir(parents=True, exist_ok=True)

        # Process all image files in directory
        image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
        processed = 0
        passed = 0
        failed = 0

        for file_path in input_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                processed += 1

                # Determine expected size based on category or filename
                expected_size = None
                check_seamless = False
                max_colors = 16

                if args.category:
                    if args.category == "terrain":
                        expected_size = (16, 16)
                        check_seamless = True
                    elif args.category in ["entity", "effect"]:
                        expected_size = (32, 32)
                    elif args.category == "ui":
                        expected_size = None  # Variable size
                    elif args.category == "portrait":
                        expected_size = (64, 64)
                    elif args.category == "background":
                        expected_size = (256, 144)

                # Override based on filename if possible
                if "16x16" in file_path.name:
                    expected_size = (16, 16)
                    check_seamless = True
                elif "32x32" in file_path.name:
                    expected_size = (32, 32)
                elif "64x64" in file_path.name:
                    expected_size = (64, 64)
                elif "256x144" in file_path.name:
                    expected_size = (256, 144)

                is_valid, issues = filter_tool.validate_asset(
                    file_path,
                    expected_size=expected_size,
                    check_transparency=False,  # Most game assets are not fully transparent
                    max_colors=max_colors,
                    check_seamless=check_seamless,
                )

                if is_valid:
                    # Copy to output directory
                    rel_path = file_path.relative_to(input_path)
                    dest_path = output_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)
                    passed += 1
                    logger.debug(f"PASSED: {file_path.name}")
                else:
                    # Move to reject directory if specified
                    if reject_dir:
                        rel_path = file_path.relative_to(input_path)
                        dest_path = reject_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(dest_path))
                    else:
                        # Just delete or leave in place - here we'll leave in place and log
                        logger.info(f"FAILED: {file_path.name} - {', '.join(issues)}")
                    failed += 1

        logger.info(f"Processed: {processed}, Passed: {passed}, Failed: {failed}")

        if output_dir.exists():
            logger.info(f"Filtered assets saved to: {output_dir}")
        if reject_dir.exists() and any(reject_dir.iterdir()):
            logger.info(f"Rejected assets saved to: {reject_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
