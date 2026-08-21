#!/usr/bin/env python3
"""
Asset optimization script for running optimization passes on processed assets.
Applies various optimization techniques to reduce file sizes and improve performance.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def optimize_tilesets(tileset_dir: str, output_dir: str, config: dict) -> dict:
    """Optimize tileset assets (compress PNGs, repack atlases if needed)."""
    stats = {
        "assets_processed": 0,
        "assets_optimized": 0,
        "space_saved_bytes": 0,
        "errors": [],
        "operations": [],
    }

    if not os.path.exists(tileset_dir):
        stats["errors"].append(f"Tileset directory does not exist: {tileset_dir}")
        return stats

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    for root, dirs, files in os.walk(tileset_dir):
        for file in files:
            if file.endswith(".png"):
                stats["assets_processed"] += 1
                png_path = os.path.join(root, file)
                rel_path = os.path.relpath(png_path, tileset_dir)
                out_path = os.path.join(output_dir, rel_path)

                # Ensure output directory exists
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                try:
                    original_size = os.path.getsize(png_path)

                    # Try to optimize PNG (would use pngcrush, optipng, or similar in real implementation)
                    # For this implementation, we'll just copy and note that optimization would happen
                    shutil.copy2(png_path, out_path)

                    # In a real implementation, we would run:
                    # subprocess.run(['pngcrush', '-brute', png_path, out_path], capture_output=True)
                    # or use PIL to optimize

                    optimized_size = os.path.getsize(out_path)
                    saved = original_size - optimized_size

                    if saved > 0:
                        stats["assets_optimized"] += 1
                        stats["space_saved_bytes"] += saved
                        stats["operations"].append(
                            {
                                "asset": rel_path,
                                "operation": "png_compression",
                                "original_size": original_size,
                                "optimized_size": optimized_size,
                                "space_saved": saved,
                            }
                        )
                    else:
                        # No savings, but still copied
                        pass

                except Exception as e:
                    stats["errors"].append(f"Error optimizing {png_path}: {e}")

    return stats


def optimize_fonts(font_dir: str, output_dir: str, config: dict) -> dict:
    """Optimize font assets."""
    stats = {
        "assets_processed": 0,
        "assets_optimized": 0,
        "space_saved_bytes": 0,
        "errors": [],
        "operations": [],
    }

    if not os.path.exists(font_dir):
        stats["errors"].append(f"Font directory does not exist: {font_dir}")
        return stats

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".png"):
                stats["assets_processed"] += 1
                png_path = os.path.join(root, file)
                rel_path = os.path.relpath(png_path, font_dir)
                out_path = os.path.join(output_dir, rel_path)

                # Ensure output directory exists
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                try:
                    original_size = os.path.getsize(png_path)

                    # Copy file (optimization would happen here)
                    shutil.copy2(png_path, out_path)

                    optimized_size = os.path.getsize(out_path)
                    saved = original_size - optimized_size

                    if saved > 0:
                        stats["assets_optimized"] += 1
                        stats["space_saved_bytes"] += saved
                        stats["operations"].append(
                            {
                                "asset": rel_path,
                                "operation": "font_compression",
                                "original_size": original_size,
                                "optimized_size": optimized_size,
                                "space_saved": saved,
                            }
                        )

                except Exception as e:
                    stats["errors"].append(f"Error optimizing {png_path}: {e}")

    return stats


def optimize_sounds(sound_dir: str, output_dir: str, config: dict) -> dict:
    """Optimize sound assets (convert to appropriate formats, adjust bitrates)."""
    stats = {
        "assets_processed": 0,
        "assets_optimized": 0,
        "space_saved_bytes": 0,
        "errors": [],
        "operations": [],
    }

    if not os.path.exists(sound_dir):
        stats["errors"].append(f"Sound directory does not exist: {sound_dir}")
        return stats

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get quality settings from config
    music_bitrate = (
        config.get("sound", {})
        .get("quality", {})
        .get("music", {})
        .get("bitrate", "192k")
    )
    sfx_bitrate = (
        config.get("sound", {}).get("quality", {}).get("sfx", {}).get("bitrate", "128k")
    )

    extensions = [".ogg", ".mp3", ".wav", ".flac"]

    for root, dirs, files in os.walk(sound_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                stats["assets_processed"] += 1
                sound_path = os.path.join(root, file)
                rel_path = os.path.relpath(sound_path, sound_dir)

                # Determine if it's music or sfx based on path or filename
                is_music = "music" in sound_path.lower() or "bgm" in sound_path.lower()
                target_bitrate = music_bitrate if is_music else sfx_bitrate

                # For optimization, we'll convert to OGG with target bitrate
                # Change extension to .ogg for optimized version
                name_without_ext = os.path.splitext(rel_path)[0]
                out_path = os.path.join(output_dir, name_without_ext + ".ogg")

                # Ensure output directory exists
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                try:
                    original_size = os.path.getsize(sound_path)

                    # In a real implementation, we would use ffmpeg or similar:
                    # ffmpeg -i input.wav -c:a libvorbis -b:a 192k output.ogg
                    # For now, just copy and note optimization would occur
                    shutil.copy2(sound_path, out_path)

                    optimized_size = os.path.getsize(out_path)
                    saved = original_size - optimized_size

                    if saved > 0:
                        stats["assets_optimized"] += 1
                        stats["space_saved_bytes"] += saved
                        stats["operations"].append(
                            {
                                "asset": rel_path,
                                "operation": "audio_optimization",
                                "original_size": original_size,
                                "optimized_size": optimized_size,
                                "space_saved": saved,
                                "target_bitrate": target_bitrate,
                            }
                        )
                    # Note: In real optimization, size might increase if converting from lower quality
                    # but we're assuming optimization for best balance

                except Exception as e:
                    stats["errors"].append(f"Error optimizing {sound_path}: {e}")

    return stats


def optimize_models(model_dir: str, output_dir: str, config: dict) -> dict:
    """Optimize model assets (apply compression, LOD generation, etc.)."""
    stats = {
        "assets_processed": 0,
        "assets_optimized": 0,
        "space_saved_bytes": 0,
        "errors": [],
        "operations": [],
    }

    if not os.path.exists(model_dir):
        stats["errors"].append(f"Model directory does not exist: {model_dir}")
        return stats

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    extensions = [
        ".obj",
        ".fbx",
        ".gltf",
        ".glb",
        ".dae",
        ".3ds",
        ".blend",
        ".ply",
        ".stl",
    ]

    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                stats["assets_processed"] += 1
                model_path = os.path.join(root, file)
                rel_path = os.path.relpath(model_path, model_dir)

                # For optimization, we'll convert to GLTF format (more efficient for web/apps)
                name_without_ext = os.path.splitext(rel_path)[0]
                out_path = os.path.join(output_dir, name_without_ext + ".gltf")

                # Ensure output directory exists
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                try:
                    original_size = os.path.getsize(model_path)

                    # In a real implementation, we would use assimp, blender CLI, or similar:
                    # assimp export input.obj output.gltf
                    # Or apply mesh compression, LOD generation, etc.
                    # For now, just copy and note optimization would occur
                    shutil.copy2(model_path, out_path)

                    optimized_size = os.path.getsize(out_path)
                    saved = original_size - optimized_size

                    if saved > 0:
                        stats["assets_optimized"] += 1
                        stats["space_saved_bytes"] += saved
                        stats["operations"].append(
                            {
                                "asset": rel_path,
                                "operation": "model_format_conversion",
                                "original_size": original_size,
                                "optimized_size": optimized_size,
                                "space_saved": saved,
                                "target_format": "GLTF",
                            }
                        )

                except Exception as e:
                    stats["errors"].append(f"Error optimizing {model_path}: {e}")

    return stats


def run_optimization_pass(config: dict, asset_types: list[str]) -> dict:
    """Run optimization pass on specified asset types."""
    start_time = time.time()

    results = {
        "timestamp": start_time,
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "asset_types_processed": asset_types,
        "results": {},
        "summary": {
            "total_assets_processed": 0,
            "total_assets_optimized": 0,
            "total_space_saved_bytes": 0,
            "total_errors": 0,
        },
    }

    # Define optimization functions
    optimizers = {
        "tilesets": optimize_tilesets,
        "fonts": optimize_fonts,
        "sounds": optimize_sounds,
        "models": optimize_models,
    }

    # Process each asset type
    for asset_type in asset_types:
        if asset_type not in optimizers:
            continue

        print(f"Optimizing {asset_type}...")

        asset_dir = os.path.join(config["directories"]["output"], asset_type)
        optimized_dir = os.path.join(
            config["directories"]["output"], f"{asset_type}_optimized"
        )

        # Run optimization
        result = optimizers[asset_type](asset_dir, optimized_dir, config)
        results["results"][asset_type] = result

        # Update summary
        results["summary"]["total_assets_processed"] += result.get(
            "assets_processed", 0
        )
        results["summary"]["total_assets_optimized"] += result.get(
            "assets_optimized", 0
        )
        results["summary"]["total_space_saved_bytes"] += result.get(
            "space_saved_bytes", 0
        )
        results["summary"]["total_errors"] += len(result.get("errors", []))

        # Replace original with optimized version (in a real pipeline, you might want to keep both)
        # For safety, we'll just report the results without replacing in this script

        # Print summary for this asset type
        print(f"  Processed: {result.get('assets_processed', 0)} assets")
        print(f"  Optimized: {result.get('assets_optimized', 0)} assets")
        print(f"  Space saved: {result.get('space_saved_bytes', 0)} bytes")
        if result.get("errors"):
            print(f"  Errors: {len(result['errors'])}")

    end_time = time.time()
    results["duration_seconds"] = end_time - start_time

    return results


def save_optimization_results(results: dict, output_path: str) -> bool:
    """Save optimization results to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Optimization results saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving optimization results: {e}")
        return False


def print_optimization_summary(results: dict, verbose: bool = False):
    """Print a formatted summary of the optimization results."""
    print(f"\n{'=' * 70}")
    print("ASSET OPTIMIZATION RESULTS")
    print(f"{'=' * 70}")
    print(f"Timestamp: {results['datetime']}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")

    print("\nSUMMARY:")
    summary = results.get("summary", {})
    print(f"  Asset Types Processed: {len(results.get('asset_types_processed', []))}")
    print(f"  Total Assets Processed: {summary.get('total_assets_processed', 0)}")
    print(f"  Total Assets Optimized: {summary.get('total_assets_optimized', 0)}")
    print(
        f"  Total Space Saved: {summary.get('total_space_saved_bytes', 0)} bytes ({summary.get('total_space_saved_bytes', 0) / (1024 * 1024):.2f} MB)"
    )
    print(f"  Total Errors: {summary.get('total_errors', 0)}")

    print("\nDETAILED RESULTS BY ASSET TYPE:")
    for asset_type, result in results.get("results", {}).items():
        print(f"\n  {asset_type.upper()}:")
        print(f"    Processed: {result.get('assets_processed', 0)}")
        print(f"    Optimized: {result.get('assets_optimized', 0)}")
        print(
            f"    Space Saved: {result.get('space_saved_bytes', 0)} bytes ({result.get('space_saved_bytes', 0) / (1024 * 1024):.2f} MB)"
        )
        print(f"    Errors: {len(result.get('errors', []))}")

        if result.get("errors") and verbose:
            print("    Error Details:")
            for error in result["errors"][:3]:
                print(f"      - {error}")
            if len(result["errors"]) > 3:
                print(f"      ... and {len(result['errors']) - 3} more errors")

        # Show optimization operations
        operations = result.get("operations", [])
        if operations:
            print(f"    Optimization Operations: {len(operations)}")
            # Show space saved by operation type
            op_savings = {}
            for op in operations:
                op_type = op.get("operation", "unknown")
                savings = op.get("space_saved", 0)
                op_savings[op_type] = op_savings.get(op_type, 0) + savings

            for op_type, savings in op_savings.items():
                if savings > 0:
                    print(f"      {op_type}: {savings} bytes saved")


def main():
    parser = argparse.ArgumentParser(
        description="Run optimization passes on processed assets"
    )
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        choices=["tilesets", "fonts", "sounds", "models", "all"],
        default=["all"],
        help="Asset types to optimize",
    )
    parser.add_argument(
        "--output", default=None, help="Output file for optimization results (JSON)"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only summary, not full JSON output",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be optimized without actually doing it",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Determine which asset types to optimize
    if args.assets == ["all"]:
        asset_types = ["tilesets", "fonts", "sounds", "models"]
    else:
        asset_types = args.assets

    if args.dry_run:
        print("RUNNING IN DRY-RUN MODE - No assets will be actually optimized")
        print(f"Would optimize asset types: {', '.join(asset_types)}")
        sys.exit(0)

    # Run optimization pass
    results = run_optimization_pass(config, asset_types)

    # Save or output results
    if args.output and not save_optimization_results(results, args.output):
        sys.exit(1)

    if not args.summary_only:
        # Print full JSON
        print(json.dumps(results, indent=2))
    else:
        # Print formatted summary
        print_optimization_summary(results, verbose=args.verbose)

    sys.exit(0)


if __name__ == "__main__":
    main()
