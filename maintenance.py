#!/usr/bin/env python3
"""Maintenance script for naRou project."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime, timedelta


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def clean_cache():
    """Clean cache directories."""
    print("Cleaning cache...")

    cache_dirs = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        ".tox",
        "dist",
        "build",
        "*.egg-info",
    ]

    for pattern in cache_dirs:
        for path in __import__("glob").glob(pattern, recursive=True):
            if os.path.isdir(path):
                __import__("shutil").rmtree(path)
                print(f"Removed: {path}")
            elif os.path.isfile(path):
                os.remove(path)
                print(f"Removed: {path}")


def clean_logs(days=30):
    """Clean old log files."""
    print(f"Cleaning logs older than {days} days...")

    log_dirs = ["logs", "tests/reports"]
    cutoff = datetime.now() - timedelta(days=days)

    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        os.remove(filepath)
                        print(f"Removed old log: {filepath}")


def clean_backups(keep=10):
    """Clean old backups."""
    print(f"Cleaning old backups (keeping {keep})...")

    backup_dir = "backups"
    if os.path.exists(backup_dir):
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")],
            key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
            reverse=True,
        )

        for backup in backups[keep:]:
            path = os.path.join(backup_dir, backup)
            os.remove(path)
            print(f"Removed old backup: {backup}")


def update_dependencies():
    """Update dependencies."""
    print("Updating dependencies...")

    run_command("pip install --upgrade pip")
    run_command("pip install -r requirements.txt --upgrade")
    run_command("pip install -e .[dev] --upgrade")


def check_health():
    """Check project health."""
    print("Checking project health...")

    # Check git status
    run_command("git status")

    # Check for uncommitted changes
    success, stdout, _ = run_command("git status --porcelain")
    if success and stdout.strip():
        print("Warning: Uncommitted changes detected")

    # Run tests
    run_command("pytest -x -q")

    # Check code quality
    run_command("mypy .")
    run_command("ruff check .")
    run_command("black --check .")


def maintenance_all():
    """Run all maintenance tasks."""
    print("Running all maintenance tasks...")

    tasks = [
        ("Clean Cache", clean_cache),
        ("Clean Logs", lambda: clean_logs(30)),
        ("Clean Backups", lambda: clean_backups(10)),
        ("Update Dependencies", update_dependencies),
        ("Health Check", check_health),
    ]

    for name, task in tasks:
        print(f"\n=== {name} ===")
        task()

    print("\nAll maintenance tasks completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maintain naRou")
    parser.add_argument("--cache", action="store_true", help="Clean cache")
    parser.add_argument("--logs", action="store_true", help="Clean logs")
    parser.add_argument("--backups", action="store_true", help="Clean backups")
    parser.add_argument("--update", action="store_true", help="Update dependencies")
    parser.add_argument("--health", action="store_true", help="Check health")
    parser.add_argument("--all", action="store_true", help="Run all maintenance")
    parser.add_argument("--days", type=int, default=30, help="Days to keep logs")
    parser.add_argument("--keep", type=int, default=10, help="Backups to keep")
    args = parser.parse_args()

    if args.all or not any([args.cache, args.logs, args.backups, args.update, args.health]):
        maintenance_all()
    else:
        if args.cache:
            clean_cache()
        if args.logs:
            clean_logs(args.days)
        if args.backups:
            clean_backups(args.keep)
        if args.update:
            update_dependencies()
        if args.health:
            check_health()
