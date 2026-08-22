#!/usr/bin/env python3
"""Install script for naRou project."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def install(package_path=None, dev=False):
    """Install the project."""
    print("Installing naRou...")

    if package_path:
        # Install from package
        if not run_command(f"pip install {package_path}"):
            return False
    else:
        # Install in development mode
        if dev:
            if not run_command("pip install -e .[dev]"):
                return False
        else:
            if not run_command("pip install -e ."):
                return False

    print("Installation completed successfully!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install naRou")
    parser.add_argument("--package", help="Path to package file")
    parser.add_argument("--dev", action="store_true", help="Install in development mode")
    args = parser.parse_args()

    success = install(args.package, args.dev)
    sys.exit(0 if success else 1)
