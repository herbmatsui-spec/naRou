#!/usr/bin/env python3
"""Build script for naRou: Masterpiece Edition.

Implements proposal #1-B (build/deploy automation). Supports one-file
PyInstaller builds for Windows, macOS and Linux, plus AppImage and WASM
bundles via the dedicated tools under ``tools/``.

Usage:
    python build.py --platform auto     # detect current OS
    python build.py --platform windows
    python build.py --platform macos
    python build.py --platform linux
    python build.py --platform all
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_POINT = "main.py"
APP_NAME = "naRou"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

HIDDEN_IMPORTS = [
    "yaml",
    "tcod",
    "core_framework",
    "data_manager",
    "config_manager",
]


def run_command(cmd: list[str], cwd: Path | None = None) -> bool:
    """Run a command and return True on success."""
    print(f"[build] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT))
    return result.returncode == 0


def ensure_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        return run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
    return True


def _common_args(onefile: bool = True) -> list[str]:
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconfirm",
        "--clean",
    ]
    if onefile:
        args.append("--onefile")
    for imp in HIDDEN_IMPORTS:
        args += ["--hidden-import", imp]
    return args


def _build_windows() -> bool:
    """Step 22: Windows build target (--windowed for tcod SDL)."""
    args = _common_args() + ["--windowed", str(PROJECT_ROOT / ENTRY_POINT)]
    return run_command(args)


def _build_macos() -> bool:
    """Step 23: macOS build target."""
    args = _common_args() + ["--windowed", str(PROJECT_ROOT / ENTRY_POINT)]
    return run_command(args)


def _build_linux() -> bool:
    """Step 24: Linux build target."""
    args = _common_args() + [str(PROJECT_ROOT / ENTRY_POINT)]
    return run_command(args)


def build_platform(platform: str) -> bool:
    builders = {
        "windows": _build_windows,
        "macos": _build_macos,
        "linux": _build_linux,
    }
    if platform == "auto":
        if sys.platform.startswith("win"):
            platform = "windows"
        elif sys.platform == "darwin":
            platform = "macos"
        else:
            platform = "linux"
        print(f"[build] auto-detected platform: {platform}")
    if platform not in builders:
        print(f"[build] unknown platform: {platform}")
        return False
    if not ensure_pyinstaller():
        return False
    return builders[platform]()


def build_all() -> bool:
    ok = True
    for p in ("windows", "macos", "linux"):
        ok = build_platform(p) and ok
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Build naRou")
    parser.add_argument(
        "--platform", default="auto",
        choices=["auto", "windows", "macos", "linux", "all"],
        help="Target platform",
    )
    parser.add_argument("--clean", action="store_true", help="Clean before build")
    args = parser.parse_args()

    if args.clean:
        for d in (DIST_DIR, BUILD_DIR):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

    if args.platform == "all":
        ok = build_all()
    else:
        ok = build_platform(args.platform)
    print("[build] done." if ok else "[build] FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
