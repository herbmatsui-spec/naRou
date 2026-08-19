#!/usr/bin/env python3
"""Build verification (Step 29).

Smoke-tests a built artifact by invoking it with ``--help`` (PyInstaller one-file
binaries support ``--help``). Used by CI/CD after packaging.

Usage:
    python tools/verify_build.py --binary dist/naRou
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def verify(binary: Path) -> bool:
    if not binary.exists():
        print(f"[verify] MISSING: {binary}")
        return False
    print(f"[verify] found: {binary} ({binary.stat().st_size} bytes)")
    try:
        result = subprocess.run(
            [str(binary), "--help"],
            capture_output=True, text=True, timeout=60,
        )
        ok = result.returncode in (0, 1)  # --help often exits 0/1
        print(f"[verify] --help exit={result.returncode} -> {'OK' if ok else 'FAIL'}")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[verify] error running binary: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify naRou build")
    parser.add_argument("--binary", default="dist/naRou", help="Built binary path")
    args = parser.parse_args()
    return 0 if verify(Path(args.binary)) else 1


if __name__ == "__main__":
    sys.exit(main())
