#!/usr/bin/env python3
"""Log management for naRou deployment."""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import argparse
import gzip
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import yaml


class LogManager:
    def __init__(self, log_dir="log_management"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.config_file = self.log_dir / "config.yaml"
        self.config = self._load_config()

    def _load_config(self):
        """Load log management configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "retention_days": 30,
            "max_size_mb": 100,
            "compress_after_days": 7,
            "archive_dir": "archives",
        }

    def save_config(self):
        """Save configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def collect_logs(self, source_dirs=None, pattern="*.log"):
        """Collect logs from source directories."""
        if source_dirs is None:
            source_dirs = ["logs", "tests/reports", "."]

        collected = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        collection_dir = self.log_dir / f"collection_{timestamp}"
        collection_dir.mkdir(parents=True)

        for source in source_dirs:
            source_path = Path(source)
            if source_path.exists():
                for log_file in source_path.rglob(pattern):
                    if log_file.is_file():
                        dest = collection_dir / log_file.relative_to(source_path)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(log_file, dest)
                        collected.append(str(dest))

        print(f"Collected {len(collected)} log files to {collection_dir}")
        return collection_dir

    def compress_logs(self, log_dir=None):
        """Compress log files older than threshold."""
        if log_dir is None:
            log_dir = self.log_dir

        log_dir = Path(log_dir)
        threshold_days = self.config.get("compress_after_days", 7)
        cutoff = datetime.now() - timedelta(days=threshold_days)

        compressed = 0
        for log_file in log_dir.rglob("*.log"):
            if log_file.is_file():
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    gz_file = log_file.with_suffix(log_file.suffix + ".gz")
                    with open(log_file, "rb") as f_in:
                        with gzip.open(gz_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()
                    compressed += 1

        print(f"Compressed {compressed} log files")
        return compressed

    def archive_logs(self, source_dir=None, archive_name=None):
        """Archive logs to compressed tarball."""
        if source_dir is None:
            # Find latest collection
            collections = sorted(self.log_dir.glob("collection_*"))
            if not collections:
                print("No collections found")
                return None
            source_dir = collections[-1]

        source_dir = Path(source_dir)
        if not source_dir.exists():
            print(f"Source directory not found: {source_dir}")
            return None

        if archive_name is None:
            archive_name = f"logs_{source_dir.name}.tar.gz"

        archive_dir = self.log_dir / self.config.get("archive_dir", "archives")
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / archive_name

        shutil.make_archive(str(archive_path.with_suffix("")), "gztar", source_dir)

        # Remove source after archiving
        shutil.rmtree(source_dir)

        print(f"Archived logs to {archive_path}")
        return archive_path

    def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        retention_days = self.config.get("retention_days", 30)
        cutoff = datetime.now() - timedelta(days=retention_days)

        removed = 0
        for log_file in self.log_dir.rglob("*"):
            if log_file.is_file():
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    removed += 1

        # Remove empty directories
        for dir_path in sorted(self.log_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()

        print(f"Removed {removed} old log files")
        return removed

    def rotate_logs(self, log_file, max_size_mb=None):
        """Rotate a log file if it exceeds max size."""
        log_file = Path(log_file)
        if not log_file.exists():
            return False

        if max_size_mb is None:
            max_size_mb = self.config.get("max_size_mb", 100)

        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb < max_size_mb:
            return False

        # Rotate
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_file.with_name(f"{log_file.stem}_{timestamp}{log_file.suffix}")
        log_file.rename(rotated)

        # Compress rotated log
        gz_file = rotated.with_suffix(rotated.suffix + ".gz")
        with open(rotated, "rb") as f_in, gzip.open(gz_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        rotated.unlink()

        print(f"Rotated {log_file} to {gz_file}")
        return True

    def search_logs(self, query, log_dir=None, pattern="*.log"):
        """Search logs for query string."""
        if log_dir is None:
            log_dir = self.log_dir

        log_dir = Path(log_dir)
        matches = []

        for log_file in log_dir.rglob(pattern):
            if log_file.is_file():
                try:
                    if log_file.suffix == ".gz":
                        opener = gzip.open
                        mode = "rt"
                    else:
                        opener = open
                        mode = "r"

                    with opener(log_file, mode) as f:
                        for i, line in enumerate(f, 1):
                            if query in line:
                                matches.append(
                                    {
                                        "file": str(log_file),
                                        "line": i,
                                        "content": line.strip(),
                                    }
                                )
                except Exception as e:
                    logger.exception("Unhandled exception")
                    print(f"Error reading {log_file}: {e}")

        return matches

    def get_stats(self):
        """Get log statistics."""
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "compressed_files": 0,
            "archived_files": 0,
        }

        for log_file in self.log_dir.rglob("*"):
            if log_file.is_file():
                stats["total_files"] += 1
                stats["total_size_mb"] += log_file.stat().st_size / (1024 * 1024)
                if log_file.suffix == ".gz":
                    stats["compressed_files"] += 1
                if "archives" in str(log_file):
                    stats["archived_files"] += 1

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats


def main():
    parser = argparse.ArgumentParser(description="Log Management")
    parser.add_argument("--dir", default="log_management", help="Log directory")
    parser.add_argument("--collect", nargs="*", help="Collect logs from directories")
    parser.add_argument("--compress", action="store_true", help="Compress old logs")
    parser.add_argument("--archive", nargs="?", const=True, help="Archive logs")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old logs")
    parser.add_argument("--rotate", help="Rotate log file")
    parser.add_argument("--search", help="Search logs")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    args = parser.parse_args()

    mgr = LogManager(args.dir)

    if args.collect is not None:
        dirs = args.collect if args.collect else None
        mgr.collect_logs(dirs)
    elif args.compress:
        mgr.compress_logs()
    elif args.archive:
        source = args.archive if isinstance(args.archive, str) else None
        mgr.archive_logs(source)
    elif args.cleanup:
        mgr.cleanup_old_logs()
    elif args.rotate:
        mgr.rotate_logs(args.rotate)
    elif args.search:
        matches = mgr.search_logs(args.search)
        for match in matches[:50]:
            print(f"{match['file']}:{match['line']}: {match['content']}")
        print(f"Total matches: {len(matches)}")
    elif args.stats:
        stats = mgr.get_stats()
        print(json.dumps(stats, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
