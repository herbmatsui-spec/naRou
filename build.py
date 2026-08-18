#!/usr/bin/env python3
"""Build script for naRou project."""
import os
import sys
import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0

def build():
    """Build the project."""
    print("Building naRou...")
    
    # Clean previous builds
    run_command("rm -rf dist build *.egg-info")
    
    # Install build dependencies
    if not run_command("pip install build"):
        return False
    
    # Build the package
    if not run_command("python -m build"):
        return False
    
    print("Build completed successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build naRou")
    parser.add_argument("--clean", action="store_true", help="Clean before build")
    args = parser.parse_args()
    
    success = build()
    sys.exit(0 if success else 1)


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager
    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
