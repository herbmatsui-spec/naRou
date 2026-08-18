#!/usr/bin/env python3
"""Downgrade script for naRou project."""
import os
import sys
import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def downgrade_dependencies(target_version=None):
    """Downgrade dependencies."""
    print("Downgrading dependencies...")
    
    if target_version:
        # Downgrade to specific version
        run_command(f"pip install -r requirements.txt=={target_version}")
    else:
        # Use pip-tools to sync to older versions
        run_command("pip install pip-tools")
        if os.path.exists("requirements.in"):
            run_command("pip-sync requirements.txt")
    
    print("Dependencies downgraded!")

def downgrade_git(target_commit=None, target_tag=None):
    """Downgrade git repository."""
    print("Downgrading git repository...")
    
    if target_tag:
        run_command(f"git checkout {target_tag}")
    elif target_commit:
        run_command(f"git checkout {target_commit}")
    else:
        # Go back one commit
        run_command("git checkout HEAD~1")
    
    print("Git repository downgraded!")

def downgrade_config():
    """Downgrade configuration."""
    print("Downgrading configuration...")
    
    # Restore config from backup
    if os.path.exists("config.yaml.bak"):
        import shutil
        shutil.copy2("config.yaml.bak", "config.yaml")
        print("Configuration restored from backup")
    else:
        print("No config backup found")
    
    print("Configuration downgraded!")

def downgrade_data():
    """Downgrade game data."""
    print("Downgrading game data...")
    
    # Restore from backup
    run_command("python restore.py --data backups/latest_data_backup.tar.gz")
    
    print("Data downgraded!")

def downgrade_all():
    """Run all downgrades."""
    print("Downgrading naRou...")
    
    downgrades = [
        ("Dependencies", downgrade_dependencies),
        ("Git Repository", downgrade_git),
        ("Configuration", downgrade_config),
        ("Data", downgrade_data),
    ]
    
    for name, downgrade in downgrades:
        print(f"\n=== {name} ===")
        downgrade()
    
    print("\nAll downgrades completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downgrade naRou")
    parser.add_argument("--deps", action="store_true", help="Downgrade dependencies")
    parser.add_argument("--git", action="store_true", help="Downgrade git")
    parser.add_argument("--config", action="store_true", help="Downgrade config")
    parser.add_argument("--data", action="store_true", help="Downgrade data")
    parser.add_argument("--version", help="Target version for dependencies")
    parser.add_argument("--commit", help="Target commit for git")
    parser.add_argument("--tag", help="Target tag for git")
    parser.add_argument("--all", action="store_true", help="Run all downgrades")
    args = parser.parse_args()
    
    if args.all or not any([args.deps, args.git, args.config, args.data]):
        downgrade_all()
    else:
        if args.deps:
            downgrade_dependencies(args.version)
        if args.git:
            downgrade_git(args.commit, args.tag)
        if args.config:
            downgrade_config()
        if args.data:
            downgrade_data()