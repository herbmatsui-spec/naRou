#!/usr/bin/env python3
"""Failover management for naRou deployment."""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml


class FailoverManager:
    def __init__(self, failover_dir="failover_management"):
        self.failover_dir = Path(failover_dir)
        self.failover_dir.mkdir(exist_ok=True)
        self.config_file = self.failover_dir / "config.yaml"
        self.state_file = self.failover_dir / "state.json"
        self.config = self._load_config()
        self.state = self._load_state()

    def _load_config(self):
        """Load failover configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "primary": {
                "name": "primary",
                "url": "http://localhost:8080",
                "health_endpoint": "/health",
            },
            "backup": {
                "name": "backup",
                "url": "http://backup:8080",
                "health_endpoint": "/health",
            },
            "monitoring": {
                "interval": 30,
                "timeout": 5,
                "max_failures": 3,
                "recovery_threshold": 2,
            },
            "failover": {
                "auto_failover": True,
                "auto_failback": True,
                "notification_webhook": "",
            },
        }

    def _load_state(self):
        """Load failover state."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "current": "primary",
            "failures": 0,
            "recoveries": 0,
            "last_failover": None,
            "last_failback": None,
            "events": [],
        }

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def save_state(self):
        """Save failover state."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def check_health(self, target="primary"):
        """Check health of a target."""
        config = self.config.get(target, {})
        url = config.get("url", "").rstrip("/")
        endpoint = config.get("health_endpoint", "/health")
        full_url = f"{url}{endpoint}"
        timeout = self.config["monitoring"].get("timeout", 5)

        try:
            response = requests.get(full_url, timeout=timeout)
            return response.status_code == 200, response.status_code
        except Exception as e:
            return False, str(e)
            logger.exception("Unhandled exception")

    def failover(self, reason="manual"):
        """Perform failover to backup."""
        if self.state["current"] == "backup":
            print("Already on backup")
            return False

        print(f"Initiating failover to backup ({reason})")

        # Check backup health first
        healthy, status = self.check_health("backup")
        if not healthy:
            print(f"Backup is unhealthy: {status}")
            return False

        # Execute failover
        # In production, this would update load balancer, DNS, etc.
        success = self._execute_failover("backup")

        if success:
            self.state["current"] = "backup"
            self.state["failures"] = 0
            self.state["last_failover"] = datetime.now().isoformat()
            self.state["events"].append(
                {
                    "type": "failover",
                    "from": "primary",
                    "to": "backup",
                    "reason": reason,
                    "timestamp": self.state["last_failover"],
                }
            )
            self.save_state()

            # Send notification
            self._send_notification(f"Failover to backup: {reason}")

            print("Failover completed successfully")
        else:
            print("Failover failed")

        return success

    def failback(self, reason="manual"):
        """Perform failback to primary."""
        if self.state["current"] == "primary":
            print("Already on primary")
            return False

        print(f"Initiating failback to primary ({reason})")

        # Check primary health
        healthy, status = self.check_health("primary")
        if not healthy:
            print(f"Primary is unhealthy: {status}")
            return False

        # Execute failback
        success = self._execute_failover("primary")

        if success:
            self.state["current"] = "primary"
            self.state["recoveries"] = 0
            self.state["last_failback"] = datetime.now().isoformat()
            self.state["events"].append(
                {
                    "type": "failback",
                    "from": "backup",
                    "to": "primary",
                    "reason": reason,
                    "timestamp": self.state["last_failback"],
                }
            )
            self.save_state()

            # Send notification
            self._send_notification(f"Failback to primary: {reason}")

            print("Failback completed successfully")
        else:
            print("Failback failed")

        return success

    def _execute_failover(self, target):
        """Execute failover action (placeholder)."""
        # In production, this would:
        # - Update load balancer target
        # - Update DNS records
        # - Update service mesh configuration
        # - Run infrastructure-as-code (Terraform, etc.)

        print(f"Executing failover to {target}")
        return True

    def _send_notification(self, message):
        """Send notification."""
        webhook = self.config["failover"].get("notification_webhook", "")
        if webhook:
            try:
                requests.post(webhook, json={"text": message})
            except Exception as e:
                logger.exception("Unhandled exception")
                print(f"Failed to send notification: {e}")

    def monitor(self):
        """Run one monitoring cycle."""
        current = self.state["current"]

        # Check current target
        healthy, status = self.check_health(current)

        if healthy:
            # Reset failure counter
            self.state["failures"] = 0
            self.state["recoveries"] += 1

            # Check for auto-failback
            if current == "backup" and self.config["failover"].get(
                "auto_failback", True
            ):
                recovery_threshold = self.config["monitoring"].get(
                    "recovery_threshold", 2
                )
                if self.state["recoveries"] >= recovery_threshold:
                    print("Primary recovered, initiating failback...")
                    self.failback("auto: primary recovered")
        else:
            self.state["failures"] += 1
            self.state["recoveries"] = 0
            print(
                f"Health check failed for {current}: {status} (failures: {self.state['failures']})"
            )

            # Check for auto-failover
            if current == "primary" and self.config["failover"].get(
                "auto_failover", True
            ):
                max_failures = self.config["monitoring"].get("max_failures", 3)
                if self.state["failures"] >= max_failures:
                    print("Max failures reached, initiating failover...")
                    self.failover("auto: max failures reached")

        self.save_state()

    def run_monitor_loop(self, interval=None):
        """Run continuous monitoring loop."""
        if interval is None:
            interval = self.config["monitoring"].get("interval", 30)

        print(f"Starting failover monitor (interval: {interval}s)")
        print(f"Primary: {self.config['primary']['url']}")
        print(f"Backup: {self.config['backup']['url']}")

        try:
            while True:
                self.monitor()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nFailover monitor stopped")

    def get_status(self):
        """Get failover status."""
        primary_healthy, primary_status = self.check_health("primary")
        backup_healthy, backup_status = self.check_health("backup")

        return {
            "current": self.state["current"],
            "primary": {"healthy": primary_healthy, "status": primary_status},
            "backup": {"healthy": backup_healthy, "status": backup_status},
            "failures": self.state["failures"],
            "recoveries": self.state["recoveries"],
            "last_failover": self.state["last_failover"],
            "last_failback": self.state["last_failback"],
            "recent_events": self.state["events"][-10:],
        }

    def manual_failover(self):
        """Manual failover trigger."""
        return self.failover("manual")

    def manual_failback(self):
        """Manual failback trigger."""
        return self.failback("manual")


def main():
    parser = argparse.ArgumentParser(description="Failover Management")
    parser.add_argument(
        "--dir", default="failover_management", help="Failover directory"
    )
    parser.add_argument("--failover", action="store_true", help="Manual failover")
    parser.add_argument("--failback", action="store_true", help="Manual failback")
    parser.add_argument("--monitor", action="store_true", help="Run monitor loop")
    parser.add_argument("--check", action="store_true", help="Run single check")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--interval", type=int, default=30, help="Monitor interval")
    args = parser.parse_args()

    mgr = FailoverManager(args.dir)

    if args.failover:
        mgr.manual_failover()
    elif args.failback:
        mgr.manual_failback()
    elif args.monitor:
        mgr.run_monitor_loop(args.interval)
    elif args.check:
        mgr.monitor()
    elif args.status:
        print(yaml.dump(mgr.get_status(), default_flow_style=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
