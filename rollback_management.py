#!/usr/bin/env python3
"""Rollback management for naRou deployment."""
import os
import sys
import yaml
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

class RollbackManager:
    def __init__(self, rollback_dir="rollback_management"):
        self.rollback_dir = Path(rollback_dir)
        self.rollback_dir.mkdir(exist_ok=True)
        self.rollbacks = {}
        self._load_rollbacks()
    
    def _load_rollbacks(self):
        """Load rollback history."""
        for rollback_file in self.rollback_dir.glob("*.yaml"):
            with open(rollback_file) as f:
                data = yaml.safe_load(f)
                if data:
                    self.rollbacks[data.get("id")] = data
    
    def create_rollback_plan(self, rollout_id, target_version, reason="manual"):
        """Create a rollback plan."""
        rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rollback = {
            "id": rollback_id,
            "rollout_id": rollout_id,
            "target_version": target_version,
            "reason": reason,
            "status": "planned",
            "created_at": datetime.now().isoformat(),
            "steps": [],
            "executed_at": None,
        }
        
        # Generate rollback steps
        rollback["steps"] = [
            {"name": "stop_traffic", "action": "stop_traffic", "params": {"version": rollout_id}},
            {"name": "restore_database", "action": "restore_database", "params": {"target": target_version}},
            {"name": "restore_config", "action": "restore_config", "params": {"target": target_version}},
            {"name": "deploy_previous", "action": "deploy", "params": {"version": target_version}},
            {"name": "health_check", "action": "health_check", "params": {}},
            {"name": "restore_traffic", "action": "restore_traffic", "params": {"version": target_version}},
        ]
        
        self.rollbacks[rollback_id] = rollback
        self._save_rollback(rollback)
        print(f"Created rollback plan: {rollback_id}")
        return rollback_id
    
    def _save_rollback(self, rollback):
        """Save rollback to file."""
        path = self.rollback_dir / f"{rollback['id']}.yaml"
        with open(path, "w") as f:
            yaml.dump(rollback, f, default_flow_style=False)
    
    def execute_rollback(self, rollback_id):
        """Execute rollback plan."""
        rollback = self.rollbacks.get(rollback_id)
        if not rollback:
            print(f"Rollback not found: {rollback_id}")
            return False
        
        rollback["status"] = "executing"
        rollback["executed_at"] = datetime.now().isoformat()
        self._save_rollback(rollback)
        
        print(f"Executing rollback: {rollback_id}")
        
        for i, step in enumerate(rollback["steps"]):
            step["status"] = "running"
            step["started_at"] = datetime.now().isoformat()
            self._save_rollback(rollback)
            
            print(f"  Step {i+1}/{len(rollback['steps'])}: {step['name']}")
            
            # Simulate step execution
            success = self._run_rollback_action(step["action"], step["params"])
            
            step["status"] = "completed" if success else "failed"
            step["completed_at"] = datetime.now().isoformat()
            self._save_rollback(rollback)
            
            if not success:
                rollback["status"] = "failed"
                self._save_rollback(rollback)
                print(f"Rollback failed at step: {step['name']}")
                return False
        
        rollback["status"] = "completed"
        self._save_rollback(rollback)
        print(f"Rollback {rollback_id} completed successfully!")
        return True
    
    def _run_rollback_action(self, action, params):
        """Run a rollback action."""
        actions = {
            "stop_traffic": lambda p: True,
            "restore_database": lambda p: True,
            "restore_config": lambda p: True,
            "deploy": lambda p: True,
            "health_check": lambda p: True,
            "restore_traffic": lambda p: True,
        }
        
        func = actions.get(action)
        if func:
            return func(params)
        print(f"Unknown rollback action: {action}")
        return False
    
    def auto_rollback(self, rollout_id, health_check_url, max_failures=3):
        """Automatically rollback on health check failures."""
        print(f"Setting up auto-rollback for {rollout_id}")
        
        failures = 0
        while failures < max_failures:
            # Simulate health check
            import requests
            try:
                response = requests.get(health_check_url, timeout=5)
                if response.status_code != 200:
                    failures += 1
                    print(f"Health check failed ({failures}/{max_failures})")
                else:
                    failures = 0
                    print("Health check passed")
            except Exception:
                failures += 1
                print(f"Health check error ({failures}/{max_failures})")
            
            if failures >= max_failures:
                print("Max failures reached, initiating rollback...")
                rollback_id = self.create_rollback_plan(rollout_id, "previous", "auto")
                self.execute_rollback(rollback_id)
                return True
            
            time.sleep(10)
        
        return False
    
    def get_rollback(self, rollback_id):
        """Get rollback details."""
        return self.rollbacks.get(rollback_id)
    
    def list_rollbacks(self):
        """List all rollbacks."""
        return sorted(self.rollbacks.values(), key=lambda r: r["created_at"], reverse=True)

def main():
    parser = argparse.ArgumentParser(description="Rollback Management")
    parser.add_argument("--dir", default="rollback_management", help="Rollback directory")
    parser.add_argument("--create", nargs=3, metavar=("ROLLOUT_ID", "TARGET_VERSION", "REASON"), help="Create rollback plan")
    parser.add_argument("--execute", help="Execute rollback")
    parser.add_argument("--auto", nargs=2, metavar=("ROLLOUT_ID", "HEALTH_URL"), help="Auto-rollback monitoring")
    parser.add_argument("--status", help="Get rollback status")
    parser.add_argument("--list", action="store_true", help="List rollbacks")
    args = parser.parse_args()
    
    mgr = RollbackManager(args.dir)
    
    if args.create:
        mgr.create_rollback_plan(args.create[0], args.create[1], args.create[2])
    elif args.execute:
        mgr.execute_rollback(args.execute)
    elif args.auto:
        mgr.auto_rollback(args.auto[0], args.auto[1])
    elif args.status:
        rollback = mgr.get_rollback(args.status)
        if rollback:
            print(yaml.dump(rollback, default_flow_style=False))
    elif args.list:
        for rollback in mgr.list_rollbacks():
            print(f"{rollback['id']} - {rollback['rollout_id']} -> v{rollback['target_version']} - {rollback['status']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()