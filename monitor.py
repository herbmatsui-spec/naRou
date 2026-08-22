#!/usr/bin/env python3
"""Monitoring script for naRou project."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime


def run_command(cmd, cwd=None):
    """Run a command and return output."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def monitor_resources(duration=60, interval=5):
    """Monitor system resources."""
    print(f"Monitoring resources for {duration}s (interval: {interval}s)...")

    end_time = time.time() + duration
    while time.time() < end_time:
        # CPU and memory
        success, stdout, _ = run_command(["ps", "aux"])
        if success and stdout:
            # Filter for python/naRou processes
            filtered = [
                line
                for line in stdout.split("\n")
                if ("python" in line.lower() or "narou" in line.lower()) and "grep" not in line
            ]
            if filtered:
                print(f"[{datetime.now().isoformat()}] Processes:\n" + "\n".join(filtered))

        # Disk usage
        success, stdout, _ = run_command(["df", "-h", "."])
        if success:
            print(f"[{datetime.now().isoformat()}] Disk:\n{stdout}")

        time.sleep(interval)


def monitor_logs(log_file="logs/game.log", follow=False):
    """Monitor log file."""
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return

    print(f"Monitoring log: {log_file}")
    if follow:
        run_command(["tail", "-f", log_file])
    else:
        run_command(["tail", "-50", log_file])


def monitor_tests():
    """Monitor test results."""
    print("Monitoring test results...")
    success, stdout, _ = run_command(["pytest", "--collect-only", "-q"])
    if success:
        # Count tests
        test_count = len([l for l in stdout.split("\n") if l.strip() and not l.startswith("=")])
        print(f"Total tests collected: {test_count}")

    # Run tests and show summary
    success, stdout, stderr = run_command(["pytest", "-v", "--tb=short"])
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)


def monitor_balance():
    """Monitor balance metrics."""
    print("Running balance simulation...")
    success, stdout, stderr = run_command(["python", "tests/balance_simulator.py"])
    if success:
        print(stdout)
    else:
        print(stderr, file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor naRou")
    parser.add_argument("--resources", action="store_true", help="Monitor system resources")
    parser.add_argument("--logs", action="store_true", help="Monitor logs")
    parser.add_argument("--follow", action="store_true", help="Follow log file")
    parser.add_argument("--tests", action="store_true", help="Monitor test results")
    parser.add_argument("--balance", action="store_true", help="Monitor balance")
    parser.add_argument("--duration", type=int, default=60, help="Monitoring duration (seconds)")
    parser.add_argument("--interval", type=int, default=5, help="Monitoring interval (seconds)")
    args = parser.parse_args()

    if args.resources:
        monitor_resources(args.duration, args.interval)
    elif args.logs:
        monitor_logs(follow=args.follow)
    elif args.tests:
        monitor_tests()
    elif args.balance:
        monitor_balance()
    else:
        parser.print_help()
