#!/usr/bin/env python3
"""
Asset cleanup script for cleaning up temporary files, caches, and old builds.
Helps maintain a clean asset pipeline workspace.
"""

import argparse
import json
import os
import time
from pathlib import Path


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def get_file_age(file_path: str) -> float:
    """Get the age of a file in seconds."""
    return time.time() - os.path.getmtime(file_path)


def is_old_file(file_path: str, max_age_seconds: float) -> bool:
    """Check if a file is older than the specified age."""
    if not os.path.exists(file_path):
        return False
    return get_file_age(file_path) > max_age_seconds


def cleanup_directory(
    directory: str,
    max_age_hours: float = 24,
    patterns: list[str] = None,
    dry_run: bool = False,
) -> dict:
    """Clean up old files in a directory."""
    if patterns is None:
        patterns = ["*"]  # Match all files by default

    stats = {"scanned_files": 0, "deleted_files": 0, "deleted_size": 0, "errors": []}

    max_age_seconds = max_age_hours * 3600

    if not os.path.exists(directory):
        stats["errors"].append(f"Directory does not exist: {directory}")
        return stats

    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                stats["scanned_files"] += 1

                # Check if file matches any pattern
                matches_pattern = False
                for pattern in patterns:
                    if Path(file_path).match(pattern):
                        matches_pattern = True
                        break

                if not matches_pattern:
                    continue

                # Check if file is old enough to delete
                if is_old_file(file_path, max_age_seconds):
                    try:
                        file_size = os.path.getsize(file_path)
                        if dry_run:
                            print(
                                f"[DRY RUN] Would delete: {file_path} ({file_size} bytes)"
                            )
                        else:
                            os.remove(file_path)
                            print(f"Deleted: {file_path} ({file_size} bytes)")

                        stats["deleted_files"] += 1
                        stats["deleted_size"] += file_size
                    except Exception as e:
                        stats["errors"].append(f"Error deleting {file_path}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error scanning directory {directory}: {e}")

    return stats


def cleanup_temp_files(config: dict, dry_run: bool = False) -> dict:
    """Clean up temporary files."""
    temp_dir = config["directories"]["temp"]
    max_age_hours = config.get("pipeline", {}).get("temp_file_max_age_hours", 1)

    print(f"Cleaning up temporary files in: {temp_dir}")
    return cleanup_directory(temp_dir, max_age_hours, ["*"], dry_run)


def cleanup_cache_files(config: dict, dry_run: bool = False) -> dict:
    """Clean up cache files based on TTL."""
    cache_dir = config["directories"]["cache"]
    ttl_seconds = config.get("cache", {}).get("ttl", 86400)  # Default 24 hours
    max_age_hours = ttl_seconds / 3600

    print(f"Cleaning up cache files in: {cache_dir} (TTL: {ttl_seconds}s)")
    return cleanup_directory(cache_dir, max_age_hours, ["*"], dry_run)


def cleanup_old_builds(config: dict, dry_run: bool = False) -> dict:
    """Clean up old build outputs, keeping only recent ones."""
    output_dir = config["directories"]["output"]
    # Keep builds from the last 7 days by default
    max_age_hours = config.get("pipeline", {}).get(
        "build_retention_hours", 168
    )  # 7 days

    print(f"Cleaning up old builds in: {output_dir} (keeping last {max_age_hours}h)")
    return cleanup_directory(output_dir, max_age_hours, ["*"], dry_run)


def cleanup_log_files(config: dict, dry_run: bool = False) -> dict:
    """Clean up old log files."""
    logs_dir = config["directories"]["logs"]
    # Keep logs from the last 30 days by default
    max_age_hours = config.get("logging", {}).get("max_log_age_hours", 720)  # 30 days

    print(f"Cleaning up old log files in: {logs_dir} (keeping last {max_age_hours}h)")
    return cleanup_directory(logs_dir, max_age_hours, ["*.log", "*.log.*"], dry_run)


def cleanup_broken_symlinks(directory: str, dry_run: bool = False) -> dict:
    """Clean up broken symbolic links."""
    stats = {"scanned_links": 0, "broken_links": 0, "removed_links": 0, "errors": []}

    if not os.path.exists(directory):
        stats["errors"].append(f"Directory does not exist: {directory}")
        return stats

    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.islink(file_path):
                    stats["scanned_links"] += 1
                    if not os.path.exists(os.path.realpath(file_path)):
                        stats["broken_links"] += 1
                        if dry_run:
                            print(f"[DRY RUN] Would remove broken symlink: {file_path}")
                        else:
                            try:
                                os.remove(file_path)
                                print(f"Removed broken symlink: {file_path}")
                                stats["removed_links"] += 1
                            except Exception as e:
                                stats["errors"].append(
                                    f"Error removing broken symlink {file_path}: {e}"
                                )
    except Exception as e:
        stats["errors"].append(
            f"Error scanning for broken symlinks in {directory}: {e}"
        )

    return stats


def cleanup_empty_directories(directory: str, dry_run: bool = False) -> dict:
    """Remove empty directories."""
    stats = {"scanned_dirs": 0, "empty_dirs": 0, "removed_dirs": 0, "errors": []}

    if not os.path.exists(directory):
        stats["errors"].append(f"Directory does not exist: {directory}")
        return stats

    # Walk bottom-up to safely remove empty directories
    try:
        for root, dirs, files in os.walk(directory, topdown=False):
            stats["scanned_dirs"] += len(dirs)
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    # Check if directory is empty
                    if not os.listdir(dir_path):
                        stats["empty_dirs"] += 1
                        if dry_run:
                            print(f"[DRY RUN] Would remove empty directory: {dir_path}")
                        else:
                            os.rmdir(dir_path)
                            print(f"Removed empty directory: {dir_path}")
                            stats["removed_dirs"] += 1
                except Exception as e:
                    stats["errors"].append(
                        f"Error checking/removing directory {dir_path}: {e}"
                    )
    except Exception as e:
        stats["errors"].append(
            f"Error scanning for empty directories in {directory}: {e}"
        )

    return stats


def main():
    parser = argparse.ArgumentParser(description="Clean up asset pipeline files")
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--target",
        choices=["temp", "cache", "builds", "logs", "all", "symlinks", "empty-dirs"],
        default="all",
        help="What to clean up",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        help="Maximum age of files to keep (overrides config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned up without actually doing it",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    if args.dry_run:
        print("RUNNING IN DRY-RUN MODE - No files will be actually deleted")

    # Run cleanup operations
    all_stats = {}

    if args.target in ["temp", "all"]:
        all_stats["temp"] = cleanup_temp_files(config, args.dry_run)

    if args.target in ["cache", "all"]:
        all_stats["cache"] = cleanup_cache_files(config, args.dry_run)

    if args.target in ["builds", "all"]:
        all_stats["builds"] = cleanup_old_builds(config, args.dry_run)

    if args.target in ["logs", "all"]:
        all_stats["logs"] = cleanup_log_files(config, args.dry_run)

    if args.target in ["symlinks", "all"]:
        # Check symlinks in all relevant directories
        symlink_stats = {
            "scanned_links": 0,
            "broken_links": 0,
            "removed_links": 0,
            "errors": [],
        }
        for dir_key in ["temp", "cache", "output", "logs"]:
            dir_path = config["directories"].get(dir_key)
            if dir_path and os.path.exists(dir_path):
                dir_stats = cleanup_broken_symlinks(dir_path, args.dry_run)
                for key in ["scanned_links", "broken_links", "removed_links"]:
                    symlink_stats[key] += dir_stats.get(key, 0)
                symlink_stats["errors"].extend(dir_stats.get("errors", []))
        all_stats["symlinks"] = symlink_stats

    if args.target in ["empty-dirs", "all"]:
        # Check empty dirs in all relevant directories
        empty_dir_stats = {
            "scanned_dirs": 0,
            "empty_dirs": 0,
            "removed_dirs": 0,
            "errors": [],
        }
        for dir_key in ["temp", "cache", "output", "logs"]:
            dir_path = config["directories"].get(dir_key)
            if dir_path and os.path.exists(dir_path):
                dir_stats = cleanup_empty_directories(dir_path, args.dry_run)
                for key in ["scanned_dirs", "empty_dirs", "removed_dirs"]:
                    empty_dir_stats[key] += dir_stats.get(key, 0)
                empty_dir_stats["errors"].extend(dir_stats.get("errors", []))
        all_stats["empty-dirs"] = empty_dir_stats

    # Print summary
    print(f"\n{'=' * 60}")
    print("CLEANUP OPERATION SUMMARY")
    print(f"{'=' * 60}")

    total_deleted_files = 0
    total_deleted_size = 0
    total_errors = 0

    for target, stats in all_stats.items():
        print(f"\n{target.upper()}:")
        if isinstance(stats, dict):
            if "deleted_files" in stats:
                print(f"  Files scanned: {stats.get('scanned_files', 0)}")
                print(f"  Files deleted: {stats.get('deleted_files', 0)}")
                print(f"  Space freed: {stats.get('deleted_size', 0)} bytes")
                total_deleted_files += stats.get("deleted_files", 0)
                total_deleted_size += stats.get("deleted_size", 0)
            if "scanned_links" in stats:
                print(f"  Symlinks scanned: {stats.get('scanned_links', 0)}")
                print(f"  Broken symlinks found: {stats.get('broken_links', 0)}")
                print(f"  Symlinks removed: {stats.get('removed_links', 0)}")
            if "scanned_dirs" in stats:
                print(f"  Directories scanned: {stats.get('scanned_dirs', 0)}")
                print(f"  Empty directories found: {stats.get('empty_dirs', 0)}")
                print(f"  Directories removed: {stats.get('removed_dirs', 0)}")

            errors = stats.get("errors", [])
            if errors:
                print(f"  Errors: {len(errors)}")
                total_errors += len(errors)
                if args.verbose:
                    for error in errors[:3]:
                        print(f"    - {error}")
                    if len(errors) > 3:
                        print(f"    ... and {len(errors) - 3} more errors")
        else:
            print(f"  Unexpected stats format: {stats}")

    print("\nTOTALS:")
    print(f"  Files deleted: {total_deleted_files}")
    print(
        f"  Space freed: {total_deleted_size} bytes ({total_deleted_size / (1024 * 1024):.2f} MB)"
    )
    print(f"  Errors encountered: {total_errors}")

    if args.dry_run:
        print(
            "\nThis was a dry run. To actually perform cleanup, run without --dry-run"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
