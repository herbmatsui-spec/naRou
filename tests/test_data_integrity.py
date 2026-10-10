"""Data integrity: the repo must not ship placeholders, and declarations must resolve.

The first test is expected to FAIL on `c7def04` and is marked
``xfail(strict=True)``: strict so that resolving the defect turns into a test
failure we have to notice, rather than a silently-green test.

Placeholders are 13-byte ``# placeholder`` files that parse to ``None``.

The second test verifies that all monster ability IDs declared in monsters.yaml
resolve to actual definitions in monster_abilities.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def _data_files() -> list[Path]:
    return sorted(
        p
        for p in DATA_DIR.rglob("*")
        if p.suffix in {".yaml", ".yml"}
        and "schemas" not in p.parts
        and "generated" not in p.parts
    )


def _placeholder_files() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for path in _data_files():
        raw = path.read_bytes()
        try:
            parsed = yaml.safe_load(raw.decode("utf-8"))
        except yaml.YAMLError:
            continue
        if parsed is None and raw.strip() == b"# placeholder":
            out.append((str(path.relative_to(REPO_ROOT)), len(raw)))
    return out


def _declared_ability_ids() -> dict[str, list[str]]:
    monsters = yaml.safe_load((DATA_DIR / "monsters.yaml").read_text(encoding="utf-8"))
    declared: dict[str, list[str]] = {}
    for monster_id, body in (monsters or {}).items():
        abilities = body.get("abilities") or body.get("skills") or []
        if abilities:
            declared[monster_id] = list(abilities)
    return declared


def _all_defined_ability_ids() -> set[str]:
    ids: set[str] = set()
    # Check monster_abilities.yaml for definitions
    abilities_path = DATA_DIR / "monster_abilities.yaml"
    if abilities_path.exists():
        try:
            parsed = yaml.safe_load(abilities_path.read_text(encoding="utf-8"))
            if parsed:
                # The YAML uses keys as ability IDs (e.g., throw_stone: {name: ...})
                for key in parsed.keys():
                    ids.add(key)
        except yaml.YAMLError:
            pass
    return ids


def _collect_keys(node: object) -> set[str]:
    if isinstance(node, dict):
        found = {str(k) for k in node}
        for value in node.values():
            found |= _collect_keys(value)
        return found
    if isinstance(node, list):
        found: set[str] = set()
        for item in node:
            found |= _collect_keys(item)
        return found
    return set()


def test_no_placeholder_data_files():
    """13バイト '# placeholder' スタブの残存を禁じる (Phase 3 で全置換)"""
    offenders = _placeholder_files()
    assert offenders == [], f"placeholder data files: {offenders}"


def test_every_monster_ability_id_resolves():
    """全モンスターの宣言能力が monster_abilities.yaml で定義されていることを確認"""
    defined = _all_defined_ability_ids()
    unresolved: dict[str, list[str]] = {}
    for monster_id, abilities in _declared_ability_ids().items():
        missing = [a for a in abilities if a not in defined]
        if missing:
            unresolved[monster_id] = missing
    assert unresolved == {}, f"ability ids declared but never defined: {unresolved}"
