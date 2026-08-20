#!/usr/bin/env python3
"""Backup script for naRou project."""

import argparse
import os
import shutil
import subprocess
import tarfile
from datetime import datetime


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        import shlex
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def backup_data(backup_dir="backups"):
    """Backup game data."""
    print("Backing up data...")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"data_backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)

    # Directories to backup
    dirs_to_backup = ["data", "saves", "config.yaml", "logs"]

    os.makedirs(backup_path, exist_ok=True)

    for item in dirs_to_backup:
        if os.path.exists(item):
            dest = os.path.join(backup_path, os.path.basename(item))
            if os.path.isdir(item):
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            print(f"Backed up: {item}")

    # Create archive using tarfile (no shell needed)
    archive_path = f"{backup_path}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(backup_path, arcname=backup_name)
    shutil.rmtree(backup_path)

    print(f"Backup created: {archive_path}")
    return True


def backup_code(backup_dir="backups"):
    """Backup source code."""
    print("Backing up source code...")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"code_backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)

    # Directories/files to backup
    items_to_backup = [
        "*.py",
        "*.yaml",
        "*.yml",
        "*.md",
        "*.txt",
        "requirements.txt",
        "pyproject.toml",
        "tests/",
        ".github/",
    ]

    os.makedirs(backup_path, exist_ok=True)

    import glob
    for pattern in items_to_backup:
        for item in glob.glob(pattern):
            if os.path.exists(item):
                dest = os.path.join(backup_path, item)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.isdir(item):
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                print(f"Backed up: {item}")

    # Create archive using tarfile (no shell needed)
    archive_path = f"{backup_path}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(backup_path, arcname=backup_name)
    shutil.rmtree(backup_path)

    print(f"Code backup created: {archive_path}")
    return True


def list_backups(backup_dir="backups"):
    """List available backups."""
    if not os.path.exists(backup_dir):
        print("No backups directory found")
        return

    backups = sorted(os.listdir(backup_dir), reverse=True)
    print("Available backups:")
    for backup in backups:
        path = os.path.join(backup_dir, backup)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        print(f"  {backup} ({size} bytes, {mtime})")


def cleanup_backups(backup_dir="backups", keep=10):
    """Clean up old backups."""
    if not os.path.exists(backup_dir):
        return

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")],
        key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
        reverse=True,
    )

    for backup in backups[keep:]:
        path = os.path.join(backup_dir, backup)
        os.remove(path)
        print(f"Removed old backup: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup naRou")
    parser.add_argument("--data", action="store_true", help="Backup data")
    parser.add_argument("--code", action="store_true", help="Backup code")
    parser.add_argument("--all", action="store_true", help="Backup everything")
    parser.add_argument("--list", action="store_true", help="List backups")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old backups")
    parser.add_argument(
        "--keep", type=int, default=10, help="Number of backups to keep"
    )
    parser.add_argument("--dir", default="backups", help="Backup directory")
    args = parser.parse_args()

    if args.list:
        list_backups(args.dir)
    elif args.cleanup:
        cleanup_backups(args.dir, args.keep)
    elif args.data:
        backup_data(args.dir)
    elif args.code:
        backup_code(args.dir)
    elif args.all:
        backup_data(args.dir)
        backup_code(args.dir)
    else:
        parser.print_help()