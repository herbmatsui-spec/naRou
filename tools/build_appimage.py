#!/usr/bin/env python3
"""AppImage builder for naRou (Step 25).

Generates a Linux AppImage from the PyInstaller one-file bundle. AppImages are
optimally Steam Deck compatible. Requires ``appimagetool`` on PATH.

Usage:
    python tools/build_appimage.py --appdir dist/naRou
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "naRou"


def run(cmd: list[str]) -> bool:
    print(f"[appimage] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def build_appimage(appdir: Path) -> bool:
    if not shutil.which("appimagetool"):
        print(
            "[appimage] appimagetool not found; skipping (install linuxdeploy/appimagetool)"
        )
        return False
    # Ensure AppRun + .desktop + icon exist (minimal placeholders).
    apprun = appdir / "AppRun"
    if not apprun.exists():
        apprun.write_text('#!/bin/sh\nexec "$(dirname "$0")/naRou" "$@"\n')
        apprun.chmod(0o755)
    desktop = appdir / f"{APP_NAME}.desktop"
    if not desktop.exists():
        desktop.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            "Exec=naRou\n"
            "Icon=naRou\n"
            "Categories=Game;\n"
        )
    icon = appdir / f"{APP_NAME}.png"
    if not icon.exists():
        icon.write_bytes(b"")
    return run(["appimagetool", str(appdir), f"{APP_NAME}.AppImage"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build naRou AppImage")
    parser.add_argument("--appdir", default="dist/naRou", help="PyInstaller output dir")
    args = parser.parse_args()
    ok = build_appimage(Path(args.appdir))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
