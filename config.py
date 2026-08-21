#!/usr/bin/env python3
"""Configuration script for naRou project."""
from __future__ import annotations

import argparse
import os

import yaml


def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    if os.path.exists(config_path):
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config, config_path="config.yaml"):
    """Save configuration to YAML file."""
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def configure(key, value, config_path="config.yaml"):
    """Set a configuration value."""
    config = load_config(config_path)
    keys = key.split(".")
    current = config
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value
    save_config(config, config_path)
    print(f"Set {key} = {value}")


def get_config(key, config_path="config.yaml"):
    """Get a configuration value."""
    config = load_config(config_path)
    keys = key.split(".")
    current = config
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    return current


def list_config(config_path="config.yaml"):
    """List all configuration values."""
    config = load_config(config_path)
    print(yaml.dump(config, default_flow_style=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure naRou")
    parser.add_argument(
        "--set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration value"
    )
    parser.add_argument("--get", metavar="KEY", help="Get configuration value")
    parser.add_argument("--list", action="store_true", help="List all configuration")
    parser.add_argument(
        "--config", default="config.yaml", help="Configuration file path"
    )
    args = parser.parse_args()

    if args.set:
        configure(args.set[0], args.set[1], args.config)
    elif args.get:
        value = get_config(args.get, args.config)
        print(value if value is not None else "Not set")
    elif args.list:
        list_config(args.config)
    else:
        parser.print_help()


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str | None = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager

    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
