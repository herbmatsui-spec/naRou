#!/usr/bin/env python3
"""Checksum generator (Step 37).

Emits SHA-256 checksums for all distribution artifacts so downloaders can verify
integrity. Output: ``checksums.txt``.

Usage:
    python tools/gen_checksums.py --dir dist
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(directory: Path) -> Path:
    out = directory / "checksums.txt"
    lines = []
    for p in sorted(directory.rglob("*")):
        if p.is_file() and p != out:
            rel = p.relative_to(directory)
            lines.append(f"{sha256(p)}  {rel.as_posix()}")
    out.write_text("\n".join(lines) + "\n")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SHA-256 checksums")
    parser.add_argument("--dir", default="dist", help="Directory to checksum")
    args = parser.parse_args()
    result = generate(Path(args.dir))
    print(f"wrote {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
