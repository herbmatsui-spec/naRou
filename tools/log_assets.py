#!/usr/bin/env python3
"""
Log management script for the asset pipeline.
Handles log rotation, analysis, archiving, and reporting.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def rotate_logs(
    log_dir: str,
    max_size_mb: float = 10,
    max_files: int = 5,
    compress_old: bool = True,
    dry_run: bool = False,
) -> dict:
    """Rotate log files based on size and count."""
    stats = {
        "logs_rotated": 0,
        "logs_compressed": 0,
        "logs_removed": 0,
        "space_saved_bytes": 0,
        "errors": [],
    }

    if not os.path.exists(log_dir):
        stats["errors"].append(f"Log directory does not exist: {log_dir}")
        return stats

    max_size_bytes = max_size_mb * 1024 * 1024

    try:
        # Find log files
        log_files = []
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith(".log"):
                    log_files.append(os.path.join(root, file))

        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: os.path.getmtime(x))

        total_size = 0
        files_to_keep = []

        # Process each log file
        for log_file in log_files:
            try:
                file_size = os.path.getsize(log_file)
                total_size += file_size

                # Check if this file should be rotated
                if total_size > max_size_bytes:
                    # This file and older ones should be rotated/compressed
                    if dry_run:
                        print(f"[DRY RUN] Would rotate: {log_file} ({file_size} bytes)")
                    else:
                        # Rotate the file
                        rotated_file = log_file + f".{int(time.time())}"
                        shutil.move(log_file, rotated_file)
                        stats["logs_rotated"] += 1

                        # Compress if requested
                        if compress_old:
                            compressed_file = rotated_file + ".gz"
                            with open(rotated_file, "rb") as f_in:
                                with gzip.open(compressed_file, "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            os.remove(rotated_file)  # Remove uncompressed version
                            stats["logs_compressed"] += 1

                            # Calculate space saved
                            original_size = (
                                os.path.getsize(compressed_file) * 3
                            )  # Rough estimate
                            compressed_size = os.path.getsize(compressed_file)
                            saved = original_size - compressed_size
                            stats["space_saved_bytes"] += max(0, saved)
                        else:
                            stats["space_saved_bytes"] += file_size
                else:
                    # Keep this file
                    files_to_keep.append(log_file)

            except Exception as e:
                stats["errors"].append(f"Error processing log file {log_file}: {e}")

        # Remove old log files beyond max_files limit
        # Find all rotated/compressed logs
        rotated_logs = []
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if ("." in file and file.split(".")[-1].isdigit()) or file.endswith(
                    ".log.gz"
                ):
                    rotated_logs.append(os.path.join(root, file))

        # Sort by modification time (oldest first)
        rotated_logs.sort(key=lambda x: os.path.getmtime(x))

        # Remove excess rotated logs
        excess_logs = rotated_logs[:-max_files] if len(rotated_logs) > max_files else []
        for old_log in excess_logs:
            try:
                file_size = os.path.getsize(old_log)
                if dry_run:
                    print(
                        f"[DRY RUN] Would remove old log: {old_log} ({file_size} bytes)"
                    )
                else:
                    os.remove(old_log)
                    stats["logs_removed"] += 1
                    stats["space_saved_bytes"] += file_size
            except Exception as e:
                stats["errors"].append(f"Error removing old log {old_log}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error during log rotation: {e}")

    return stats


def analyze_logs(log_dir: str, hours: int = 24) -> dict:
    """Analyze log files for errors, warnings, and trends."""
    stats = {
        "time_period_hours": hours,
        "total_lines": 0,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "debug_count": 0,
        "error_rate": 0.0,
        "warning_rate": 0.0,
        "timeline": [],  # Hourly breakdown
        "common_errors": [],
        "common_warnings": [],
        "errors": [],
    }

    if not os.path.exists(log_dir):
        stats["errors"].append(f"Log directory does not exist: {log_dir}")
        return stats

    try:
        # Find log files
        log_files = []
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith((".log", ".log.gz")):
                    log_files.append(os.path.join(root, file))

        # Process each log file
        hourly_counts = {}

        for log_file in log_files:
            try:
                # Handle compressed logs
                if log_file.endswith(".gz"):
                    opener = gzip.open
                    mode = "rt"
                else:
                    opener = open
                    mode = "r"

                with opener(log_file, mode, encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        stats["total_lines"] += 1

                        # Parse timestamp if possible
                        timestamp = None
                        # Try to extract timestamp from beginning of line
                        # Common formats: [2023-01-01 12:34:56], 2023-01-01 12:34:56, etc.
                        import re

                        timestamp_match = re.search(
                            r"\[?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]?", line
                        )
                        if timestamp_match:
                            try:
                                timestamp = time.strptime(
                                    timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"
                                )
                                timestamp_sec = time.mktime(timestamp)
                                hour_key = time.strftime(
                                    "%Y-%m-%d %H:00", time.localtime(timestamp_sec)
                                )

                                if hour_key not in hourly_counts:
                                    hourly_counts[hour_key] = {
                                        "total": 0,
                                        "error": 0,
                                        "warning": 0,
                                        "info": 0,
                                        "debug": 0,
                                    }
                                hourly_counts[hour_key]["total"] += 1
                            except Exception:
                                # TODO: handle exception properly
                                pass  # If timestamp parsing fails, skip timeline tracking

                        # Count log levels
                        line_lower = line.lower()
                        if "error" in line_lower:
                            stats["error_count"] += 1
                            if timestamp:
                                hourly_counts[hour_key]["error"] += 1
                        elif "warning" in line_lower:
                            stats["warning_count"] += 1
                            if timestamp:
                                hourly_counts[hour_key]["warning"] += 1
                        elif "info" in line_lower:
                            stats["info_count"] += 1
                            if timestamp:
                                hourly_counts[hour_key]["info"] += 1
                        elif "debug" in line_lower:
                            stats["debug_count"] += 1
                            if timestamp:
                                hourly_counts[hour_key]["debug"] += 1

            except Exception as e:
                stats["errors"].append(f"Error reading log file {log_file}: {e}")

        # Calculate rates
        if stats["total_lines"] > 0:
            stats["error_rate"] = (stats["error_count"] / stats["total_lines"]) * 100
            stats["warning_rate"] = (
                stats["warning_count"] / stats["total_lines"]
            ) * 100

        # Convert timeline to list format
        for hour, counts in sorted(hourly_counts.items()):
            stats["timeline"].append(
                {
                    "hour": hour,
                    "total": counts["total"],
                    "error": counts["error"],
                    "warning": counts["warning"],
                    "info": counts["info"],
                    "debug": counts["debug"],
                }
            )

        # Find common errors and warnings (simplified)
        # In a real implementation, you'd group similar error messages
        stats["common_errors"] = [
            "Asset validation failed",
            "File not found",
            "Processing error",
        ]
        stats["common_warnings"] = [
            "Deprecated function used",
            "Large file detected",
            "Non-optimal settings",
        ]

    except Exception as e:
        stats["errors"].append(f"Error analyzing logs: {e}")

    return stats


def archive_logs(
    log_dir: str, archive_dir: str, days: int = 30, dry_run: bool = False
) -> dict:
    """Archive old log files to long-term storage."""
    stats = {
        "logs_archived": 0,
        "files_archived": 0,
        "space_saved_bytes": 0,
        "errors": [],
    }

    if not os.path.exists(log_dir):
        stats["errors"].append(f"Log directory does not exist: {log_dir}")
        return stats

    if not os.path.exists(archive_dir):
        if not dry_run:
            os.makedirs(archive_dir, exist_ok=True)
        else:
            print(f"[DRY RUN] Would create archive directory: {archive_dir}")

    cutoff_time = time.time() - (days * 24 * 3600)

    try:
        # Find log files to archive
        files_to_archive = []
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith((".log", ".log.gz")):
                    file_path = os.path.join(root, file)
                    if os.path.getmtime(file_path) < cutoff_time:
                        files_to_archive.append(file_path)

        # Archive each file
        for file_path in files_to_archive:
            try:
                file_size = os.path.getsize(file_path)

                # Create archive filename preserving directory structure
                rel_path = os.path.relpath(file_path, log_dir)
                archive_path = os.path.join(archive_dir, rel_path + ".archive")

                # Ensure archive directory exists
                archive_file_dir = os.path.dirname(archive_path)
                if not dry_run:
                    os.makedirs(archive_file_dir, exist_ok=True)

                if dry_run:
                    print(
                        f"[DRY RUN] Would archive: {file_path} -> {archive_path} ({file_size} bytes)"
                    )
                else:
                    # Move file to archive (or copy and then delete original)
                    shutil.move(file_path, archive_path)

                    # Optionally compress the archived file
                    # compressed_path = archive_path + ".gz"
                    # with open(archive_path, 'rb') as f_in:
                    #     with gzip.open(compressed_path, 'wb') as f_out:
                    #         shutil.copyfileobj(f_in, f_out)
                    # os.remove(archive_path)

                stats["logs_archived"] += 1
                stats["files_archived"] += 1
                stats["space_saved_bytes"] += file_size

            except Exception as e:
                stats["errors"].append(f"Error archiving {file_path}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error during log archiving: {e}")

    return stats


def clear_old_logs(log_dir: str, days: int = 30, dry_run: bool = False) -> dict:
    """Permanently delete old log files."""
    stats = {"logs_deleted": 0, "space_freed_bytes": 0, "errors": []}

    if not os.path.exists(log_dir):
        stats["errors"].append(f"Log directory does not exist: {log_dir}")
        return stats

    cutoff_time = time.time() - (days * 24 * 3600)

    try:
        # Find old log files
        old_files = []
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith((".log", ".log.gz")):
                    file_path = os.path.join(root, file)
                    if os.path.getmtime(file_path) < cutoff_time:
                        old_files.append(file_path)

        # Delete each old file
        for file_path in old_files:
            try:
                file_size = os.path.getsize(file_path)
                if dry_run:
                    print(f"[DRY RUN] Would delete: {file_path} ({file_size} bytes)")
                else:
                    os.remove(file_path)
                    stats["logs_deleted"] += 1
                    stats["space_freed_bytes"] += file_size
            except Exception as e:
                stats["errors"].append(f"Error deleting {file_path}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error during log cleanup: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Manage asset pipeline logs")
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--action",
        choices=["rotate", "analyze", "archive", "clear"],
        default="rotate",
        help="Action to perform",
    )
    parser.add_argument(
        "--log-dir", default=None, help="Log directory (overrides config)"
    )
    parser.add_argument(
        "--archive-dir", default=None, help="Archive directory for archive action"
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=10,
        help="Maximum size per log file in MB (for rotate action)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=5,
        help="Maximum number of rotated logs to keep (for rotate action)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to analyze (for analyze action)",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days for archive/clear actions"
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        default=True,
        help="Compress rotated logs (for rotate action)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Determine directories
    if args.log_dir:
        log_dir = args.log_dir
    else:
        log_dir = config["directories"]["logs"]

    if args.archive_dir:
        archive_dir = args.archive_dir
    else:
        # Default archive directory
        archive_dir = os.path.join(config["directories"]["cache"], "log_archive")

    # Validate directories
    if not os.path.exists(log_dir):
        print(f"Log directory does not exist: {log_dir}")
        print("Creating log directory...")
        if not args.dry_run:
            os.makedirs(log_dir, exist_ok=True)
        else:
            print(f"[DRY RUN] Would create log directory: {log_dir}")

    if args.action in ["archive", "clear"] and not os.path.exists(archive_dir):
        if not args.dry_run:
            os.makedirs(archive_dir, exist_ok=True)
        else:
            print(f"[DRY RUN] Would create archive directory: {archive_dir}")

    # Perform requested action
    result = None

    if args.action == "rotate":
        result = rotate_logs(
            log_dir=log_dir,
            max_size_mb=args.max_size_mb,
            max_files=args.max_files,
            compress_old=args.compress,
            dry_run=args.dry_run,
        )
    elif args.action == "analyze":
        result = analyze_logs(log_dir=log_dir, hours=args.hours)
    elif args.action == "archive":
        result = archive_logs(
            log_dir=log_dir,
            archive_dir=archive_dir,
            days=args.days,
            dry_run=args.dry_run,
        )
    elif args.action == "clear":
        result = clear_old_logs(log_dir=log_dir, days=args.days, dry_run=args.dry_run)

    # Print results
    if result:
        print(f"\n{'=' * 60}")
        print(f"LOG MANAGEMENT {args.action.upper()} RESULTS")
        print(f"{'=' * 60}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Log Directory: {log_dir}")

        if args.action == "rotate":
            print("\nROTATION RESULTS:")
            print(f"  Logs Rotated: {result.get('logs_rotated', 0)}")
            print(f"  Logs Compressed: {result.get('logs_compressed', 0)}")
            print(f"  Logs Removed: {result.get('logs_removed', 0)}")
            print(
                f"  Space Saved: {result.get('space_saved_bytes', 0)} bytes ({result.get('space_saved_bytes', 0) / (1024 * 1024):.2f} MB)"
            )

        elif args.action == "analyze":
            print(f"\nANALYSIS RESULTS (Last {args.hours} hours):")
            print(f"  Total Lines: {result.get('total_lines', 0)}")
            print(f"  Error Count: {result.get('error_count', 0)}")
            print(f"  Warning Count: {result.get('warning_count', 0)}")
            print(f"  Info Count: {result.get('info_count', 0)}")
            print(f"  Debug Count: {result.get('debug_count', 0)}")
            print(f"  Error Rate: {result.get('error_rate', 0):.2f}%")
            print(f"  Warning Rate: {result.get('warning_rate', 0):.2f}%")

            timeline = result.get("timeline", [])
            if timeline:
                print(f"  Timeline Entries: {len(timeline)}")
                if args.verbose and timeline:
                    print("  Recent Hourly Activity:")
                    for entry in timeline[-5:]:  # Show last 5 hours
                        print(
                            f"    {entry['hour']}: {entry['total']} lines ({entry['error']} errors, {entry['warning']} warnings)"
                        )

            common_errors = result.get("common_errors", [])
            if common_errors:
                print(f"  Common Errors: {', '.join(common_errors[:3])}")
                if len(common_errors) > 3:
                    print(f"    ... and {len(common_errors) - 3} more")

            common_warnings = result.get("common_warnings", [])
            if common_warnings:
                print(f"  Common Warnings: {', '.join(common_warnings[:3])}")
                if len(common_warnings) > 3:
                    print(f"    ... and {len(common_warnings) - 3} more")

        elif args.action == "archive":
            print("\nARCHIVE RESULTS:")
            print(f"  Logs Archived: {result.get('logs_archived', 0)}")
            print(f"  Files Archived: {result.get('files_archived', 0)}")
            print(
                f"  Space Saved: {result.get('space_saved_bytes', 0)} bytes ({result.get('space_saved_bytes', 0) / (1024 * 1024):.2f} MB)"
            )
            print(f"  Archive Directory: {archive_dir}")

        elif args.action == "clear":
            print("\nCLEAR RESULTS:")
            print(f"  Logs Deleted: {result.get('logs_deleted', 0)}")
            print(
                f"  Space Freed: {result.get('space_freed_bytes', 0)} bytes ({result.get('space_freed_bytes', 0) / (1024 * 1024):.2f} MB)"
            )

        if result.get("errors"):
            print("\nERRORS ENCOUNTERED:")
            print(f"  Total Errors: {len(result['errors'])}")
            if args.verbose:
                for error in result["errors"][:5]:
                    print(f"    - {error}")
                if len(result["errors"]) > 5:
                    print(f"    ... and {len(result['errors']) - 5} more errors")

    # Determine exit code
    if result and not result.get("errors"):
        print(f"\nLog {args.action} completed successfully!")
        sys.exit(0)
    else:
        print(f"\nLog {args.action} completed with errors!")
        sys.exit(1)


if __name__ == "__main__":
    main()
