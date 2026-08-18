#!/usr/bin/env python3
"""Package script for naRou project."""
import os
import sys
import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0

def package():
    """Package the project."""
    print("Packaging naRou...")
    
    # Create package directory
    os.makedirs("package", exist_ok=True)
    
    # Copy build artifacts
    if os.path.exists("dist"):
        run_command("cp -r dist/* package/")
    
    # Create package metadata
    with open("package/MANIFEST.txt", "w") as f:
        f.write("naRou Package\n")
        f.write("=============\n")
        for file in os.listdir("package"):
            f.write(f"- {file}\n")
    
    print("Packaging completed successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package naRou")
    args = parser.parse_args()
    
    success = package()
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
