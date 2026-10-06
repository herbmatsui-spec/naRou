"""Data integrity: the repo must not ship placeholders, and declarations must resolve.

Both tests here are expected to FAIL on `c7def04` and are marked
``xfail(strict=True)``: strict so that resolving the defect turns into a test
failure we have to notice, rather than a silently-green test.

Placeholders are 13-byte ``# placeholder`` files that parse to ``None``.
Fourteen of the fifteen skill ids declared by monsters are declared and nothing
else — they resolve nowhere.
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


def _declared_skill_ids() -> dict[str, list[str]]:
    monsters = yaml.safe_load((DATA_DIR / "monsters.yaml").read_text(encoding="utf-8"))
    declared: dict[str, list[str]] = {}
    for monster_id, body in (monsters or {}).items():
        skills = body.get("skills") or []
        if skills:
            declared[monster_id] = list(skills)
    return declared


def _all_declared_ids() -> set[str]:
    ids: set[str] = set()
    for path in _data_files():
        if path.name == "monsters.yaml":
            continue  # the declaration site itself does not count as a definition
        try:
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        ids |= _collect_keys(parsed)
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


@pytest.mark.xfail(
    strict=True,
    reason="6 data files are 13-byte '# placeholder' stubs (D8: retire the empty growth axes)",
)
def test_no_placeholder_data_files():
    offenders = _placeholder_files()
    assert offenders == [], f"placeholder data files: {offenders}"


@pytest.mark.xfail(
    strict=True,
    reason="14 of 15 monster skill ids resolve nowhere; Phase 2 Step 47 authors them",
)
def test_every_monster_skill_id_resolves():
    defined = _all_declared_ids()
    unresolved: dict[str, list[str]] = {}
    for monster_id, skills in _declared_skill_ids().items():
        missing = [s for s in skills if s not in defined]
        if missing:
            unresolved[monster_id] = missing
    assert unresolved == {}, f"skill ids declared but never defined: {unresolved}"
