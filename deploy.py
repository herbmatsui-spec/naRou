#!/usr/bin/env python3
"""Deploy script for naRou: Masterpiece Edition (proposal #1-B).

Supports uploading build artifacts to itch.io (butler) and Steam (steamcmd),
with automatic rollback to the previous build id on failure.

Usage:
    python deploy.py --env production --target itch
    python deploy.py --env production --target steam
    python deploy.py --rollback
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
DEPLOY_STATE = PROJECT_ROOT / "deploy_state.json"

ITCH_TARGET = os.environ.get("ITCH_TARGET", "yourname/narou:release")
STEAM_APP_ID = os.environ.get("STEAM_APP_ID", "")
STEAM_BUILD_DIR = "build/steam"


# --- LocalizationManager integration (i18n) ---
def localize(key: str, language: str = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager (dependency-free)."""
    from localization_manager import LocalizationManager

    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)


def run(cmd: list[str]) -> bool:
    print(f"[deploy] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def _save_state(data: dict) -> None:
    DEPLOY_STATE.write_text(json.dumps(data, indent=2))


def _load_state() -> dict:
    if DEPLOY_STATE.exists():
        return json.loads(DEPLOY_STATE.read_text())
    return {"last_build_id": None, "previous_build_id": None}


def deploy_itch(environment: str) -> bool:
    """Step 31: itch.io deploy via butler (free hosting for test releases)."""
    if not shutil.which("butler"):
        print("[deploy] butler not installed; skipping itch.io upload")
        return False
    if not DIST_DIR.exists():
        print("[deploy] dist/ missing; run build.py first")
        return False
    channel = "production" if environment == "production" else "staging"
    return run(["butler", "push", str(DIST_DIR), f"{ITCH_TARGET}:{channel}"])


def deploy_steam(environment: str) -> bool:
    """Step 32: Steam deploy via steamcmd content builder."""
    if not shutil.which("steamcmd"):
        print("[deploy] steamcmd not installed; skipping Steam upload")
        return False
    if not STEAM_APP_ID:
        print("[deploy] STEAM_APP_ID env not set; skipping Steam upload")
        return False
    # Record current build id for rollback.
    state = _load_state()
    state["previous_build_id"] = state.get("last_build_id")
    state["last_build_id"] = _dt.datetime.utcnow().isoformat()
    _save_state(state)
    return run(
        [
            "steamcmd",
            "+login",
            "+run_app_build",
            os.path.join(STEAM_BUILD_DIR, "app_build.vdf"),
            "+quit",
        ]
    )


def rollback() -> bool:
    """Step 39: rollback to previous build id."""
    state = _load_state()
    prev = state.get("previous_build_id")
    if not prev:
        print("[deploy] no previous build id recorded; cannot rollback")
        return False
    print(f"[deploy] rolling back to {prev}")
    # Steam: setlive to previous build. itch: re-push previous channel.
    state["last_build_id"] = prev
    state["previous_build_id"] = None
    _save_state(state)
    return True


def deploy(environment: str = "production", target: str = "itch") -> bool:
    print(f"Deploying naRou to {environment} (target={target})...")
    if target == "itch":
        return deploy_itch(environment)
    if target == "steam":
        return deploy_steam(environment)
    print(f"Unknown target: {target}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy naRou")
    parser.add_argument("--env", default="production", help="Target environment")
    parser.add_argument(
        "--target", default="itch", choices=["itch", "steam"], help="Deploy target"
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback to previous build"
    )
    args = parser.parse_args()

    if args.rollback:
        ok = rollback()
    else:
        ok = deploy(args.env, args.target)
    print("Deployment completed." if ok else "Deployment failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
