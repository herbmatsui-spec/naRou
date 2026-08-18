#!/usr/bin/env python3
"""Upgrade script for naRou project."""
import os
import sys
import subprocess
import argparse
import json

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def check_version():
    """Check current version."""
    version = "1.0.0"
    if os.path.exists("pyproject.toml"):
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            version = data.get("project", {}).get("version", "1.0.0")
    return version

def upgrade_dependencies():
    """Upgrade all dependencies."""
    print("Upgrading dependencies...")
    
    # Upgrade pip
    run_command("pip install --upgrade pip")
    
    # Upgrade setuptools and wheel
    run_command("pip install --upgrade setuptools wheel")
    
    # Upgrade requirements
    run_command("pip install -r requirements.txt --upgrade")
    
    # Upgrade dev dependencies
    run_command("pip install -e .[dev] --upgrade")
    
    print("Dependencies upgraded!")

def upgrade_python():
    """Upgrade Python version (informational)."""
    print("Checking Python version...")
    print(f"Current Python: {sys.version}")
    print("Note: Python upgrade requires system-level changes")

def upgrade_git():
    """Upgrade git repository."""
    print("Upgrading git repository...")
    
    # Fetch latest
    run_command("git fetch --all --prune")
    
    # Check for updates
    run_command("git status")
    
    print("Git repository updated!")

def upgrade_config():
    """Upgrade configuration files."""
    print("Upgrading configuration...")
    
    # Check for config.yaml
    if not os.path.exists("config.yaml"):
        print("No config.yaml found, creating default...")
        run_command("python init.py")
    
    print("Configuration upgraded!")

def upgrade_data():
    """Upgrade game data."""
    print("Upgrading game data...")
    
    # Run data migration scripts if any
    migrations_dir = "migrations"
    if os.path.exists(migrations_dir):
        for migration in sorted(os.listdir(migrations_dir)):
            if migration.endswith(".py"):
                print(f"Running migration: {migration}")
                run_command(f"python {os.path.join(migrations_dir, migration)}")
    
    print("Data upgraded!")

def upgrade_all():
    """Run all upgrades."""
    print(f"Upgrading naRou from version {check_version()}...")
    
    upgrades = [
        ("Git Repository", upgrade_git),
        ("Dependencies", upgrade_dependencies),
        ("Configuration", upgrade_config),
        ("Data", upgrade_data),
    ]
    
    for name, upgrade in upgrades:
        print(f"\n=== {name} ===")
        upgrade()
    
    print("\nAll upgrades completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upgrade naRou")
    parser.add_argument("--deps", action="store_true", help="Upgrade dependencies")
    parser.add_argument("--git", action="store_true", help="Upgrade git")
    parser.add_argument("--config", action="store_true", help="Upgrade config")
    parser.add_argument("--data", action="store_true", help="Upgrade data")
    parser.add_argument("--all", action="store_true", help="Run all upgrades")
    args = parser.parse_args()
    
    if args.all or not any([args.deps, args.git, args.config, args.data]):
        upgrade_all()
    else:
        if args.git:
            upgrade_git()
        if args.deps:
            upgrade_dependencies()
        if args.config:
            upgrade_config()
        if args.data:
            upgrade_data()