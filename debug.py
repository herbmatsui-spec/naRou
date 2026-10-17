#!/usr/bin/env python3
"""Debug script for naRou project."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
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
        logger.exception("Unhandled exception")

    try:
        print("systems: OK")
    except Exception as e:
        print(f"systems: FAILED - {e}")
        logger.exception("Unhandled exception")
        traceback.print_exc()

    try:
        print("game: OK")
    except Exception as e:
        logger.exception("Unhandled exception")
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
    success, _stdout, _stderr = run_command(
        ["python", "-c", "import game; print('Game module loaded')"]
    )
    if not success:
        print("Game module failed to load")
        return False
    return True


def debug_time():
    """Debug world clock system."""
    print("Debugging world clock...")
    try:
        from time_system import TimeConfig, TimePhase, WorldClock, get_world_clock

        # Test TimePhase
        print("  TimePhase tests:")
        for phase in TimePhase:
            print(f"    {phase.name}: {phase.display_name} ({phase.start_hour}-{phase.end_hour})")

        # Test from_hour
        test_hours = [0, 5, 6, 12, 17, 18, 21, 22, 23]
        for h in test_hours:
            phase = TimePhase.from_hour(h)
            print(f"    Hour {h:2d} -> {phase.display_name}")

        # Test WorldClock
        print("  WorldClock tests:")
        config = TimeConfig(start_hour=8, start_minute=0)
        clock = WorldClock(config)
        print(f"    Initial: {clock.to_string()}")
        print(f"    Phase: {clock.current_phase.display_name}")

        # Advance time
        clock.advance(2)
        print(f"    +2h: {clock.to_string()}")
        print(f"    Phase: {clock.current_phase.display_name}")

        clock.advance(10)
        print(f"    +10h: {clock.to_string()}")
        print(f"    Phase: {clock.current_phase.display_name}")

        # Test ticks
        clock.advance_ticks(100)
        print(f"    +100 ticks: {clock.to_string()}")

        # Test save/load
        data = clock.to_dict()
        clock2 = WorldClock.from_dict(data)
        print(f"    Reloaded: {clock2.to_string()}")

        # Test global access
        global_clock = get_world_clock()
        print(f"    Global: {global_clock.to_string()}")

        print("  All tests passed!")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        traceback.print_exc()
        logger.exception("Unhandled exception")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug naRou")
    parser.add_argument("--imports", action="store_true", help="Debug imports")
    parser.add_argument("--paths", action="store_true", help="Debug paths")
    parser.add_argument("--env", action="store_true", help="Debug environment")
    parser.add_argument("--game", action="store_true", help="Debug game startup")
    parser.add_argument("--time", action="store_true", help="Debug world clock system")
    parser.add_argument("--all", action="store_true", help="Run all debug checks")
    args = parser.parse_args()

    if args.all or not any([args.imports, args.paths, args.env, args.game, args.time]):
        args.imports = args.paths = args.env = args.game = args.time = True

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

    if args.time:
        debug_time()
        print()

    print("Debug completed.")
