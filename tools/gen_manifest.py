#!/usr/bin/env python3
"""Manifest generator (Step 38).

Produces a build manifest (assets + binaries) consumed by the auto-updater and
anti-cheat integrity checks (proposal #1-C). Output: ``build_manifest.json``.

Usage:
    python tools/gen_manifest.py --dir dist
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(directory: Path, version: str = "0.0.0") -> Path:
    entries = {}
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            rel = p.relative_to(directory).as_posix()
            entries[rel] = {
                "size": p.stat().st_size,
                "sha256": file_hash(p),
            }
    manifest = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }
    out = directory / "build_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate build manifest")
    parser.add_argument("--dir", default="dist", help="Build directory")
    parser.add_argument("--version", default="0.0.0", help="Build version")
    args = parser.parse_args()
    result = generate(Path(args.dir), args.version)
    print(f"wrote {result} ({len(json.loads(result.read_text())['files'])} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
