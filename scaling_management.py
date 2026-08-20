#!/usr/bin/env python3
"""Scaling management for naRou deployment."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import yaml


class ScalingManager:
    def __init__(self, scaling_dir="scaling_management"):
        self.scaling_dir = Path(scaling_dir)
        self.scaling_dir.mkdir(exist_ok=True)
        self.config_file = self.scaling_dir / "config.yaml"
        self.state_file = self.scaling_dir / "state.json"
        self.config = self._load_config()
        self.state = self._load_state()

    def _load_config(self):
        """Load scaling configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "horizontal": {
                "min_replicas": 2,
                "max_replicas": 10,
                "target_cpu_percent": 70,
                "scale_up_cooldown": 300,
                "scale_down_cooldown": 600,
            },
            "vertical": {
                "enabled": False,
                "max_cpu": "4000m",
                "max_memory": "8Gi",
            },
            "database": {
                "read_replicas": 2,
                "max_connections": 100,
            },
            "cache": {
                "nodes": 3,
                "max_memory": "2Gi",
            },
        }

    def _load_state(self):
        """Load scaling state."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "current_replicas": 2,
            "last_scale_up": None,
            "last_scale_down": None,
            "scale_events": [],
        }

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def save_state(self):
        """Save scaling state."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def get_current_replicas(self):
        """Get current replica count."""
        return self.state.get(
            "current_replicas", self.config["horizontal"]["min_replicas"]
        )

    def scale_horizontal(self, replicas, reason="manual"):
        """Scale horizontally to target replicas."""
        current = self.get_current_replicas()
        min_replicas = self.config["horizontal"]["min_replicas"]
        max_replicas = self.config["horizontal"]["max_replicas"]

        if replicas < min_replicas or replicas > max_replicas:
            print(f"Replicas {replicas} out of range [{min_replicas}, {max_replicas}]")
            return False

        if replicas == current:
            print(f"Already at {replicas} replicas")
            return True

        print(f"Scaling horizontally: {current} -> {replicas} replicas")

        # Simulate scaling action
        # In reality, this would call kubectl, docker, etc.
        success = self._execute_scale("horizontal", replicas)

        if success:
            self.state["current_replicas"] = replicas
            if replicas > current:
                self.state["last_scale_up"] = datetime.now().isoformat()
            else:
                self.state["last_scale_down"] = datetime.now().isoformat()

            self.state["scale_events"].append(
                {
                    "type": "horizontal",
                    "from": current,
                    "to": replicas,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self.save_state()
            print(f"Scaled to {replicas} replicas")
        else:
            print("Scaling failed")

        return success

    def scale_vertical(self, cpu_limit=None, memory_limit=None):
        """Scale vertically (resource limits)."""
        print("Scaling vertically...")

        current_cpu = cpu_limit or self.config["vertical"].get("max_cpu", "4000m")
        current_memory = memory_limit or self.config["vertical"].get(
            "max_memory", "8Gi"
        )

        # Simulate vertical scaling
        success = self._execute_scale(
            "vertical", {"cpu": current_cpu, "memory": current_memory}
        )

        if success:
            if cpu_limit:
                self.config["vertical"]["max_cpu"] = cpu_limit
            if memory_limit:
                self.config["vertical"]["max_memory"] = memory_limit
            self.save_config()
            print(f"Vertical scaling: CPU={current_cpu}, Memory={current_memory}")

        return success

    def _execute_scale(self, scale_type, params):
        """Execute scaling action (placeholder)."""
        # In production, this would integrate with:
        # - Kubernetes: kubectl scale, kubectl set resources
        # - Docker Swarm: docker service scale
        # - Cloud APIs: AWS ASG, GCP Instance Groups, Azure VMSS
        # - Custom orchestration

        print(f"Executing {scale_type} scaling: {params}")
        return True

    def auto_scale(self, metrics):
        """Auto-scale based on metrics."""
        cpu_percent = metrics.get("cpu_percent", 0)
        memory_percent = metrics.get("memory_percent", 0)
        metrics.get("request_rate", 0)

        current = self.get_current_replicas()
        min_replicas = self.config["horizontal"]["min_replicas"]
        max_replicas = self.config["horizontal"]["max_replicas"]
        target_cpu = self.config["horizontal"]["target_cpu_percent"]

        # Check cooldowns
        now = datetime.now()
        if self.state["last_scale_up"]:
            last_up = datetime.fromisoformat(self.state["last_scale_up"])
            if (now - last_up).total_seconds() < self.config["horizontal"][
                "scale_up_cooldown"
            ]:
                return False

        if self.state["last_scale_down"]:
            last_down = datetime.fromisoformat(self.state["last_scale_down"])
            if (now - last_down).total_seconds() < self.config["horizontal"][
                "scale_down_cooldown"
            ]:
                return False

        # Scale up logic
        if cpu_percent > target_cpu or memory_percent > 80:
            target = min(current + 1, max_replicas)
            if target > current:
                return self.scale_horizontal(
                    target, f"auto: cpu={cpu_percent}%, mem={memory_percent}%"
                )

        # Scale down logic
        elif cpu_percent < target_cpu * 0.5 and memory_percent < 40:
            target = max(current - 1, min_replicas)
            if target < current:
                return self.scale_horizontal(
                    target, f"auto: cpu={cpu_percent}%, mem={memory_percent}%"
                )

        return True

    def configure_database_scaling(self, read_replicas=None, max_connections=None):
        """Configure database scaling."""
        if read_replicas is not None:
            self.config["database"]["read_replicas"] = read_replicas
        if max_connections is not None:
            self.config["database"]["max_connections"] = max_connections

        self.save_config()
        print(
            f"Database scaling: replicas={self.config['database']['read_replicas']}, max_conn={self.config['database']['max_connections']}"
        )
        return True

    def configure_cache_scaling(self, nodes=None, max_memory=None):
        """Configure cache scaling."""
        if nodes is not None:
            self.config["cache"]["nodes"] = nodes
        if max_memory is not None:
            self.config["cache"]["max_memory"] = max_memory

        self.save_config()
        print(
            f"Cache scaling: nodes={self.config['cache']['nodes']}, max_mem={self.config['cache']['max_memory']}"
        )
        return True

    def get_status(self):
        """Get scaling status."""
        return {
            "horizontal": {
                "current_replicas": self.get_current_replicas(),
                "min_replicas": self.config["horizontal"]["min_replicas"],
                "max_replicas": self.config["horizontal"]["max_replicas"],
                "target_cpu_percent": self.config["horizontal"]["target_cpu_percent"],
            },
            "vertical": self.config["vertical"],
            "database": self.config["database"],
            "cache": self.config["cache"],
            "recent_events": self.state["scale_events"][-10:],
        }

    def run_auto_scaler(self, interval=60):
        """Run auto-scaler loop."""
        print(f"Starting auto-scaler (interval: {interval}s)")

        try:
            while True:
                # In production, collect real metrics
                # For now, simulate
                metrics = {
                    "cpu_percent": 50,  # Would come from monitoring
                    "memory_percent": 60,
                    "request_rate": 100,
                }

                self.auto_scale(metrics)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Auto-scaler stopped")


def main():
    parser = argparse.ArgumentParser(description="Scaling Management")
    parser.add_argument("--dir", default="scaling_management", help="Scaling directory")
    parser.add_argument("--horizontal", type=int, help="Scale horizontally to replicas")
    parser.add_argument(
        "--vertical", nargs=2, metavar=("CPU", "MEMORY"), help="Scale vertically"
    )
    parser.add_argument("--auto", action="store_true", help="Run auto-scaler")
    parser.add_argument(
        "--db", nargs=2, metavar=("REPLICAS", "MAX_CONN"), help="Configure DB scaling"
    )
    parser.add_argument(
        "--cache", nargs=2, metavar=("NODES", "MAX_MEM"), help="Configure cache scaling"
    )
    parser.add_argument("--status", action="store_true", help="Show scaling status")
    parser.add_argument("--interval", type=int, default=60, help="Auto-scaler interval")
    args = parser.parse_args()

    mgr = ScalingManager(args.dir)

    if args.horizontal is not None:
        mgr.scale_horizontal(args.horizontal)
    elif args.vertical:
        mgr.scale_vertical(args.vertical[0], args.vertical[1])
    elif args.auto:
        mgr.run_auto_scaler(args.interval)
    elif args.db:
        mgr.configure_database_scaling(int(args.db[0]), int(args.db[1]))
    elif args.cache:
        mgr.configure_cache_scaling(int(args.cache[0]), args.cache[1])
    elif args.status:
        print(yaml.dump(mgr.get_status(), default_flow_style=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
