#!/usr/bin/env python3
"""
Asset restoration script for restoring assets from backups.
Supports restoring from full backups, incremental backups, and specific points in time.
"""

import argparse
import json
import os
import shutil
import sys
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def restore_from_backup(backup_source: str, restore_target: str, config: dict) -> dict:
    """Restore assets from a backup directory."""
    stats = {
        "restore_type": "full_from_backup",
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backup_source": backup_source,
        "restore_target": restore_target,
        "files_restored": 0,
        "files_skipped": 0,
        "total_size_bytes": 0,
        "errors": [],
    }

    try:
        print(f"Restoring from backup: {backup_source} to {restore_target}")

        # Check if backup source exists
        if not os.path.exists(backup_source):
            stats["errors"].append(f"Backup source does not exist: {backup_source}")
            return stats

        # Check for backup manifest
        manifest_path = os.path.join(backup_source, "backup_manifest.json")
        backup_info = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                backup_info = manifest.get("backup_info", {})
                print(f"Backup type: {backup_info.get('backup_type', 'unknown')}")
                print(f"Backup time: {backup_info.get('datetime', 'unknown')}")
            except Exception as e:
                stats["errors"].append(f"Error reading backup manifest: {e}")

        # Create restore target directory
        os.makedirs(restore_target, exist_ok=True)

        # Walk through backup directory and restore files
        for root, dirs, files in os.walk(backup_source):
            # Skip the manifest file
            if "backup_manifest.json" in files:
                files.remove("backup_manifest.json")

            # Create corresponding directories in target
            for dir_name in dirs:
                src_dir = os.path.join(root, dir_name)
                rel_path = os.path.relpath(src_dir, backup_source)
                dst_dir = os.path.join(restore_target, rel_path)
                os.makedirs(dst_dir, exist_ok=True)

            # Copy files
            for file_name in files:
                src_file = os.path.join(root, file_name)
                rel_path = os.path.relpath(src_file, backup_source)
                dst_file = os.path.join(restore_target, rel_path)

                try:
                    # Copy file
                    shutil.copy2(src_file, dst_file)

                    # Update stats
                    file_size = os.path.getsize(src_file)
                    stats["files_restored"] += 1
                    stats["total_size_bytes"] += file_size

                except Exception as e:
                    stats["files_skipped"] += 1
                    stats["errors"].append(f"Error restoring {src_file}: {e}")

        print(
            f"Restore completed: {stats['files_restored']} files, {stats['total_size_bytes']} bytes"
        )

    except Exception as e:
        stats["errors"].append(f"Restore failed: {e}")

    return stats


def restore_specific_files(
    backup_source: str, restore_target: str, file_list: list[str], config: dict
) -> dict:
    """Restore specific files from a backup."""
    stats = {
        "restore_type": "selective",
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backup_source": backup_source,
        "restore_target": restore_target,
        "files_requested": len(file_list),
        "files_restored": 0,
        "files_not_found": 0,
        "files_skipped": 0,
        "total_size_bytes": 0,
        "errors": [],
    }

    try:
        print(f"Restoring specific files from {backup_source} to {restore_target}")
        print(f"Number of files requested: {len(file_list)}")

        # Check if backup source exists
        if not os.path.exists(backup_source):
            stats["errors"].append(f"Backup source does not exist: {backup_source}")
            return stats

        # Create restore target directory
        os.makedirs(restore_target, exist_ok=True)

        # Restore each requested file
        for rel_path in file_list:
            src_file = os.path.join(backup_source, rel_path)
            dst_file = os.path.join(restore_target, rel_path)

            # Ensure destination directory exists
            dst_dir = os.path.dirname(dst_file)
            if dst_dir:
                os.makedirs(dst_dir, exist_ok=True)

            if os.path.exists(src_file):
                try:
                    # Copy file
                    shutil.copy2(src_file, dst_file)

                    # Update stats
                    file_size = os.path.getsize(src_file)
                    stats["files_restored"] += 1
                    stats["total_size_bytes"] += file_size

                except Exception as e:
                    stats["files_skipped"] += 1
                    stats["errors"].append(f"Error restoring {src_file}: {e}")
            else:
                stats["files_not_found"] += 1
                stats["errors"].append(f"File not found in backup: {rel_path}")

        print(
            f"Selective restore completed: {stats['files_restored']} files restored, {stats['files_not_found']} not found"
        )

    except Exception as e:
        stats["errors"].append(f"Selective restore failed: {e}")

    return stats


def list_available_backups(backup_dir: str) -> list[dict]:
    """List available backups in a backup directory."""
    backups = []

    if not os.path.exists(backup_dir):
        return backups

    try:
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            if os.path.isdir(item_path):
                # Try to get backup information from manifest
                manifest_path = os.path.join(item_path, "backup_manifest.json")
                backup_info = {
                    "name": item,
                    "path": item_path,
                    "timestamp": None,
                    "datetime": None,
                    "type": "unknown",
                    "size_bytes": 0,
                    "file_count": 0,
                }

                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        info = manifest.get("backup_info", {})
                        backup_info["timestamp"] = info.get("timestamp")
                        backup_info["datetime"] = info.get("datetime")
                        backup_info["type"] = info.get("backup_type", "unknown")
                    except Exception:
                        pass

                # Calculate backup size and file count
                try:
                    size = 0
                    count = 0
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            if file != "backup_manifest.json":
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    try:
                                        size += os.path.getsize(file_path)
                                        count += 1
                                    except Exception:
                                        pass
                    backup_info["size_bytes"] = size
                    backup_info["file_count"] = count
                except Exception:
                    pass

                # Fallback to filesystem timestamps
                if backup_info["timestamp"] is None:
                    backup_info["timestamp"] = os.path.getmtime(item_path)
                    backup_info["datetime"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(backup_info["timestamp"])
                    )

                backups.append(backup_info)

    except Exception as e:
        print(f"Error listing backups: {e}")

    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return backups


def main():
    parser = argparse.ArgumentParser(description="Restore assets from backups")
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--backup-source",
        required=True,
        help="Backup source directory or backup identifier",
    )
    parser.add_argument(
        "--restore-target", required=True, help="Target directory to restore assets to"
    )
    parser.add_argument(
        "--list-backups", action="store_true", help="List available backups and exit"
    )
    parser.add_argument(
        "--files", nargs="+", help="Specific files to restore (relative to backup root)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Handle list backups request
    if args.list_backups:
        # Determine backup directory
        if os.path.isdir(args.backup_source):
            backup_dir = args.backup_source
        else:
            # Assume it's a backup name within the configured backup directory
            backup_config = config.get("backup", {})
            backup_dir = os.path.join(
                config["directories"].get("cache", "assets/cache"),
                "backups",
                args.backup_source,
            )
            if not os.path.exists(backup_dir):
                backup_dir = os.path.join(
                    config["directories"].get("output", "assets/build"),
                    "backups",
                    args.backup_source,
                )

        backups = list_available_backups(backup_dir)

        print(f"\nAvailable backups in: {backup_dir}")
        print(f"{'=' * 80}")
        if not backups:
            print("No backups found.")
        else:
            for backup in backups:
                print(f"Name: {backup['name']}")
                print(f"  Path: {backup['path']}")
                print(f"  Type: {backup['type']}")
                print(f"  Date: {backup['datetime']}")
                print(f"  Size: {backup['size_bytes'] / (1024 * 1024):.2f} MB")
                print(f"  Files: {backup['file_count']}")
                print()
        sys.exit(0)

    # Determine actual backup source path
    backup_source = args.backup_source
    if not os.path.exists(backup_source):
        # Try to find it in configured backup locations
        backup_dirs_to_check = [
            config["directories"].get("cache", "assets/cache"),
            config["directories"].get("output", "assets/build"),
            "./backups",
            "./assets/backups",
        ]

        found = False
        for base_dir in backup_dirs_to_check:
            if base_dir and os.path.exists(base_dir):
                potential_path = os.path.join(base_dir, args.backup_source)
                if os.path.exists(potential_path):
                    backup_source = potential_path
                    found = True
                    break

        if not found:
            print(f"Error: Backup source not found: {args.backup_source}")
            print("Searched in:")
            for base_dir in backup_dirs_to_check:
                if base_dir:
                    print(f"  {os.path.join(base_dir, args.backup_source)}")
            sys.exit(1)

    # Ensure restore target directory exists
    os.makedirs(args.restore_target, exist_ok=True)

    # Perform restoration
    result = None

    if args.files:
        # Restore specific files
        result = restore_specific_files(
            backup_source, args.restore_target, args.files, config
        )
    else:
        # Restore entire backup
        result = restore_from_backup(backup_source, args.restore_target, config)

    # Print results
    if result:
        print(f"\n{'=' * 60}")
        print("RESTORE OPERATION RESULTS")
        print(f"{'=' * 60}")
        print(f"Operation: {result.get('restore_type', 'unknown')}")
        print(f"Timestamp: {result.get('datetime', 'N/A')}")
        print(f"Backup Source: {result.get('backup_source', 'N/A')}")
        print(f"Restore Target: {result.get('restore_target', 'N/A')}")

        if result.get("restore_type") == "full_from_backup":
            print(f"Files Restored: {result.get('files_restored', 0)}")
            print(f"Files Skipped: {result.get('files_skipped', 0)}")
            print(f"Total Size: {result.get('total_size_bytes', 0)} bytes")

        elif result.get("restore_type") == "selective":
            print(f"Files Requested: {result.get('files_requested', 0)}")
            print(f"Files Restored: {result.get('files_restored', 0)}")
            print(f"Files Not Found: {result.get('files_not_found', 0)}")
            print(f"Files Skipped: {result.get('files_skipped', 0)}")
            print(f"Total Size: {result.get('total_size_bytes', 0)} bytes")

        if result.get("errors"):
            print(f"Errors: {len(result['errors'])}")
            if args.verbose:
                for error in result["errors"][:5]:
                    print(f"  - {error}")
                if len(result["errors"]) > 5:
                    print(f"  ... and {len(result['errors']) - 5} more errors")

    # Determine exit code
    if result and not result.get("errors"):
        print("\nRestore completed successfully!")
        sys.exit(0)
    else:
        print("\nRestore completed with errors!")
        sys.exit(1)


if __name__ == "__main__":
    main()
