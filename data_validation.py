"""YAML data loading with existence and optional type validation.

Centralizes safe YAML loading used across managers and systems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml_validated(path: str, schema: dict[str, type] | None = None) -> dict:
    """Load a YAML file, raising on missing files and (optionally) bad types.

    Args:
        path: Path to the YAML file.
        schema: Optional mapping of key -> expected type for top-level keys.

    Returns:
        Parsed dict (empty dict if the file is empty).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if schema:
        for key, typ in schema.items():
            if key in data and not isinstance(data[key], typ):
                raise ValueError(f"Invalid type for {key} in {path}")
    return data
