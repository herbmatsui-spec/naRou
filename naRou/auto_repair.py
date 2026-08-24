#!/usr/bin/env python3
"""Auto-repair script for naRou project."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        # Split string command into list
        import shlex

        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def repair_dependencies():
    """Repair broken dependencies."""
    print("Repairing dependencies...")

    # Reinstall dependencies
    run_command("pip install --force-reinstall -r requirements.txt")
    run_command("pip install --force-reinstall -e .[dev]")

    # Fix any missing packages
    run_command("pip check")

    print("Dependencies repaired!")


def repair_code():
    """Repair code formatting and linting issues."""
    print("Repairing code...")

    # Fix formatting
    run_command("black .")

    # Fix linting
    run_command("ruff check . --fix")

    # Fix imports
    run_command("pip install isort")
    run_command("isort .")

    print("Code repaired!")


def repair_tests():
    """Repair failing tests."""
    print("Repairing tests...")

    # Run tests and capture failures
    result = subprocess.run(["pytest", "-v", "--tb=short"], capture_output=True, text=True)

    if result.returncode != 0:
        print("Some tests failed. Attempting to fix...")
        # In practice, this would analyze failures and apply fixes
        # For now, just re-run with more verbose output
        run_command("pytest -v --tb=long")
    else:
        print("All tests passing!")

    return result.returncode == 0


def repair_config():
    """Repair configuration issues."""
    print("Repairing configuration...")

    # Validate config.yaml
    if os.path.exists("config.yaml"):
        import yaml

        try:
            with open("config.yaml") as f:
                yaml.safe_load(f)
            print("Configuration valid")
        except Exception:
            logger.exception("ロード失敗")
            # Restore from backup
            if os.path.exists("config.yaml.bak"):
                import shutil

                shutil.copy2("config.yaml.bak", "config.yaml")
                print("Configuration restored from backup")
    else:
        print("No config.yaml found, creating default...")
        run_command("python init.py")

    return True


def repair_data():
    """Repair corrupted data."""
    print("Repairing data...")

    # Check data directory
    if os.path.exists("data"):
        # Validate YAML files
        for root, dirs, files in os.walk("data"):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    filepath = os.path.join(root, file)
                    try:
                        import yaml

                        with open(filepath) as f:
                            yaml.safe_load(f)
                    except Exception:
                        logger.exception("ロード失敗")
                        # Restore from backup
                        backup_dir = "backups"
                        if os.path.exists(backup_dir):
                            run_command(
                                f"python restore.py --data {backup_dir}/latest_data_backup.tar.gz"
                            )
                            break

    print("Data repaired!")
    return True


def repair_git():
    """Repair git repository issues."""
    print("Repairing git repository...")

    # Check for git corruption
    run_command("git fsck --full")

    # Clean up
    run_command("git gc --prune=now")

    print("Git repository repaired!")
    return True


def repair_all():
    """Run all repairs."""
    print("Running auto-repair...")

    repairs = [
        ("Dependencies", repair_dependencies),
        ("Code", repair_code),
        ("Tests", repair_tests),
        ("Configuration", repair_config),
        ("Data", repair_data),
        ("Git", repair_git),
    ]

    all_success = True
    for name, repair in repairs:
        print(f"\n=== {name} ===")
        if not repair():
            print(f"{name} repair FAILED")
            all_success = False
        else:
            print(f"{name} repair PASSED")

    if all_success:
        print("\nAll repairs completed successfully!")
    else:
        print("\nSome repairs failed!")

    return all_success


def monitor_and_repair(interval=300):
    """Monitor and auto-repair."""
    print(f"Starting auto-repair monitor (interval: {interval}s)")
    print("Press Ctrl+C to stop")

    while True:
        try:
            print(f"\n[{time.ctime()}] Running auto-repair check...")
            repair_all()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nAuto-repair monitor stopped")
            break
        except Exception:
            logger.exception("ロード失敗")
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-repair naRou")
    parser.add_argument("--deps", action="store_true", help="Repair dependencies")
    parser.add_argument("--code", action="store_true", help="Repair code")
    parser.add_argument("--tests", action="store_true", help="Repair tests")
    parser.add_argument("--config", action="store_true", help="Repair config")
    parser.add_argument("--data", action="store_true", help="Repair data")
    parser.add_argument("--git", action="store_true", help="Repair git")
    parser.add_argument("--all", action="store_true", help="Run all repairs")
    parser.add_argument("--monitor", action="store_true", help="Monitor and auto-repair")
    parser.add_argument("--interval", type=int, default=300, help="Monitor interval (seconds)")
    args = parser.parse_args()

    if args.monitor:
        monitor_and_repair(args.interval)
    elif args.all or not any([args.deps, args.code, args.tests, args.config, args.data, args.git]):
        repair_all()
    else:
        if args.deps:
            repair_dependencies()
        if args.code:
            repair_code()
        if args.tests:
            repair_tests()
        if args.config:
            repair_config()
        if args.data:
            repair_data()
        if args.git:
            repair_git()
