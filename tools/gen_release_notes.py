#!/usr/bin/env python3
"""Release notes generator (Step 36).

Builds a CHANGELOG fragment from ``git log`` since the last tag, following
Conventional Commits conventions. Requires ``git``.

Usage:
    python tools/gen_release_notes.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    ).stdout.strip()


def last_tag() -> str:
    return git("describe", "--tags", "--abbrev=0") or ""


def recent_commits(since_tag: str) -> list[str]:
    range_spec = f"{since_tag}..HEAD" if since_tag else "HEAD"
    raw = git("log", range_spec, "--pretty=format:%s")
    return [c for c in raw.splitlines() if c.strip()]


def categorise(commits: list[str]) -> dict[str, list[str]]:
    cats = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Other": [],
    }
    for c in commits:
        low = c.lower()
        if low.startswith(("feat", "add")):
            cats["Added"].append(c)
        elif low.startswith(("fix", "bug")):
            cats["Fixed"].append(c)
        elif low.startswith(("refactor", "chore", "docs", "style")):
            cats["Changed"].append(c)
        else:
            cats["Other"].append(c)
    return cats


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument("--write", action="store_true", help="Append to CHANGELOG.md")
    args = parser.parse_args()

    tag = last_tag()
    commits = recent_commits(tag)
    cats = categorise(commits)

    lines = [f"## Release (since {tag or 'beginning'})", ""]
    for cat, items in cats.items():
        if items:
            lines.append(f"### {cat}")
            lines.extend(f"- {i}" for i in items)
            lines.append("")

    notes = "\n".join(lines)
    print(notes)

    if args.write and commits:
        with open(CHANGELOG, "a", encoding="utf-8") as fh:
            fh.write("\n" + notes + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
