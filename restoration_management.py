#!/usr/bin/env python3
"""Restoration management for naRou deployment."""

from __future__ import annotations

import argparse
import json
import tarfile
from datetime import datetime
from pathlib import Path

import yaml


class RestorationManager:
    def __init__(self, restoration_dir="restoration_management"):
        self.restoration_dir = Path(restoration_dir)
        self.restoration_dir.mkdir(exist_ok=True)
        self.config_file = self.restoration_dir / "config.yaml"
        self.history_file = self.restoration_dir / "history.json"
        self.config = self._load_config()
        self.history = self._load_history()

    def _load_config(self):
        """Load restoration configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "backup_dirs": ["backup_management", "backups"],
            "default_target": ".",
            "verify_checksums": True,
            "create_restore_point": True,
        }

    def _load_history(self):
        """Load restoration history."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return {"restorations": []}

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def save_history(self):
        """Save restoration history."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def find_backups(self, name_pattern=None):
        """Find available backups across backup directories."""
        backups = []

        for backup_dir in self.config.get("backup_dirs", []):
            backup_path = Path(backup_dir)
            if backup_path.exists():
                # Check for index.json
                index_file = backup_path / "index.json"
                if index_file.exists():
                    with open(index_file) as f:
                        index = json.load(f)
                        for backup in index.get("backups", []):
                            if name_pattern is None or name_pattern in backup["name"]:
                                backup["source_dir"] = backup_dir
                                backups.append(backup)
                else:
                    # Scan for tar.gz files
                    for backup_file in backup_path.glob("*.tar.gz"):
                        if name_pattern is None or name_pattern in backup_file.stem:
                            stat = backup_file.stat()
                            backups.append(
                                {
                                    "name": backup_file.stem,
                                    "path": str(backup_file),
                                    "size": stat.st_size,
                                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "source_dir": backup_dir,
                                }
                            )

        return sorted(backups, key=lambda b: b["created_at"], reverse=True)

    def create_restore_point(self, name, target_dir="."):
        """Create a restore point before restoration."""
        if not self.config.get("create_restore_point", True):
            return None

        target_path = Path(target_dir)
        if not target_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        restore_point_name = f"restore_point_{name}_{timestamp}"
        restore_point_path = self.restoration_dir / f"{restore_point_name}.tar.gz"

        print(f"Creating restore point: {restore_point_name}")

        with tarfile.open(restore_point_path, "w:gz") as tar:
            for file_path in target_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(target_path)
                    tar.add(file_path, arcname=str(arcname))

        return {
            "name": restore_point_name,
            "path": str(restore_point_path),
            "target_dir": str(target_path),
            "created_at": datetime.now().isoformat(),
        }

    def restore(self, backup_name, target_dir=".", restore_point=None):
        """Restore from backup."""
        # Find backup
        backups = self.find_backups(backup_name)
        if not backups:
            print(f"Backup not found: {backup_name}")
            return False

        backup = backups[0]  # Use most recent
        backup_path = Path(backup["path"])

        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Create restore point if enabled
        rp = None
        if restore_point is None:
            restore_point = self.config.get("create_restore_point", True)

        if restore_point:
            rp = self.create_restore_point(backup_name, target_dir)

        # Verify checksum if enabled
        if self.config.get("verify_checksums", True) and "checksum" in backup:
            import hashlib

            sha256 = hashlib.sha256()
            with open(backup_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            if sha256.hexdigest() != backup["checksum"]:
                print("Checksum verification failed!")
                return False

        print(f"Restoring {backup_name} to {target_dir}")

        # Extract backup
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(target_path)

        # Record restoration
        restoration_record = {
            "backup_name": backup_name,
            "backup_path": str(backup_path),
            "target_dir": str(target_path),
            "restore_point": rp["name"] if rp else None,
            "restored_at": datetime.now().isoformat(),
            "status": "completed",
        }

        self.history["restorations"].append(restoration_record)
        self.save_history()

        print("Restoration completed successfully")
        return True

    def restore_selective(self, backup_name, patterns, target_dir="."):
        """Restore only files matching patterns."""
        backups = self.find_backups(backup_name)
        if not backups:
            print(f"Backup not found: {backup_name}")
            return False

        backup = backups[0]
        backup_path = Path(backup["path"])

        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        print(f"Selective restore from {backup_name} for patterns: {patterns}")

        restored = 0
        with tarfile.open(backup_path, "r:gz") as tar:
            for member in tar.getmembers():
                for pattern in patterns:
                    if Path(member.name).match(pattern):
                        tar.extract(member, target_path)
                        restored += 1
                        break

        print(f"Restored {restored} files")
        return True

    def list_restore_points(self):
        """List available restore points."""
        restore_points = []
        for rp_file in self.restoration_dir.glob("restore_point_*.tar.gz"):
            stat = rp_file.stat()
            restore_points.append(
                {
                    "name": rp_file.stem,
                    "path": str(rp_file),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        return sorted(restore_points, key=lambda r: r["created_at"], reverse=True)

    def rollback_to_restore_point(self, restore_point_name, target_dir="."):
        """Rollback to a restore point."""
        restore_points = self.list_restore_points()
        rp = next((r for r in restore_points if r["name"] == restore_point_name), None)

        if not rp:
            print(f"Restore point not found: {restore_point_name}")
            return False

        rp_path = Path(rp["path"])
        target_path = Path(target_dir)

        print(f"Rolling back to restore point: {restore_point_name}")

        with tarfile.open(rp_path, "r:gz") as tar:
            tar.extractall(target_path)

        print("Rollback completed")
        return True

    def get_history(self):
        """Get restoration history."""
        return self.history["restorations"]


def main():
    parser = argparse.ArgumentParser(description="Restoration Management")
    parser.add_argument("--dir", default="restoration_management", help="Restoration directory")
    parser.add_argument("--find", nargs="?", const=True, help="Find backups")
    parser.add_argument("--restore", nargs=2, metavar=("BACKUP", "TARGET"), help="Restore backup")
    parser.add_argument(
        "--selective",
        nargs=3,
        metavar=("BACKUP", "PATTERNS", "TARGET"),
        help="Selective restore",
    )
    parser.add_argument("--list-rp", action="store_true", help="List restore points")
    parser.add_argument(
        "--rollback",
        nargs=2,
        metavar=("RESTORE_POINT", "TARGET"),
        help="Rollback to restore point",
    )
    parser.add_argument("--history", action="store_true", help="Show restoration history")
    args = parser.parse_args()

    mgr = RestorationManager(args.dir)

    if args.find is not None:
        pattern = args.find if isinstance(args.find, str) else None
        backups = mgr.find_backups(pattern)
        for backup in backups:
            print(
                f"{backup['name']} - {backup['size']} bytes - {backup['created_at']} ({backup['source_dir']})"
            )
    elif args.restore:
        mgr.restore(args.restore[0], args.restore[1])
    elif args.selective:
        patterns = args.selective[1].split(",")
        mgr.restore_selective(args.selective[0], patterns, args.selective[2])
    elif args.list_rp:
        for rp in mgr.list_restore_points():
            print(f"{rp['name']} - {rp['size']} bytes - {rp['created_at']}")
    elif args.rollback:
        mgr.rollback_to_restore_point(args.rollback[0], args.rollback[1])
    elif args.history:
        for restoration in mgr.get_history():
            print(
                f"{restoration['restored_at']} - {restoration['backup_name']} -> {restoration['target_dir']} ({restoration['status']})"
            )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
