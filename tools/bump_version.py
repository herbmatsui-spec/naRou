#!/usr/bin/env python3
"""Version bumper (Step 35).

Centrally manages the semantic version string stored in ``VERSION`` and mirrors
it into ``pyproject.toml`` / ``kilocode`` metadata if present.

Usage:
    python tools/bump_version.py patch
    python tools/bump_version.py minor
    python tools/bump_version.py major
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def read_version() -> list[int]:
    if VERSION_FILE.exists():
        nums = re.findall(r"\d+", VERSION_FILE.read_text().strip())
        if len(nums) >= 3:
            return [int(n) for n in nums[:3]]
    return [0, 0, 0]


def write_version(nums: list[int]) -> str:
    text = ".".join(str(n) for n in nums)
    VERSION_FILE.write_text(text + "\n")
    if PYPROJECT.exists():
        content = PYPROJECT.read_text()
        content = re.sub(r'(version\s*=\s*")[^"]+(")', rf"\g<1>{text}\g<2>", content)
        PYPROJECT.write_text(content)
    return text


def bump(part: str) -> str:
    nums = read_version()
    if part == "major":
        nums = [nums[0] + 1, 0, 0]
    elif part == "minor":
        nums = [nums[0], nums[1] + 1, 0]
    elif part == "patch":
        nums = [nums[0], nums[1], nums[2] + 1]
    else:
        raise ValueError(f"unknown part: {part}")
    return write_version(nums)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump naRou version")
    parser.add_argument("part", choices=["major", "minor", "patch"], help="Version part")
    args = parser.parse_args()
    new_v = bump(args.part)
    print(f"version -> {new_v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
