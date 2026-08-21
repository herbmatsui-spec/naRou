#!/usr/bin/env python3
"""
Animation Interpolator for naRou
Interpolates animation frames to create smoother animations.
"""
from __future__ import annotations

import argparse
import logging
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


class AnimationInterpolator:
    def __init__(self):
        """Initialize the Animation Interpolator."""

    def interpolate_frames(
        self, frames: list[Path], target_frame_count: int, output_dir: Path
    ) -> list[Path]:
        """
        Interpolate between keyframes to create smoother animation.

        Args:
            frames: List of paths to keyframe images (in order)
            target_frame_count: Desired total number of frames in output
            output_dir: Directory to save interpolated frames

        Returns:
            List of paths to interpolated frames
        """
        if not PIL_AVAILABLE:
            logger.error("Cannot interpolate frames: PIL not available")
            return []

        if len(frames) < 2:
            logger.error("Need at least 2 frames to interpolate")
            return []

        if target_frame_count < len(frames):
            logger.warning(
                f"Target frame count ({target_frame_count}) is less than keyframe count ({len(frames)}). Returning keyframes."
            )
            return frames

        output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate how many interpolated frames to insert between each keyframe
        intervals = len(frames) - 1  # Number of gaps between keyframes
        frames_per_interval = (target_frame_count - len(frames)) // intervals
        remainder = (target_frame_count - len(frames)) % intervals

        logger.info(
            f"Interpolating {len(frames)} keyframes to {target_frame_count} frames"
        )
        logger.info(
            f"{intervals} intervals, {frames_per_interval} frames per interval, {remainder} remainder"
        )

        result_frames = []

        for i in range(len(frames)):
            # Add the current keyframe
            result_frames.append(frames[i])

            # If this is not the last frame, interpolate to the next keyframe
            if i < len(frames) - 1:
                # Determine how many frames to interpolate in this interval
                frames_in_this_interval = frames_per_interval
                if i < remainder:  # Distribute remainder to first intervals
                    frames_in_this_interval += 1

                if frames_in_this_interval > 0:
                    # Interpolate between frames[i] and frames[i+1]
                    interpolated = self._interpolate_between_frames(
                        frames[i],
                        frames[i + 1],
                        frames_in_this_interval + 1,  # +1 to include the end frame
                    )
                    # Skip the first frame (it's the keyframe we already added) and last frame (will be added as next keyframe)
                    result_frames.extend(interpolated[1:-1])

        # Save all frames
        saved_paths = []
        for i, frame_path in enumerate(result_frames):
            output_path = output_dir / f"frame_{i:04d}.png"
            try:
                # Copy the frame to output
                sh.copy2(frame_path, output_path)
                saved_paths.append(output_path)
            except Exception as e:
                logger.error(f"Error saving frame {i}: {e}")

        logger.info(f"Saved {len(saved_paths)} interpolated frames to {output_dir}")
        return saved_paths

    def _interpolate_between_frames(
        self, start_frame: Path, end_frame: Path, steps: int
    ) -> list[Path]:
        """
        Interpolate between two frames to create intermediate frames.

        Args:
            start_frame: Path to start frame image
            end_frame: Path to end frame image
            steps: Number of steps including start and end

        Returns:
            List of paths to interpolated frames (including start and end)
        """
        if not PIL_AVAILABLE:
            return [start_frame, end_frame]

        try:
            with Image.open(start_frame) as img1, Image.open(end_frame) as img2:
                # Ensure images are the same size
                if img1.size != img2.size:
                    logger.warning(
                        f"Frame sizes differ: {img1.size} vs {img2.size}. Resizing to match."
                    )
                    # Use the smaller size
                    width = min(img1.width, img2.width)
                    height = min(img1.height, img2.height)
                    img1 = img1.crop((0, 0, width, height))
                    img2 = img2.crop((0, 0, width, height))

                # Convert to RGBA for consistent interpolation
                if img1.mode != "RGBA":
                    img1 = img1.convert("RGBA")
                if img2.mode != "RGBA":
                    img2 = img2.convert("RGBA")

                # Get pixel data
                pixels1 = list(img1.getdata())
                pixels2 = list(img2.getdata())

                # Create interpolated frames
                interpolated_frames = []

                for step in range(steps):
                    # Calculate interpolation ratio (0.0 to 1.0)
                    ratio = step / (steps - 1) if steps > 1 else 0.5

                    # Interpolate each pixel
                    interpolated_pixels = []
                    for p1, p2 in zip(pixels1, pixels2):
                        # Interpolate each channel (R, G, B, A)
                        r = int(p1[0] + (p2[0] - p1[0]) * ratio)
                        g = int(p1[1] + (p2[1] - p1[1]) * ratio)
                        b = int(p1[2] + (p2[2] - p1[2]) * ratio)
                        a = int(p1[3] + (p2[3] - p1[3]) * ratio)
                        interpolated_pixels.append((r, g, b, a))

                    # Create new image
                    interpolated_img = Image.new("RGBA", img1.size)
                    interpolated_img.putdata(interpolated_pixels)

                    # Save to temporary file
                    temp_path = Path(f"/tmp/interpolated_{step}_{int(time.time())}.png")
                    interpolated_img.save(temp_path)
                    interpolated_frames.append(temp_path)

                return interpolated_frames
        except Exception as e:
            logger.error(f"Error interpolating between frames: {e}")
            return [start_frame, end_frame]


def main():
    parser = argparse.ArgumentParser(description="Interpolate animation frames")
    parser.add_argument(
        "input_frames", nargs="+", type=str, help="Input frame files (in order)"
    )
    parser.add_argument(
        "--target-frames",
        type=int,
        required=True,
        help="Target number of frames in output",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for interpolated frames",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Treat animation as looping (connect last frame to first)",
    )

    args = parser.parse_args()

    # Convert string paths to Path objects
    frame_paths = [Path(p) for p in args.input_frames]
    output_dir = Path(args.output_dir)

    # Validate input files
    for frame_path in frame_paths:
        if not frame_path.exists():
            logger.error(f"Input frame not found: {frame_path}")
            return 1

    interpolator = AnimationInterpolator()

    if args.loop and len(frame_paths) >= 2:
        # For looping animations, also interpolate from last frame to first
        logger.info(
            "Creating looping animation: adding interpolation from last to first frame"
        )
        # We'll handle this by duplicating the first frame at the end for interpolation purposes
        extended_frames = frame_paths + [frame_paths[0]]
        result_frames = interpolator.interpolate_frames(
            extended_frames, args.target_frames + 1, output_dir
        )
        # Remove the duplicate last frame if it was added
        if len(result_frames) > args.target_frames:
            result_frames = result_frames[:-1]
    else:
        result_frames = interpolator.interpolate_frames(
            frame_paths, args.target_frames, output_dir
        )

    if result_frames:
        logger.info(
            f"Successfully interpolated {len(frame_paths)} keyframes to {len(result_frames)} frames"
        )
        return 0
    else:
        logger.error("Failed to interpolate frames")
        return 1


if __name__ == "__main__":
    import time

    sys.exit(main())
