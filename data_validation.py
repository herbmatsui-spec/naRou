"""YAML data loading with schema validation.

Centralizes safe YAML loading used across managers and systems.

Supports:
  * required keys  (``Required(...)`` wrapper)
  * nested structure validation (dict schema entries, validated recursively)
  * custom validators (callable schema entries)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

__all__ = ["SchemaError", "Required", "load_yaml_validated"]

_MISSING = object()


class SchemaError(ValueError):
    """Raised when loaded YAML data does not conform to a schema."""


class Required:
    """ラッパー: スキーマエントリを「必須」として扱う。

    どんなエントリ（型・ネスト辞書・カスタムバリデレータ）でも
    必須化できる。
    """

    __slots__ = ("entry",)

    def __init__(self, entry: Any) -> None:
        self.entry = entry

    def __repr__(self) -> str:
        return f"Required({self.entry!r})"


def _validate_value(
    value: Any,
    entry: Any,
    path: str,
    errors: list[str],
) -> None:
    """1 値をスキーマエントリに対して検証し、エラーを errors に追加する."""
    required = False
    if isinstance(entry, Required):
        required = True
        entry = entry.entry

    if value is _MISSING:
        if required:
            errors.append(f"Missing required key: {path}")
        return

    if isinstance(entry, type):
        if not isinstance(value, entry):
            errors.append(
                f"Invalid type for {path}: expected {entry.__name__}, "
                f"got {type(value).__name__}"
            )
    elif isinstance(entry, dict):
        if not isinstance(value, dict):
            errors.append(
                f"Invalid type for {path}: expected dict, got {type(value).__name__}"
            )
        else:
            _validate_mapping(value, entry, path, errors)
    elif callable(entry):
        try:
            result = entry(value)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Custom validator failed for {path}: {exc}")
        else:
            if result is not None and not result:
                errors.append(f"Custom validator failed for {path}")
    else:
        errors.append(f"Unknown schema entry for {path}: {entry!r}")


def _validate_mapping(
    data: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    for key, entry in schema.items():
        _validate_value(data.get(key, _MISSING), entry, f"{path}.{key}", errors)


def load_yaml_validated(
    path: str,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load a YAML file, raising on missing files and (optionally) bad schema.

    Args:
        path: Path to the YAML file.
        schema: Optional mapping of key -> schema entry. An entry may be:

            * a type (e.g. ``str``, ``int``, ``dict``): type-checked when present,
              optional unless wrapped in :class:`Required`.
            * a dict: nested schema, validated recursively.
            * a callable: custom validator ``fn(value)`` that raises or returns
              a falsy value on failure.
            * :class:`Required(entry)`: marks the key as required.

    Returns:
        Parsed dict (empty dict if the file is empty).

    Raises:
        FileNotFoundError: the file does not exist.
        SchemaError: the top-level value is not a mapping, or the data does
            not conform to ``schema``.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SchemaError(
            f"Top-level YAML must be a mapping, got {type(data).__name__}: {path}"
        )
    if schema:
        errors: list[str] = []
        _validate_mapping(data, schema, str(p), errors)
        if errors:
            raise SchemaError(
                f"Schema validation failed for {path}:\n" + "\n".join(errors)
            )
    return data
