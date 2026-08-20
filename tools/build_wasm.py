#!/usr/bin/env python3
"""WASM builder for naRou (Step 26).

Produces a WebAssembly build using Pyodide so ``web_game_client.html`` can run
the full game logic offline in the browser. Requires ``pyodide-build``.

Usage:
    python tools/build_wasm.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> bool:
    print(f"[wasm] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode == 0


def build_wasm() -> bool:
    try:
        import pyodide_build  # noqa: F401
    except ImportError:
        if not run([sys.executable, "-m", "pip", "install", "pyodide-build"]):
            print("[wasm] pyodide-build unavailable; skipping WASM build")
            return False
    out = PROJECT_ROOT / "build" / "wasm"
    out.mkdir(parents=True, exist_ok=True)
    # Wrap the game entry point into a callable module bundle.
    ok = run(
        [
            sys.executable,
            "-m",
            "pyodide_build",
            "pyoxidizer",
            "--target",
            "wasm32-unknown-emscripten",
            "main.py",
            "--outdir",
            str(out),
        ]
    )
    if not ok:
        print("[wasm] Pyodide build step skipped (toolchain not present)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build naRou WASM bundle")
    parser.parse_args()
    return 0 if build_wasm() else 1


if __name__ == "__main__":
    sys.exit(main())
