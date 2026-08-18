#!/usr/bin/env python3
"""Deploy script for naRou project."""
import os
import sys
import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0

def deploy(environment="production"):
    """Deploy the project."""
    print(f"Deploying naRou to {environment}...")
    
    # Verify build artifacts exist
    if not os.path.exists("dist"):
        print("Error: No dist directory found. Run build.py first.")
        return False
    
    # Deploy based on environment
    if environment == "production":
        print("Deploying to production...")
        # Add production deployment logic here
        pass
    elif environment == "staging":
        print("Deploying to staging...")
        # Add staging deployment logic here
        pass
    else:
        print(f"Unknown environment: {environment}")
        return False
    
    print("Deployment completed successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy naRou")
    parser.add_argument("--env", default="production", help="Target environment")
    args = parser.parse_args()
    
    success = deploy(args.env)
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
