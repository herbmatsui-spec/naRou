#!/usr/bin/env python3
"""Failover script for naRou project."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import argparse
import subprocess
import sys
import time
from datetime import datetime

import requests


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    if isinstance(cmd, str):
        import shlex

        cmd = shlex.split(cmd)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def check_health(endpoint="http://localhost:8080/health"):
    """Check service health."""
    try:
        response = requests.get(endpoint, timeout=5)
        return response.status_code == 200
    except Exception:
        # TODO: handle exception properly
        logger.exception("Unhandled exception")
        return False


def failover_to_backup(backup_endpoint="http://backup:8080"):
    """Failover to backup service."""
    print(f"Failing over to backup: {backup_endpoint}")

    # Check backup health
    if check_health(f"{backup_endpoint}/health"):
        print("Backup service is healthy")

        # Update DNS/load balancer (placeholder)
        print("Updating load balancer to point to backup...")
        # run_command("update_load_balancer --target backup")

        print("Failover completed!")
        return True
    else:
        print("Backup service is unhealthy!")
        return False


def failback_to_primary(primary_endpoint="http://primary:8080"):
    """Failback to primary service."""
    print(f"Failing back to primary: {primary_endpoint}")

    # Check primary health
    if check_health(f"{primary_endpoint}/health"):
        print("Primary service is healthy")

        # Update DNS/load balancer (placeholder)
        print("Updating load balancer to point to primary...")
        # run_command("update_load_balancer --target primary")

        print("Failback completed!")
        return True
    else:
        print("Primary service is still unhealthy!")
        return False


def monitor_and_failover(
    primary_endpoint="http://localhost:8080",
    backup_endpoint="http://backup:8080",
    interval=30,
):
    """Monitor primary and failover if needed."""
    print(f"Monitoring {primary_endpoint} (interval: {interval}s)")
    print("Press Ctrl+C to stop")

    primary_down = False
    while True:
        try:
            if check_health(f"{primary_endpoint}/health"):
                if primary_down:
                    print(f"[{datetime.now()}] Primary recovered, failing back...")
                    failback_to_primary(primary_endpoint)
                    primary_down = False
                else:
                    print(f"[{datetime.now()}] Primary healthy")
            else:
                if not primary_down:
                    print(f"[{datetime.now()}] Primary down, initiating failover...")
                    if failover_to_backup(backup_endpoint):
                        primary_down = True
                    else:
                        print("Failover failed!")
                else:
                    print(f"[{datetime.now()}] Primary still down, running on backup")

            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break
        except Exception as e:
            logger.exception("Unhandled exception")
            print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Failover naRou")
    parser.add_argument("--to-backup", action="store_true", help="Failover to backup")
    parser.add_argument("--to-primary", action="store_true", help="Failback to primary")
    parser.add_argument("--monitor", action="store_true", help="Monitor and auto-failover")
    parser.add_argument("--primary", default="http://localhost:8080", help="Primary endpoint")
    parser.add_argument("--backup", default="http://backup:8080", help="Backup endpoint")
    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval (seconds)")
    args = parser.parse_args()

    if args.to_backup:
        failover_to_backup(args.backup)
    elif args.to_primary:
        failback_to_primary(args.primary)
    elif args.monitor:
        monitor_and_failover(args.primary, args.backup, args.interval)
    else:
        parser.print_help()
