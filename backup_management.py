#!/usr/bin/env python3
"""Backup management for naRou deployment."""

from __future__ import annotations

import argparse
import json
import logging
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

import yaml


class BackupManager:
    def __init__(self, backup_dir="backup_management"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.config_file = self.backup_dir / "config.yaml"
        self.index_file = self.backup_dir / "index.json"
        self.config = self._load_config()
        self.index = self._load_index()

    def _load_config(self):
        """Load backup configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "retention_count": 10,
            "retention_days": 30,
            "compression": "gzip",
            "include_patterns": ["**/*"],
            "exclude_patterns": [
                "**/__pycache__/**",
                "**/*.pyc",
                "**/.git/**",
                "**/node_modules/**",
            ],
        }

    def _load_index(self):
        """Load backup index."""
        if self.index_file.exists():
            with open(self.index_file) as f:
                return json.load(f)
        return {"backups": []}

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def save_index(self):
        """Save backup index."""
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def create_backup(self, name, source_paths, backup_type="full"):
        """Create a backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"

        print(f"Creating backup: {backup_name}")

        # Create tar.gz
        with tarfile.open(backup_path, "w:gz") as tar:
            for source in source_paths:
                source_path = Path(source)
                if source_path.exists():
                    if source_path.is_file():
                        tar.add(source_path, arcname=source_path.name)
                    else:
                        for file_path in source_path.rglob("*"):
                            if file_path.is_file():
                                # Check exclude patterns
                                excluded = False
                                for pattern in self.config.get("exclude_patterns", []):
                                    if file_path.match(pattern):
                                        excluded = True
                                        break
                                if not excluded:
                                    arcname = file_path.relative_to(source_path.parent)
                                    tar.add(file_path, arcname=str(arcname))

        # Update index
        backup_info = {
            "name": backup_name,
            "type": backup_type,
            "source_paths": source_paths,
            "path": str(backup_path),
            "size": backup_path.stat().st_size,
            "created_at": datetime.now().isoformat(),
            "checksum": self._calculate_checksum(backup_path),
        }

        self.index["backups"].append(backup_info)
        self.save_index()

        print(f"Backup created: {backup_path} ({backup_info['size']} bytes)")
        return backup_name

    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum."""
        import hashlib

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_backups(self, name_filter=None):
        """List backups."""
        backups = self.index["backups"]
        if name_filter:
            backups = [b for b in backups if name_filter in b["name"]]
        return sorted(backups, key=lambda b: b["created_at"], reverse=True)

    def get_backup(self, name):
        """Get backup info."""
        for backup in self.index["backups"]:
            if backup["name"] == name:
                return backup
        return None

    def restore_backup(self, name, target_dir=".", overwrite=False):
        """Restore from backup."""
        backup = self.get_backup(name)
        if not backup:
            print(f"Backup not found: {name}")
            return False

        backup_path = Path(backup["path"])
        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False

        print(f"Restoring backup: {name}")
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        with tarfile.open(backup_path, "r:gz") as tar:
            for member in tar.getmembers():
                dest = target_path / member.name
                if dest.exists() and not overwrite:
                    print(f"Skipping existing file: {dest}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                tar.extract(member, target_path)

        print(f"Restored to {target_dir}")
        return True

    def delete_backup(self, name):
        """Delete a backup."""
        backup = self.get_backup(name)
        if not backup:
            print(f"Backup not found: {name}")
            return False

        backup_path = Path(backup["path"])
        if backup_path.exists():
            backup_path.unlink()

        self.index["backups"] = [b for b in self.index["backups"] if b["name"] != name]
        self.save_index()

        print(f"Deleted backup: {name}")
        return True

    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        retention_count = self.config.get("retention_count", 10)
        retention_days = self.config.get("retention_days", 30)
        cutoff = datetime.now() - timedelta(days=retention_days)

        # Sort by date
        backups = sorted(self.index["backups"], key=lambda b: b["created_at"], reverse=True)

        # Keep by count
        to_delete = backups[retention_count:]

        # Also delete by age
        for backup in backups[:retention_count]:
            created = datetime.fromisoformat(backup["created_at"])
            if created < cutoff:
                to_delete.append(backup)

        # Remove duplicates
        to_delete = {b["name"]: b for b in to_delete}.values()

        for backup in to_delete:
            self.delete_backup(backup["name"])

        print(f"Cleaned up {len(to_delete)} old backups")
        return len(to_delete)

    def verify_backup(self, name):
        """Verify backup integrity."""
        backup = self.get_backup(name)
        if not backup:
            print(f"Backup not found: {name}")
            return False

        backup_path = Path(backup["path"])
        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False

        # Verify checksum
        current_checksum = self._calculate_checksum(backup_path)
        if current_checksum != backup["checksum"]:
            print(f"Checksum mismatch for {name}")
            return False

        # Verify tar integrity
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.getmembers()
        except Exception:
            logger.exception("ロード失敗")
            return False

        print(f"Backup {name} verified successfully")
        return True


def main():
    parser = argparse.ArgumentParser(description="Backup Management")
    parser.add_argument("--dir", default="backup_management", help="Backup directory")
    parser.add_argument(
        "--create", nargs=3, metavar=("NAME", "TYPE", "SOURCES"), help="Create backup"
    )
    parser.add_argument("--list", action="store_true", help="List backups")
    parser.add_argument("--restore", nargs=2, metavar=("NAME", "TARGET"), help="Restore backup")
    parser.add_argument("--delete", help="Delete backup")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old backups")
    parser.add_argument("--verify", help="Verify backup")
    args = parser.parse_args()

    mgr = BackupManager(args.dir)

    if args.create:
        sources = args.create[2].split(",")
        mgr.create_backup(args.create[0], sources, args.create[1])
    elif args.list:
        for backup in mgr.list_backups():
            print(
                f"{backup['name']} - {backup['type']} - {backup['size']} bytes - {backup['created_at']}"
            )
    elif args.restore:
        mgr.restore_backup(args.restore[0], args.restore[1])
    elif args.delete:
        mgr.delete_backup(args.delete)
    elif args.cleanup:
        mgr.cleanup_old_backups()
    elif args.verify:
        mgr.verify_backup(args.verify)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
