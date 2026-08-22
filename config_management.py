#!/usr/bin/env python3
"""Configuration management for naRou deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


class ConfigManager:
    def __init__(self, config_dir="config_management"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

    def load_config(self, name):
        """Load configuration from file."""
        for ext in [".yaml", ".yml", ".json"]:
            path = self.config_dir / f"{name}{ext}"
            if path.exists():
                with open(path) as f:
                    if ext == ".json":
                        return json.load(f)
                    return yaml.safe_load(f)
        return None

    def save_config(self, name, config, format="yaml"):
        """Save configuration to file."""
        ext = ".yaml" if format == "yaml" else ".json"
        path = self.config_dir / f"{name}{ext}"
        with open(path, "w") as f:
            if format == "yaml":
                yaml.dump(config, f, default_flow_style=False)
            else:
                json.dump(config, f, indent=2)
        print(f"Saved config: {path}")

    def merge_configs(self, *names):
        """Merge multiple configurations."""
        merged = {}
        for name in names:
            config = self.load_config(name)
            if config:
                merged = self._deep_merge(merged, config)
        return merged

    def _deep_merge(self, base, override):
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_value(self, name, key):
        """Get a specific configuration value."""
        config = self.load_config(name)
        if not config:
            return None

        keys = key.split(".")
        current = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    def set_value(self, name, key, value):
        """Set a specific configuration value."""
        config = self.load_config(name) or {}
        keys = key.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        self.save_config(name, config)

    def list_configs(self):
        """List all configuration files."""
        configs = []
        for ext in [".yaml", ".yml", ".json"]:
            configs.extend(self.config_dir.glob(f"*{ext}"))
        return [c.stem for c in configs]

    def validate_config(self, name, schema=None):
        """Validate configuration against schema."""
        config = self.load_config(name)
        if not config:
            return False, "Config not found"

        if schema:
            # Simple schema validation
            for key, expected_type in schema.items():
                if key not in config:
                    return False, f"Missing required key: {key}"
                if not isinstance(config[key], expected_type):
                    return False, f"Key {key} has wrong type"

        return True, "Valid"


def main():
    parser = argparse.ArgumentParser(description="Configuration Management")
    parser.add_argument("--dir", default="config_management", help="Config directory")
    parser.add_argument("--load", help="Load and display config")
    parser.add_argument("--save", nargs=2, metavar=("NAME", "FILE"), help="Save config from file")
    parser.add_argument("--merge", nargs="+", help="Merge configs")
    parser.add_argument("--get", nargs=2, metavar=("NAME", "KEY"), help="Get config value")
    parser.add_argument("--set", nargs=3, metavar=("NAME", "KEY", "VALUE"), help="Set config value")
    parser.add_argument("--list", action="store_true", help="List configs")
    parser.add_argument("--validate", nargs=2, metavar=("NAME", "SCHEMA"), help="Validate config")
    args = parser.parse_args()

    mgr = ConfigManager(args.dir)

    if args.load:
        config = mgr.load_config(args.load)
        if config:
            print(yaml.dump(config, default_flow_style=False))
        else:
            print(f"Config not found: {args.load}")
    elif args.save:
        with open(args.save[1]) as f:
            config = yaml.safe_load(f)
        mgr.save_config(args.save[0], config)
    elif args.merge:
        merged = mgr.merge_configs(*args.merge)
        print(yaml.dump(merged, default_flow_style=False))
    elif args.get:
        value = mgr.get_value(args.get[0], args.get[1])
        print(value)
    elif args.set:
        # Try to parse value as JSON, fallback to string
        try:
            value = json.loads(args.set[2])
        except json.JSONDecodeError:
            value = args.set[2]
        mgr.set_value(args.set[0], args.set[1], value)
    elif args.list:
        for config in mgr.list_configs():
            print(config)
    elif args.validate:
        schema = {}
        # Parse simple schema
        for pair in args.validate[1].split(","):
            k, t = pair.split(":")
            schema[k.strip()] = {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
            }[t.strip()]
        _valid, msg = mgr.validate_config(args.validate[0], schema)
        print(msg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
