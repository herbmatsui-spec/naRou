"""Unified command-line interface for naRou maintenance tools.

Consolidates the many one-off scripts under `tools/` into a single
entry point with subcommands, e.g.:

    python tools/cli.py validate-assets
    python tools/cli.py gen-manifest
"""
from __future__ import annotations

import argparse
import importlib
import logging

logger = logging.getLogger(__name__)

# Mapping of subcommand name -> dotted module path under `tools`.
COMMANDS: dict[str, str] = {
    "validate-assets": "tools.validate_assets",
    "gen-manifest": "tools.gen_manifest",
    "verify-build": "tools.verify_build",
    "gen-release-notes": "tools.gen_release_notes",
    "bump-version": "tools.bump_version",
    "stats-assets": "tools.stats_assets",
    "visual-regression": "tools.visual_regression",
}


def _run(module_path: str) -> int:
    """Import a tool module and invoke its ``main()`` if present."""
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to load %s: %s", module_path, e)
        return 1
    main = getattr(mod, "main", None)
    if callable(main):
        main()
    else:
        logger.warning("%s has no main(); nothing to run", module_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tools/cli.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")
    for name in COMMANDS:
        sub.add_parser(name, help=f"Run {name}")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    module_path = COMMANDS.get(args.cmd)
    if not module_path:
        logger.error("Unknown command: %s", args.cmd)
        return 2
    return _run(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
