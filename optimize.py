#!/usr/bin/env python3
"""Optimization script for naRou project."""

import argparse
import os
import subprocess
import sys
import shlex


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


def optimize_dependencies():
    """Optimize dependencies."""
    print("Optimizing dependencies...")

    # Update pip
    run_command("pip install --upgrade pip")

    # Install pip-tools for dependency management
    run_command("pip install pip-tools")

    # Compile requirements
    if os.path.exists("requirements.in"):
        run_command("pip-compile requirements.in -o requirements.txt")
    else:
        # Generate requirements.in from current environment
        run_command("pip freeze > requirements.in")
        run_command("pip-compile requirements.in -o requirements.txt")

    print("Dependencies optimized!")


def optimize_code():
    """Optimize code formatting and imports."""
    print("Optimizing code...")

    # Run black
    run_command("black .")

    # Run ruff with fix
    run_command("ruff check . --fix")

    # Sort imports with isort (if available)
    run_command("pip install isort")
    run_command("isort .")

    print("Code optimized!")


def optimize_build():
    """Optimize build process."""
    print("Optimizing build...")

    # Clean build artifacts
    import shutil
    for pattern in ["dist", "build", "*.egg-info", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]:
        for path in __import__("glob").glob(pattern, recursive=True):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                print(f"Removed: {path}")
            elif os.path.isfile(path):
                os.remove(path)
                print(f"Removed: {path}")

    # Rebuild
    run_command("pip install build")
    run_command("python -m build")

    print("Build optimized!")


def optimize_tests():
    """Optimize test performance."""
    print("Optimizing tests...")

    # Run tests with parallel execution
    run_command("pip install pytest-xdist")
    run_command("pytest -n auto --tb=short")

    print("Tests optimized!")


def optimize_all():
    """Run all optimizations."""
    print("Running all optimizations...")

    optimizations = [
        ("Dependencies", optimize_dependencies),
        ("Code", optimize_code),
        ("Build", optimize_build),
        ("Tests", optimize_tests),
    ]

    for name, opt in optimizations:
        print(f"\n=== {name} ===")
        opt()

    print("\nAll optimizations completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize naRou")
    parser.add_argument("--deps", action="store_true", help="Optimize dependencies")
    parser.add_argument("--code", action="store_true", help="Optimize code")
    parser.add_argument("--build", action="store_true", help="Optimize build")
    parser.add_argument("--tests", action="store_true", help="Optimize tests")
    parser.add_argument("--all", action="store_true", help="Run all optimizations")
    args = parser.parse_args()

    if args.all or not any([args.deps, args.code, args.build, args.tests]):
        optimize_all()
    else:
        if args.deps:
            optimize_dependencies()
        if args.code:
            optimize_code()
        if args.build:
            optimize_build()
        if args.tests:
            optimize_tests()