#!/usr/bin/env python3
"""Monitoring script for naRou project."""
import os
import sys
import time
import subprocess
import argparse
import json
from datetime import datetime

def run_command(cmd, cwd=None):
    """Run a command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def monitor_resources(duration=60, interval=5):
    """Monitor system resources."""
    print(f"Monitoring resources for {duration}s (interval: {interval}s)...")
    
    end_time = time.time() + duration
    while time.time() < end_time:
        # CPU and memory
        success, stdout, _ = run_command("ps aux | grep -E '(python|naRou)' | grep -v grep")
        if success and stdout:
            print(f"[{datetime.now().isoformat()}] Processes:\n{stdout}")
        
        # Disk usage
        success, stdout, _ = run_command("df -h .")
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
        run_command(f"tail -f {log_file}")
    else:
        run_command(f"tail -50 {log_file}")

def monitor_tests():
    """Monitor test results."""
    print("Monitoring test results...")
    success, stdout, _ = run_command("pytest --collect-only -q 2>/dev/null | wc -l")
    if success:
        print(f"Total tests collected: {stdout.strip()}")
    
    # Run tests and show summary
    success, stdout, stderr = run_command("pytest -v --tb=short 2>&1 | tail -20")
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

def monitor_balance():
    """Monitor balance metrics."""
    print("Running balance simulation...")
    success, stdout, stderr = run_command("python tests/balance_simulator.py")
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