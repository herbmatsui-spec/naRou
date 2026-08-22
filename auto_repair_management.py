#!/usr/bin/env python3
"""Auto-repair management for naRou deployment."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

import yaml


class AutoRepairManager:
    def __init__(self, repair_dir="auto_repair_management"):
        self.repair_dir = Path(repair_dir)
        self.repair_dir.mkdir(exist_ok=True)
        self.config_file = self.repair_dir / "config.yaml"
        self.history_file = self.repair_dir / "history.json"
        self.config = self._load_config()
        self.history = self._load_history()

    def _load_config(self):
        """Load auto-repair configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "enabled": True,
            "check_interval": 300,
            "max_repair_attempts": 3,
            "repair_actions": {
                "dependencies": {
                    "enabled": True,
                    "command": "pip install --force-reinstall -r requirements.txt",
                },
                "code_format": {
                    "enabled": True,
                    "command": "black . && ruff check . --fix",
                },
                "tests": {
                    "enabled": True,
                    "command": "pytest -x",
                },
                "config": {
                    "enabled": True,
                    "command": "python init.py",
                },
                "git": {
                    "enabled": True,
                    "command": "git fsck --full && git gc --prune=now",
                },
            },
            "notifications": {
                "enabled": False,
                "webhook_url": "",
            },
        }

    def _load_history(self):
        """Load repair history."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return {"repairs": []}

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def save_history(self):
        """Save repair history."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def _run_cmd(self, cmd):
        """Run a command safely without shell=True."""
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        return subprocess.run(cmd, capture_output=True, text=True)

    def check_health(self):
        """Check system health and identify issues."""
        issues = []

        # Check dependencies
        result = self._run_cmd("pip check")
        if result.returncode != 0:
            issues.append({"type": "dependencies", "message": result.stdout or result.stderr})

        # Check code formatting
        result = self._run_cmd("black --check .")
        if result.returncode != 0:
            issues.append({"type": "code_format", "message": "Code formatting issues detected"})

        result = self._run_cmd("ruff check .")
        if result.returncode != 0:
            issues.append({"type": "linting", "message": result.stdout[:500]})

        # Check tests
        result = self._run_cmd("pytest -x -q")
        if result.returncode != 0:
            issues.append(
                {
                    "type": "tests",
                    "message": result.stdout[-500:] if result.stdout else "Tests failed",
                }
            )

        # Check config
        if not os.path.exists("config.yaml"):
            issues.append({"type": "config", "message": "config.yaml not found"})

        # Check git
        result = self._run_cmd("git fsck --full")
        if result.returncode != 0:
            issues.append({"type": "git", "message": "Git repository issues detected"})

        return issues

    def repair(self, issue_type):
        """Repair a specific issue type."""
        actions = self.config.get("repair_actions", {})
        action = actions.get(issue_type)

        if not action or not action.get("enabled", True):
            print(f"No repair action for: {issue_type}")
            return False

        command = action["command"]
        print(f"Repairing {issue_type}: {command}")

        result = self._run_cmd(command)

        success = result.returncode == 0
        if success:
            print(f"Repair successful: {issue_type}")
        else:
            print(f"Repair failed: {issue_type}")
            print(result.stderr[:500])

        return success

    def repair_all(self):
        """Run all repair actions."""
        issues = self.check_health()

        if not issues:
            print("No issues found")
            return True

        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue['type']}: {issue['message'][:100]}")

        results = {}
        for issue in issues:
            issue_type = issue["type"]
            success = self.repair(issue_type)
            results[issue_type] = success

            # Record repair attempt
            self.history["repairs"].append(
                {
                    "type": issue_type,
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                    "attempt": len([r for r in self.history["repairs"] if r["type"] == issue_type])
                    + 1,
                }
            )

        self.save_history()

        all_success = all(results.values())
        if all_success:
            print("All repairs completed successfully")
        else:
            failed = [k for k, v in results.items() if not v]
            print(f"Some repairs failed: {failed}")

        return all_success

    def send_notification(self, message):
        """Send notification."""
        notif = self.config.get("notifications", {})
        if notif.get("enabled") and notif.get("webhook_url"):
            import requests

            try:
                requests.post(notif["webhook_url"], json={"text": message})
            except Exception:
                logger.exception("ロード失敗")

    def run_monitor(self, interval=None):
        """Run continuous monitoring and auto-repair."""
        if interval is None:
            interval = self.config.get("check_interval", 300)

        if not self.config.get("enabled", True):
            print("Auto-repair is disabled")
            return

        print(f"Starting auto-repair monitor (interval: {interval}s)")

        try:
            while True:
                print(f"\n[{datetime.now()}] Running health check...")
                issues = self.check_health()

                if issues:
                    print(f"Found {len(issues)} issues, attempting repair...")
                    self.repair_all()
                    self.send_notification(f"Auto-repair executed: {len(issues)} issues fixed")
                else:
                    print("System healthy")

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nAuto-repair monitor stopped")

    def get_history(self, limit=50):
        """Get repair history."""
        return self.history["repairs"][-limit:]


def main():
    parser = argparse.ArgumentParser(description="Auto-Repair Management")
    parser.add_argument("--dir", default="auto_repair_management", help="Repair directory")
    parser.add_argument("--check", action="store_true", help="Check health")
    parser.add_argument("--repair", help="Repair specific issue type")
    parser.add_argument("--repair-all", action="store_true", help="Repair all issues")
    parser.add_argument("--monitor", action="store_true", help="Run monitor")
    parser.add_argument("--interval", type=int, default=300, help="Check interval")
    parser.add_argument("--history", action="store_true", help="Show repair history")
    args = parser.parse_args()

    mgr = AutoRepairManager(args.dir)

    if args.check:
        issues = mgr.check_health()
        if issues:
            for issue in issues:
                print(f"{issue['type']}: {issue['message']}")
        else:
            print("No issues found")
    elif args.repair:
        mgr.repair(args.repair)
    elif args.repair_all:
        mgr.repair_all()
    elif args.monitor:
        mgr.run_monitor(args.interval)
    elif args.history:
        for repair in mgr.get_history():
            status = "OK" if repair["success"] else "FAIL"
            print(
                f"{repair['timestamp']} - {repair['type']} - {status} (attempt {repair['attempt']})"
            )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
