#!/usr/bin/env python3
"""Validation script for naRou project."""

from __future__ import annotations

import argparse
import subprocess
import sys


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def validate_code():
    """Validate code quality."""
    print("Validating code...")

    # Run mypy
    if not run_command("mypy ."):
        print("Type checking failed")
        return False

    # Run ruff
    if not run_command("ruff check ."):
        print("Linting failed")
        return False

    # Run black check
    if not run_command("black --check ."):
        print("Formatting check failed")
        return False

    return True


def validate_tests():
    """Validate tests pass."""
    print("Validating tests...")

    if not run_command("pytest -v"):
        print("Tests failed")
        return False

    return True


def validate_balance():
    """Validate game balance."""
    print("Validating balance...")

    if not run_command("python tests/balance_simulator.py"):
        print("Balance validation failed")
        return False

    return True


def validate_all():
    """Run all validations."""
    print("Running all validations...")

    checks = [
        ("Code Quality", validate_code),
        ("Tests", validate_tests),
        ("Balance", validate_balance),
    ]

    all_passed = True
    for name, check in checks:
        print(f"\n=== {name} ===")
        if not check():
            print(f"{name} validation FAILED")
            all_passed = False
        else:
            print(f"{name} validation PASSED")

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate naRou")
    parser.add_argument("--code", action="store_true", help="Validate code only")
    parser.add_argument("--tests", action="store_true", help="Validate tests only")
    parser.add_argument("--balance", action="store_true", help="Validate balance only")
    args = parser.parse_args()

    if args.code:
        success = validate_code()
    elif args.tests:
        success = validate_tests()
    elif args.balance:
        success = validate_balance()
    else:
        success = validate_all()

    print(f"\nOverall: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
