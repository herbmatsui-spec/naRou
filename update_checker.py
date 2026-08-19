#!/usr/bin/env python3
"""Update checker (Step 34).

Compares the running build's version against a remote manifest and reports
whether a newer build is available. Designed to be cheap (single HTTP HEAD)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


@dataclass
class Version:
    major: int = 0
    minor: int = 0
    patch: int = 0

    @classmethod
    def parse(cls, s: str) -> "Version":
        parts = (s.strip().lstrip("v").split(".") + ["0", "0", "0"])[:3]
        return cls(*(int(p) for p in parts))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def current_version() -> Version:
    if VERSION_FILE.exists():
        return Version.parse(VERSION_FILE.read_text().strip())
    return Version(0, 0, 0)


def fetch_remote_version(manifest_url: str, timeout: int = 5) -> Version | None:
    try:
        with urllib.request.urlopen(manifest_url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        return Version.parse(data.get("version", "0.0.0"))
    except Exception:  # noqa: BLE001
        return None


def check_for_update(manifest_url: str) -> tuple[bool, Version, Version]:
    cur = current_version()
    remote = fetch_remote_version(manifest_url)
    if remote is None:
        return (False, cur, cur)
    return (remote > cur, cur, remote)


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("usage: python update_checker.py <manifest_url>")
        raise SystemExit(1)
    has_update, cur, remote = check_for_update(url)
    print(f"current={cur} remote={remote} update_available={has_update}")
