#!/usr/bin/env python3
"""Rollback script for naRou project."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys


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


def rollback_deployment(target_tag=None):
    """Rollback deployment to a specific tag."""
    print("Rolling back deployment...")

    if target_tag:
        # Checkout specific tag
        run_command("git fetch --tags")
        run_command(f"git checkout {target_tag}")
    else:
        # Rollback to previous tag
        run_command("git fetch --tags")
        _success, stdout, _ = run_command("git tag -l 'v*' --sort=-v:refname")
        tag_list = stdout.strip().split("\n")
        if len(tag_list) > 1:
            run_command(f"git checkout {tag_list[1]}")
        else:
            print("No previous tag found")
            return False

    # Rebuild and redeploy
    run_command("python build.py")
    run_command("python deploy.py")

    print("Deployment rolled back!")
    return True


def rollback_config():
    """Rollback configuration to previous version."""
    print("Rolling back configuration...")

    # Find config backups
    config_backups = sorted(
        [f for f in os.listdir(".") if f.startswith("config.yaml.bak.")], reverse=True
    )
    if config_backups:
        latest_backup = config_backups[0]
        shutil.copy2(latest_backup, "config.yaml")
        print(f"Configuration rolled back to {latest_backup}")
    else:
        print("No configuration backup found")
        return False

    return True


def rollback_data(target_backup=None):
    """Rollback game data."""
    print("Rolling back game data...")

    if target_backup:
        return run_command(f"python restore.py --data {target_backup}")
    else:
        # Find latest data backup
        backup_dir = "backups"
        if os.path.exists(backup_dir):
            data_backups = sorted(
                [
                    f
                    for f in os.listdir(backup_dir)
                    if f.startswith("data_backup_") and f.endswith(".tar.gz")
                ],
                reverse=True,
            )
            if data_backups:
                return run_command(
                    f"python restore.py --data {os.path.join(backup_dir, data_backups[0])}"
                )

    print("No data backup found")
    return False


def rollback_all():
    """Rollback everything."""
    print("Rolling back naRou...")

    rollbacks = [
        ("Deployment", rollback_deployment),
        ("Configuration", rollback_config),
        ("Data", rollback_data),
    ]

    all_success = True
    for name, rollback in rollbacks:
        print(f"\n=== {name} ===")
        if not rollback():
            print(f"{name} rollback FAILED")
            all_success = False

    if all_success:
        print("\nAll rollbacks completed successfully!")
    else:
        print("\nSome rollbacks failed!")

    return all_success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rollback naRou")
    parser.add_argument("--deploy", action="store_true", help="Rollback deployment")
    parser.add_argument("--config", action="store_true", help="Rollback config")
    parser.add_argument("--data", action="store_true", help="Rollback data")
    parser.add_argument("--tag", help="Target tag for deployment rollback")
    parser.add_argument("--backup", help="Target backup for data rollback")
    parser.add_argument("--all", action="store_true", help="Rollback everything")
    args = parser.parse_args()

    if args.all or not any([args.deploy, args.config, args.data]):
        rollback_all()
    else:
        if args.deploy:
            rollback_deployment(args.tag)
        if args.config:
            rollback_config()
        if args.data:
            rollback_data(args.backup)