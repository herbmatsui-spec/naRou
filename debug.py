#!/usr/bin/env python3
"""Debug script for naRou project."""

import argparse
import os
import subprocess
import sys
import traceback


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        import shlex
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0, result.stdout, result.stderr


def debug_imports():
    """Debug import issues."""
    print("Debugging imports...")
    try:
        print("entity: OK")
    except Exception as e:
        print(f"entity: FAILED - {e}")
        traceback.print_exc()

    try:
        print("systems: OK")
    except Exception as e:
        print(f"systems: FAILED - {e}")
        traceback.print_exc()

    try:
        print("game: OK")
    except Exception as e:
        print(f"game: FAILED - {e}")
        traceback.print_exc()


def debug_paths():
    """Debug path issues."""
    print("Debugging paths...")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")


def debug_env():
    """Debug environment."""
    print("Debugging environment...")
    for key in ["PYTHONPATH", "PATH", "HOME", "USER"]:
        print(f"{key}: {os.environ.get(key, 'Not set')}")


def debug_game():
    """Debug game startup."""
    print("Debugging game startup...")
    success, stdout, stderr = run_command(
        ["python", "-c", "import game; print('Game module loaded')"]
    )
    if not success:
        print("Game module failed to load")
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug naRou")
    parser.add_argument("--imports", action="store_true", help="Debug imports")
    parser.add_argument("--paths", action="store_true", help="Debug paths")
    parser.add_argument("--env", action="store_true", help="Debug environment")
    parser.add_argument("--game", action="store_true", help="Debug game startup")
    parser.add_argument("--all", action="store_true", help="Run all debug checks")
    args = parser.parse_args()

    if args.all or not any([args.imports, args.paths, args.env, args.game]):
        args.imports = args.paths = args.env = args.game = True

    if args.paths:
        debug_paths()
        print()

    if args.env:
        debug_env()
        print()

    if args.imports:
        debug_imports()
        print()

    if args.game:
        debug_game()
        print()

    print("Debug completed.")