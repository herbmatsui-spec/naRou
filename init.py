#!/usr/bin/env python3
"""Initialization script for naRou project."""

import argparse
import os
import subprocess
import sys
import shlex


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def init_project():
    """Initialize the project."""
    print("Initializing naRou...")

    # Create necessary directories
    dirs = [
        "data",
        "logs",
        "saves",
        "config",
        "cache",
        "tests/data",
        "tests/reports",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}")

    # Create default config if not exists
    if not os.path.exists("config.yaml"):
        default_config = {
            "game": {
                "title": "naRou",
                "version": "1.0.0",
                "fullscreen": False,
                "resolution": [1280, 720],
            },
            "audio": {
                "master_volume": 0.8,
                "music_volume": 0.7,
                "sfx_volume": 0.8,
            },
            "graphics": {
                "vsync": True,
                "fps_limit": 60,
            },
        }
        import yaml

        with open("config.yaml", "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print("Created default config.yaml")

    # Initialize git hooks if in git repo
    if os.path.exists(".git"):
        if not run_command("git config core.hooksPath .githooks"):
            print("Note: Could not set git hooks path")

    print("Initialization completed successfully!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize naRou")
    args = parser.parse_args()

    success = init_project()
    sys.exit(0 if success else 1)