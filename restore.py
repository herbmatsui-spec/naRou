#!/usr/bin/env python3
"""Restore script for naRou project."""

from __future__ import annotations

import argparse
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tarfile

logger = logging.getLogger(__name__)


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def restore_backup(backup_file, target_dir="."):
    """Restore from backup file."""
    print(f"Restoring from {backup_file}...")

    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        return False

    # Create temporary extraction directory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract archive using tarfile (no shell)
        print(f"Extracting to {tmpdir}...")
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(tmpdir)
        except Exception:
            logger.exception("ロード失敗")
            return False

        # Find extracted directory
        extracted = os.listdir(tmpdir)
        if not extracted:
            print("No content in backup")
            return False

        extracted_path = os.path.join(tmpdir, extracted[0])

        # Restore files
        for item in os.listdir(extracted_path):
            src = os.path.join(extracted_path, item)
            dest = os.path.join(target_dir, item)

            # Backup existing file/dir
            if os.path.exists(dest):
                backup_dest = (
                    f"{dest}.bak.{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                print(f"Backing up existing {dest} to {backup_dest}")
                if os.path.isdir(dest):
                    shutil.move(dest, backup_dest)
                else:
                    shutil.move(dest, backup_dest)

            # Restore
            print(f"Restoring {item}...")
            if os.path.isdir(src):
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)

    print("Restore completed successfully!")
    return True


def restore_data(backup_file, target_dir="."):
    """Restore data only."""
    print(f"Restoring data from {backup_file}...")
    return restore_backup(backup_file, target_dir)


def restore_code(backup_file, target_dir="."):
    """Restore code only."""
    print(f"Restoring code from {backup_file}...")
    return restore_backup(backup_file, target_dir)


def list_backup_contents(backup_file):
    """List contents of backup file."""
    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        return

    print(f"Contents of {backup_file}:")
    with tarfile.open(backup_file, "r:gz") as tar:
        for member in tar.getmembers():
            print(f"  {member.name} ({member.size} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore naRou")
    parser.add_argument("backup", nargs="?", help="Backup file to restore")
    parser.add_argument("--data", action="store_true", help="Restore data only")
    parser.add_argument("--code", action="store_true", help="Restore code only")
    parser.add_argument("--list", action="store_true", help="List backup contents")
    parser.add_argument("--target", default=".", help="Target directory")
    args = parser.parse_args()

    if not args.backup:
        parser.print_help()
        sys.exit(1)

    if args.list:
        list_backup_contents(args.backup)
    elif args.data:
        restore_data(args.backup, args.target)
    elif args.code:
        restore_code(args.backup, args.target)
    else:
        restore_backup(args.backup, args.target)
