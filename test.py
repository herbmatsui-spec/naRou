#!/usr/bin/env python3
"""Test runner script for naRou project."""

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


def run_tests(test_type="all", coverage=False, verbose=False):
    """Run tests."""
    print(f"Running {test_type} tests...")

    cmd = ["pytest"]

    if verbose:
        cmd += ["-v"]

    if coverage:
        cmd += ["--cov=.", "--cov-report=term-missing", "--cov-report=html"]

    if test_type == "unit":
        cmd += ["tests/unit"]
    elif test_type == "integration":
        cmd += ["tests/integration"]
    elif test_type == "functional":
        cmd += ["tests/functional"]
    elif test_type == "load":
        cmd += ["tests/load"]
    elif test_type == "stress":
        cmd += ["tests/stress"]
    elif test_type == "deterministic":
        cmd += ["tests/deterministic"]
    elif test_type == "automated":
        cmd += ["tests/automated"]

    return run_command(cmd)


def run_balance_tests():
    """Run balance simulator tests."""
    print("Running balance simulator...")
    return run_command(["python", "tests/balance_simulator.py"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run naRou tests")
    parser.add_argument(
        "--type",
        default="all",
        choices=[
            "all",
            "unit",
            "integration",
            "functional",
            "load",
            "stress",
            "deterministic",
            "automated",
        ],
        help="Test type to run",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--balance", action="store_true", help="Run balance tests only")
    args = parser.parse_args()

    if args.balance:
        success = run_balance_tests()
    else:
        success = run_tests(args.type, args.coverage, args.verbose)

    sys.exit(0 if success else 1)