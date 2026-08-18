#!/usr/bin/env python3
"""Environment management for naRou deployment."""
import os
import sys
import yaml
import argparse
from pathlib import Path

class EnvironmentManager:
    def __init__(self, env_dir="environment_management"):
        self.env_dir = Path(env_dir)
        self.env_dir.mkdir(exist_ok=True)
        self.environments = {}
        self._load_environments()
    
    def _load_environments(self):
        """Load all environment configurations."""
        for env_file in self.env_dir.glob("*.yaml"):
            env_name = env_file.stem
            with open(env_file) as f:
                self.environments[env_name] = yaml.safe_load(f) or {}
    
    def create_environment(self, name, base=None, **overrides):
        """Create a new environment."""
        config = {}
        if base and base in self.environments:
            config = self.environments[base].copy()
        config.update(overrides)
        
        self.environments[name] = config
        self.save_environment(name)
        print(f"Created environment: {name}")
    
    def save_environment(self, name):
        """Save environment to file."""
        path = self.env_dir / f"{name}.yaml"
        with open(path, "w") as f:
            yaml.dump(self.environments[name], f, default_flow_style=False)
        print(f"Saved environment: {path}")
    
    def get_environment(self, name):
        """Get environment configuration."""
        return self.environments.get(name)
    
    def set_variable(self, env_name, key, value):
        """Set environment variable."""
        if env_name not in self.environments:
            self.environments[env_name] = {}
        self.environments[env_name][key] = value
        self.save_environment(env_name)
    
    def get_variable(self, env_name, key):
        """Get environment variable."""
        env = self.environments.get(env_name, {})
        return env.get(key)
    
    def list_environments(self):
        """List all environments."""
        return list(self.environments.keys())
    
    def activate(self, name):
        """Activate environment (export variables)."""
        env = self.environments.get(name)
        if not env:
            print(f"Environment not found: {name}")
            return False
        
        # Generate shell export commands
        for key, value in env.items():
            print(f"export {key}={value}")
        
        print(f"# Activated environment: {name}")
        return True
    
    def diff(self, env1, env2):
        """Compare two environments."""
        e1 = self.environments.get(env1, {})
        e2 = self.environments.get(env2, {})
        
        all_keys = set(e1.keys()) | set(e2.keys())
        for key in sorted(all_keys):
            v1 = e1.get(key)
            v2 = e2.get(key)
            if v1 != v2:
                print(f"  {key}: {v1} -> {v2}")

def main():
    parser = argparse.ArgumentParser(description="Environment Management")
    parser.add_argument("--dir", default="environment_management", help="Environment directory")
    parser.add_argument("--create", nargs=2, metavar=("NAME", "BASE"), help="Create environment")
    parser.add_argument("--set", nargs=3, metavar=("ENV", "KEY", "VALUE"), help="Set variable")
    parser.add_argument("--get", nargs=2, metavar=("ENV", "KEY"), help="Get variable")
    parser.add_argument("--activate", help="Activate environment")
    parser.add_argument("--diff", nargs=2, metavar=("ENV1", "ENV2"), help="Compare environments")
    parser.add_argument("--list", action="store_true", help="List environments")
    args = parser.parse_args()
    
    mgr = EnvironmentManager(args.dir)
    
    if args.create:
        mgr.create_environment(args.create[0], args.create[1] if args.create[1] != "none" else None)
    elif args.set:
        mgr.set_variable(args.set[0], args.set[1], args.set[2])
    elif args.get:
        value = mgr.get_variable(args.get[0], args.get[1])
        print(value)
    elif args.activate:
        mgr.activate(args.activate)
    elif args.diff:
        mgr.diff(args.diff[0], args.diff[1])
    elif args.list:
        for env in mgr.list_environments():
            print(env)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()