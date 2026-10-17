#!/usr/bin/env python3
"""Regression test for naRou -> naRogue rebranding.

Ensures that all user-facing strings reference the new brand name
and that no legacy 'naRou: Masterpiece Edition' strings remain
in visible output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files to scan for brand strings
SCAN_GLOBS = [
    "**/*.py",
    "**/*.md",
    "**/*.html",
    "**/*.txt",
    "**/*.yaml",
    "**/*.yml",
    "**/*.json",
    "**/*.toml",
    "**/*.bat",
    "**/*.sh",
]

# Strings that should NOT appear (case-sensitive)
FORBIDDEN_PATTERNS = [
    r"naRou: Masterpiece Edition",
]

# Strings that MUST appear (at least once)
REQUIRED_PATTERNS = [
    r"naRogue: Masterpiece Edition",
]


def collect_files():
    files = []
    for glob in SCAN_GLOBS:
        files.extend(REPO_ROOT.glob(glob))
    # Exclude certain directories
    excluded = {".git", ".worktrees", "__pycache__", "build", "dist", ".mimocode"}
    result = []
    for f in files:
        if not any(part in excluded for part in f.parts) and f.is_file():
            # Exclude this test file itself to avoid self-matching
            if "test_rebranding_regression" in f.name:
                continue
            result.append(f)
    return result


def check_file_forbidden(file_path: Path) -> list[str]:
    """Return list of forbidden matches found in file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    matches = []
    for pattern in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, content):
            # Avoid matches inside import statements like "from naRou.systems"
            # Simple heuristic: if the match is preceded by "from " or "import " within same line, skip
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.end())
            line = content[line_start:line_end]
            if re.search(r"\b(from|import)\b", line):
                continue
            matches.append(f"{file_path}:{line_start}:{match.group()}")
    return matches


def check_file_required(file_path: Path) -> bool:
    """Return True if any required pattern found in file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    for pattern in REQUIRED_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def test_rebranding():
    files = collect_files()
    forbidden_hits = []
    for f in files:
        hits = check_file_forbidden(f)
        forbidden_hits.extend(hits)

    # Require at least one file with the new brand (should be many)
    required_found = any(check_file_required(f) for f in files)

    assert required_found, "No occurrence of 'naRogue: Masterpiece Edition' found in scanned files."
    assert not forbidden_hits, "Forbidden 'naRou' strings found:\n" + "\n".join(forbidden_hits)


if __name__ == "__main__":
    test_rebranding()
    print("✅ Rebranding regression test passed.")
