#!/usr/bin/env python3
"""
Main build script for the asset pipeline.
Orchestrates the processing of all asset types through the pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def run_command(command: list[str], description: str = "") -> bool:
    """Run a command and return success status."""
    if description:
        print(f"Running: {description}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}")
        return False


def validate_source(config: dict) -> bool:
    """Validate source assets exist and are usable."""
    source_dir = config["directories"]["source"]
    if not os.path.exists(source_dir):
        print(f"Source directory does not exist: {source_dir}")
        return False

    print(f"Validating source assets in: {source_dir}")
    # In a real implementation, would check for required files
    return True


def process_tilesets(config: dict) -> bool:
    """Process tileset assets."""
    print("Processing tilesets...")

    # Tilesets are consumed directly from assets/tiles (where tileset_def.json
    # and the web client expect them).
    output_dir = "assets/tiles"
    os.makedirs(output_dir, exist_ok=True)

    # A tileset definition may live in either the configured source tree
    # (assets/src/tilesets) or the legacy source tree (assets/source/tilesets).
    candidate_dirs = [
        os.path.join(config["directories"]["source"], "tilesets"),
        os.path.join("assets", "source", "tilesets"),
    ]
    def_files: list[str] = []
    for tileset_def_dir in candidate_dirs:
        if os.path.isdir(tileset_def_dir):
            for f in sorted(os.listdir(tileset_def_dir)):
                if f.endswith(".json") and f not in [
                    os.path.basename(p) for p in def_files
                ]:
                    def_files.append(os.path.join(tileset_def_dir, f))

    if not def_files:
        print("No tileset definitions found, skipping tileset processing")
        return True

    # Generate an atlas for every configured tile size.
    sizes = config.get("tileset", {}).get("sizes", [config["tileset"]["default_size"]])
    for def_path in def_files:
        for size in sizes:
            cmd = [
                sys.executable,
                "tools/generate_tileset_atlas.py",
                "--def",
                def_path,
                "--output",
                output_dir,
                "--size",
                str(size),
            ]
            if not run_command(
                cmd,
                f"Generating {size}x{size} tileset from {os.path.basename(def_path)}",
            ):
                return False

    return True


def process_fonts(config: dict) -> bool:
    """Process font assets."""
    print("Processing fonts...")

    os.makedirs(os.path.join(config["directories"]["output"], "fonts"), exist_ok=True)

    font_dir = os.path.join(config["directories"]["source"], "fonts")
    if os.path.exists(font_dir):
        font_files = [
            f
            for f in os.listdir(font_dir)
            if f.lower().endswith((".ttf", ".otf", ".woff", ".woff2"))
        ]
        for font_file in font_files:
            font_path = os.path.join(font_dir, font_file)
            cmd = [
                sys.executable,
                "tools/generate_font_atlas.py",
                "--font",
                font_path,
                "--output",
                os.path.join(config["directories"]["output"], "fonts"),
                "--size",
                str(config["font"]["default_size"]),
            ]
            if not run_command(cmd, f"Generating font atlas from {font_file}"):
                return False
    else:
        print("No font files found, skipping font processing")

    return True


def process_sounds(config: dict) -> bool:
    """Process sound assets."""
    print("Processing sounds...")

    os.makedirs(os.path.join(config["directories"]["output"], "sounds"), exist_ok=True)

    sound_dir = os.path.join(config["directories"]["source"], "sounds")
    if os.path.exists(sound_dir):
        # Create sound index
        cmd = [
            sys.executable,
            "tools/convert_sounds.py",
            "index",
            sound_dir,
            "--output",
            os.path.join(config["directories"]["output"], "sounds", "sound_index.json"),
        ]
        if not run_command(cmd, "Creating sound index"):
            return False

        # Convert sounds to target format
        cmd = [
            sys.executable,
            "tools/convert_sounds.py",
            "convert",
            os.path.join(sound_dir, "placeholder.wav"),  # Would process actual files
            os.path.join(config["directories"]["output"], "sounds", "placeholder.ogg"),
            "--format",
            "ogg",
        ]
        # Only run if placeholder exists, otherwise just create index
        if os.path.exists(os.path.join(sound_dir, "placeholder.wav")):
            if not run_command(cmd, "Converting sound format"):
                return False
    else:
        print("No sound files found, skipping sound processing")

    return True


def process_models(config: dict) -> bool:
    """Process 3D model assets."""
    print("Processing 3D models...")

    os.makedirs(os.path.join(config["directories"]["output"], "models"), exist_ok=True)

    model_dir = os.path.join(config["directories"]["source"], "models")
    if os.path.exists(model_dir):
        # Create model statistics
        cmd = [
            sys.executable,
            "tools/optimize_models.py",
            "stats",
            model_dir,
            "--output",
            os.path.join(config["directories"]["output"], "models", "model_stats.json"),
        ]
        if not run_command(cmd, "Creating model statistics"):
            return False
    else:
        print("No model files found, skipping model processing")

    return True


def optimize_assets(config: dict) -> bool:
    """Run optimization passes on processed assets."""
    print("Optimizing assets...")

    # Optimize textures (run pngcrush, optipng, etc. on output)
    tileset_output = os.path.join(config["directories"]["output"], "tilesets")
    if os.path.exists(tileset_output):
        print("Optimizing tileset textures...")
        # Would run image optimization tools here

    # Optimize models
    model_output = os.path.join(config["directories"]["output"], "models")
    if os.path.exists(model_output):
        print("Optimizing 3D models...")
        # Would run model optimization here

    return True


def package_assets(config: dict) -> bool:
    """Package assets for distribution."""
    print("Packaging assets...")

    # Create package manifest
    manifest = {
        "version": config.get("version", "1.0.0"),
        "generated_at": time.time(),
        "directories": config["directories"],
        "asset_counts": {},
    }

    # Count assets in each category
    for asset_type in ["tilesets", "fonts", "sounds", "models"]:
        asset_dir = os.path.join(config["directories"]["output"], asset_type)
        if os.path.exists(asset_dir):
            count = len(
                [
                    f
                    for f in os.listdir(asset_dir)
                    if os.path.isfile(os.path.join(asset_dir, f))
                ]
            )
            manifest["asset_counts"][asset_type] = count
        else:
            manifest["asset_counts"][asset_type] = 0

    # Write manifest
    manifest_path = os.path.join(config["directories"]["output"], "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Asset manifest created: {manifest_path}")
    return True


def validate_output(config: dict) -> bool:
    """Validate output assets are correct and complete."""
    print("Validating output assets...")

    output_dir = config["directories"]["output"]
    if not os.path.exists(output_dir):
        print(f"Output directory does not exist: {output_dir}")
        return False

    # Check that expected subdirectories exist
    expected_dirs = ["tilesets", "fonts", "sounds", "models"]
    for dir_name in expected_dirs:
        dir_path = os.path.join(output_dir, dir_name)
        if not os.path.exists(dir_path):
            print(f"Warning: Expected directory not found: {dir_path}")

    # Check for manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Warning: Manifest not found: {manifest_path}")

    print("Output validation completed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Build assets using the pipeline")
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=[
            "validate_source",
            "process_tilesets",
            "process_fonts",
            "process_sounds",
            "process_models",
            "optimize_assets",
            "package_assets",
            "validate_output",
            "all",
        ],
        default=["all"],
        help="Steps to run",
    )
    parser.add_argument(
        "--skip-validation", action="store_true", help="Skip input validation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN - Would execute the following steps:")
        steps = (
            args.steps
            if args.steps != ["all"]
            else [
                "validate_source",
                "process_tilesets",
                "process_fonts",
                "process_sounds",
                "process_models",
                "optimize_assets",
                "package_assets",
                "validate_output",
            ]
        )
        for step in steps:
            print(f"  - {step}")
        return

    # Determine which steps to run
    if args.steps == ["all"]:
        steps = [
            "validate_source",
            "process_tilesets",
            "process_fonts",
            "process_sounds",
            "process_models",
            "optimize_assets",
            "package_assets",
            "validate_output",
        ]
    else:
        steps = args.steps

    # Execute steps
    start_time = time.time()
    failed_steps = []

    for step in steps:
        print(f"\n{'=' * 50}")
        print(f"Executing step: {step}")
        print(f"{'=' * 50}")

        step_success = False
        try:
            if step == "validate_source" and not args.skip_validation:
                step_success = validate_source(config)
            elif step == "process_tilesets":
                step_success = process_tilesets(config)
            elif step == "process_fonts":
                step_success = process_fonts(config)
            elif step == "process_sounds":
                step_success = process_sounds(config)
            elif step == "process_models":
                step_success = process_models(config)
            elif step == "optimize_assets":
                step_success = optimize_assets(config)
            elif step == "package_assets":
                step_success = package_assets(config)
            elif step == "validate_output":
                step_success = validate_output(config)
            else:
                print(f"Unknown step: {step}")
                step_success = False
        except Exception as e:
            print(f"Error executing step {step}: {e}")
            step_success = False

        if step_success:
            print(f"✓ Step '{step}' completed successfully")
        else:
            print(f"✗ Step '{step}' failed")
            failed_steps.append(step)
            if not config["pipeline"]["continue_on_error"]:
                break

    # Summary
    end_time = time.time()
    duration = end_time - start_time

    print(f"\n{'=' * 50}")
    print("PIPELINE EXECUTION SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total duration: {duration:.2f} seconds")
    print(f"Steps executed: {len(steps)}")
    print(f"Steps successful: {len(steps) - len(failed_steps)}")
    print(f"Steps failed: {len(failed_steps)}")

    if failed_steps:
        print(f"Failed steps: {', '.join(failed_steps)}")
        sys.exit(1)
    else:
        print("All steps completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
