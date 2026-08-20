#!/usr/bin/env python3
"""Monitoring management for naRou deployment."""

import argparse
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml

try:
    from prometheus_client import Gauge, start_http_server
except ImportError:
    # Fallback dummy implementations for environments without prometheus_client
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            class _NoOp:
                def set(self, value):
                    pass

            return _NoOp()

    def start_http_server(port):
        pass


class MonitoringManager:
    def __init__(self, monitor_dir="monitoring_management"):
        self._setup_prometheus()

    def _setup_prometheus(self):
        """Start Prometheus exporter on port 8000 and define gauges."""
        start_http_server(8000)
        self._check_gauge = Gauge(
            "naRou_check_success", "Health check success", ["check"]
        )

        self.monitor_dir = Path(monitor_dir)
        self.monitor_dir.mkdir(exist_ok=True)
        self.checks = {}
        self.alerts = {}
        self.running = False
        self._load_config()

    def _load_config(self):
        """Load monitoring configuration."""
        config_file = self.monitor_dir / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
                self.checks = config.get("checks", {})
                self.alerts = config.get("alerts", {})

    def save_config(self):
        """Save monitoring configuration."""
        config_file = self.monitor_dir / "config.yaml"
        config = {
            "checks": self.checks,
            "alerts": self.alerts,
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("Saved monitoring config")

    def add_check(self, name, check_type, target, interval=60, threshold=None):
        """Add a health check."""
        self.checks[name] = {
            "type": check_type,
            "target": target,
            "interval": interval,
            "threshold": threshold,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        self.save_config()
        print(f"Added check: {name}")

    def remove_check(self, name):
        """Remove a health check."""
        if name in self.checks:
            del self.checks[name]
            self.save_config()
            print(f"Removed check: {name}")

    def add_alert(self, name, condition, action, params=None):
        """Add an alert rule."""
        self.alerts[name] = {
            "condition": condition,
            "action": action,
            "params": params or {},
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        self.save_config()
        print(f"Added alert: {name}")

    def run_check(self, name):
        """Run a single health check."""
        check = self.checks.get(name)
        if not check:
            return False, "Check not found"

        if not check.get("enabled", True):
            return True, "Check disabled"

        check_type = check["type"]
        target = check["target"]
        threshold = check.get("threshold")

        try:
            if check_type == "http":
                import requests

                response = requests.get(target, timeout=10)
                success = response.status_code == 200
                return success, f"HTTP {response.status_code}"

            elif check_type == "tcp":
                import socket

                host, port = target.split(":")
                sock = socket.create_connection((host, int(port)), timeout=5)
                sock.close()
                return True, "TCP connection OK"

            elif check_type == "command":
                import subprocess
                import shlex

                cmd = shlex.split(target)
                result = subprocess.run(
                    cmd, capture_output=True, timeout=30
                )
                success = result.returncode == 0
                return (
                    success,
                    result.stdout.decode() if success else result.stderr.decode(),
                )

            elif check_type == "disk":
                import shutil

                usage = shutil.disk_usage(target)
                free_pct = (usage.free / usage.total) * 100
                if threshold:
                    success = free_pct > threshold
                else:
                    success = free_pct > 10
                return success, f"Disk free: {free_pct:.1f}%"

            elif check_type == "memory":
                import psutil

                mem = psutil.virtual_memory()
                if threshold:
                    success = mem.percent < threshold
                else:
                    success = mem.percent < 90
                return success, f"Memory usage: {mem.percent:.1f}%"

            else:
                return False, f"Unknown check type: {check_type}"

        except Exception as e:
            return False, str(e)

    def run_all_checks(self):
        """Run all health checks."""
        results = {}
        for name in self.checks:
            success, message = self.run_check(name)
            # Update Prometheus gauge
            try:
                self._check_gauge.labels(check=name).set(1 if success else 0)
            except Exception:
                pass
            results[name] = {
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        return results

    def evaluate_alerts(self, results):
        """Evaluate alert conditions."""
        for alert_name, alert in self.alerts.items():
            if not alert.get("enabled", True):
                continue

            condition = alert["condition"]
            # Simple condition evaluation
            check_name = condition.get("check")
            if check_name in results:
                result = results[check_name]
                expected = condition.get("success", True)
                if result["success"] != expected:
                    self.trigger_alert(alert_name, alert, result)

    def trigger_alert(self, alert_name, alert, result):
        """Trigger an alert action."""
        print(f"ALERT: {alert_name} - {result['message']}")

        action = alert["action"]
        params = alert.get("params", {})

        if action == "webhook":
            import requests

            try:
                requests.post(
                    params.get("url"),
                    json={
                        "alert": alert_name,
                        "message": result["message"],
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            except Exception as e:
                print(f"Failed to send webhook: {e}")

        elif action == "command":
            import subprocess
            import shlex

            try:
                cmd = shlex.split(params.get("cmd", ""))
                subprocess.run(cmd)
            except Exception as e:
                print(f"Failed to run command: {e}")

        elif action == "log":
            # Log to file
            log_file = self.monitor_dir / "alerts.log"
            with open(log_file, "a") as f:
                f.write(
                    f"{datetime.now().isoformat()} - {alert_name}: {result['message']}\n"
                )

    def start_monitoring(self, interval=60):
        """Start continuous monitoring."""
        self.running = True
        print(f"Starting monitoring (interval: {interval}s)")

        def monitor_loop():
            while self.running:
                results = self.run_all_checks()
                self.evaluate_alerts(results)

                # Log results
                log_file = self.monitor_dir / "checks.log"
                with open(log_file, "a") as f:
                    for name, result in results.items():
                        f.write(
                            f"{result['timestamp']} - {name}: {'OK' if result['success'] else 'FAIL'} - {result['message']}\n"
                        )

                time.sleep(interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        return thread

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.running = False
        print("Monitoring stopped")

    def list_checks(self):
        """List all checks."""
        return self.checks

    def list_alerts(self):
        """List all alerts."""
        return self.alerts


def main():
    parser = argparse.ArgumentParser(description="Monitoring Management")
    parser.add_argument(
        "--dir", default="monitoring_management", help="Monitoring directory"
    )
    parser.add_argument(
        "--add-check",
        nargs=4,
        metavar=("NAME", "TYPE", "TARGET", "INTERVAL"),
        help="Add check",
    )
    parser.add_argument("--remove-check", help="Remove check")
    parser.add_argument(
        "--add-alert",
        nargs=3,
        metavar=("NAME", "CONDITION", "ACTION"),
        help="Add alert",
    )
    parser.add_argument("--run", help="Run specific check")
    parser.add_argument("--run-all", action="store_true", help="Run all checks")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval")
    parser.add_argument("--list-checks", action="store_true", help="List checks")
    parser.add_argument("--list-alerts", action="store_true", help="List alerts")
    args = parser.parse_args()

    mgr = MonitoringManager(args.dir)

    if args.add_check:
        mgr.add_check(
            args.add_check[0],
            args.add_check[1],
            args.add_check[2],
            int(args.add_check[3]),
        )
    elif args.remove_check:
        mgr.remove_check(args.remove_check)
    elif args.add_alert:
        condition = json.loads(args.add_alert[1])
        mgr.add_alert(args.add_alert[0], condition, args.add_alert[2])
    elif args.run:
        success, msg = mgr.run_check(args.run)
        print(f"{'PASS' if success else 'FAIL'}: {msg}")
    elif args.run_all:
        results = mgr.run_all_checks()
        for name, result in results.items():
            print(
                f"{name}: {'PASS' if result['success'] else 'FAIL'} - {result['message']}"
            )
    elif args.monitor:
        thread = mgr.start_monitoring(args.interval)
        try:
            thread.join()
        except KeyboardInterrupt:
            mgr.stop_monitoring()
    elif args.list_checks:
        for name, check in mgr.list_checks().items():
            print(
                f"{name}: {check['type']} -> {check['target']} (every {check['interval']}s)"
            )
    elif args.list_alerts:
        for name, alert in mgr.list_alerts().items():
            print(f"{name}: {alert['condition']} -> {alert['action']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()