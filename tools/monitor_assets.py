#!/usr/bin/env python3
"""
Asset monitoring script for monitoring asset pipeline performance, health, and metrics.
Tracks build times, asset counts, resource usage, and trends.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return json.load(f)


def get_pipeline_metrics(config: dict) -> dict:
    """Get current pipeline metrics and status."""
    metrics = {
        "timestamp": time.time(),
        "datetime": datetime.datetime.fromtimestamp(time.time()).isoformat(),
        "pipeline_health": "unknown",
        "assets": {},
        "performance": {},
        "storage": {},
        "trends": {},
    }

    # Asset counts and sizes
    asset_types = ["tilesets", "fonts", "sounds", "models"]
    total_files = 0
    total_size = 0

    for asset_type in asset_types:
        asset_dir = os.path.join(config["directories"]["output"], asset_type)
        asset_info = {
            "file_count": 0,
            "total_size_bytes": 0,
            "avg_file_size": 0,
            "largest_file": None,
            "smallest_file": None,
        }

        if os.path.exists(asset_dir):
            file_sizes = []
            largest_file = {"path": "", "size": 0}
            smallest_file = {"path": "", "size": float("inf")}

            for root, dirs, files in os.walk(asset_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            file_sizes.append(file_size)
                            total_size += file_size
                            total_files += 1

                            if file_size > largest_file["size"]:
                                largest_file = {"path": file_path, "size": file_size}
                            if file_size < smallest_file["size"]:
                                smallest_file = {"path": file_path, "size": file_size}
                        except Exception:
                            # TODO: handle exception properly
                            pass  # Skip files we can't read

            asset_info["file_count"] = len(file_sizes)
            asset_info["total_size_bytes"] = sum(file_sizes) if file_sizes else 0
            asset_info["avg_file_size"] = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            asset_info["largest_file"] = largest_file if largest_file["size"] > 0 else None
            asset_info["smallest_file"] = (
                smallest_file if smallest_file["size"] != float("inf") else None
            )

        metrics["assets"][asset_type] = asset_info

    metrics["assets"]["total_files"] = total_files
    metrics["assets"]["total_size_bytes"] = total_size

    # Performance metrics (from recent builds)
    metrics["performance"] = get_performance_metrics(config)

    # Storage metrics
    metrics["storage"] = get_storage_metrics(config)

    # Determine pipeline health
    metrics["pipeline_health"] = determine_pipeline_health(metrics)

    return metrics


def get_performance_metrics(config: dict) -> dict:
    """Get performance metrics from recent pipeline runs."""
    perf_metrics = {
        "last_build_time": None,
        "average_build_time": None,
        "build_success_rate": None,
        "recent_builds": [],
    }

    # Look for build logs or metrics files
    logs_dir = config["directories"]["logs"]
    if os.path.exists(logs_dir):
        try:
            # Look for recent log files
            log_files = []
            for root, dirs, files in os.walk(logs_dir):
                for file in files:
                    if file.endswith(".log") or "pipeline" in file.lower():
                        log_files.append(os.path.join(root, file))

            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Process recent logs for build times
            build_times = []
            success_count = 0
            total_count = 0

            for log_file in log_files[:10]:  # Check last 10 log files
                try:
                    with open(log_file) as f:
                        content = f.read()

                    # Simple parsing for build completion and timing
                    if "PIPELINE EXECUTION SUMMARY" in content:
                        total_count += 1
                        if "All steps completed successfully" in content:
                            success_count += 1

                        # Extract build time
                        import re

                        time_match = re.search(r"Total duration: (\d+\.?\d*) seconds", content)
                        if time_match:
                            build_times.append(float(time_match.group(1)))
                except Exception:
                    # TODO: handle exception properly
                    pass  # Skip unreadable logs

            if build_times:
                perf_metrics["last_build_time"] = build_times[0] if build_times else None
                perf_metrics["average_build_time"] = sum(build_times) / len(build_times)

            if total_count > 0:
                perf_metrics["build_success_rate"] = (success_count / total_count) * 100

            perf_metrics["recent_builds"] = total_count
        except Exception:
            # TODO: handle exception properly
            pass  # If we can't read logs, leave metrics as None

    return perf_metrics


def get_storage_metrics(config: dict) -> dict:
    """Get storage usage metrics."""
    storage_metrics = {
        "output_directory_size": 0,
        "temp_directory_size": 0,
        "cache_directory_size": 0,
        "logs_directory_size": 0,
        "source_directory_size": 0,
    }

    dirs_to_check = [
        ("output_directory_size", "output"),
        ("temp_directory_size", "temp"),
        ("cache_directory_size", "cache"),
        ("logs_directory_size", "logs"),
        ("source_directory_size", "source"),
    ]

    for metric_key, dir_key in dirs_to_check:
        dir_path = config["directories"].get(dir_key)
        if dir_path and os.path.exists(dir_path):
            try:
                total_size = 0
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            try:
                                total_size += os.path.getsize(file_path)
                            except Exception:
                                # TODO: handle exception properly
                                pass
                storage_metrics[metric_key] = total_size
            except Exception:
                # TODO: handle exception properly
                pass  # If we can't calculate size, leave as 0

    return storage_metrics


def determine_pipeline_health(metrics: dict) -> str:
    """Determine overall pipeline health based on metrics."""
    # Simple health scoring
    health_score = 100

    # Check for missing assets
    total_files = metrics["assets"].get("total_files", 0)
    if total_files == 0:
        health_score -= 30  # No assets is concerning

    # Check build success rate
    success_rate = metrics["performance"].get("build_success_rate")
    if success_rate is not None:
        if success_rate < 50:
            health_score -= 40
        elif success_rate < 80:
            health_score -= 20

    # Check for extremely large files (potential issues)
    largest_asset_size = 0
    for asset_type in ["tilesets", "fonts", "sounds", "models"]:
        asset_info = metrics["assets"].get(asset_type, {})
        largest_file = asset_info.get("largest_file")
        if largest_file and largest_file.get("size", 0) > largest_asset_size:
            largest_asset_size = largest_file["size"]

    # Warn if any single asset is > 50MB
    if largest_asset_size > 50 * 1024 * 1024:
        health_score -= 20

    # Determine health status
    if health_score >= 90:
        return "excellent"
    elif health_score >= 75:
        return "good"
    elif health_score >= 60:
        return "fair"
    elif health_score >= 40:
        return "poor"
    else:
        return "critical"


def get_trend_data(config: dict) -> dict:
    """Get trend data from historical metrics."""
    # In a real implementation, this would read from a metrics database or time-series storage
    # For this basic implementation, we'll return placeholder data
    return {
        "asset_growth_daily": 0,  # assets added per day
        "build_time_trend": "stable",  # improving, degrading, stable
        "storage_trend": "stable",
        "error_rate_trend": "stable",
    }


def save_metrics(metrics: dict, output_path: str) -> bool:
    """Save metrics to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Metrics saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving metrics: {e}")
        return False


def print_metrics_summary(metrics: dict):
    """Print a formatted summary of the metrics."""
    print(f"\n{'=' * 60}")
    print("ASSET PIPELINE MONITORING REPORT")
    print(f"{'=' * 60}")
    print(f"Timestamp: {metrics['datetime']}")
    print(f"Pipeline Health: {metrics['pipeline_health'].upper()}")

    print("\nASSET STATISTICS:")
    assets = metrics["assets"]
    print(f"  Total Files: {assets.get('total_files', 0)}")
    print(f"  Total Size: {assets.get('total_size_bytes', 0) / (1024 * 1024):.2f} MB")

    for asset_type in ["tilesets", "fonts", "sounds", "models"]:
        asset_info = assets.get(asset_type, {})
        count = asset_info.get("file_count", 0)
        size_mb = asset_info.get("total_size_bytes", 0) / (1024 * 1024)
        print(f"  {asset_type.capitalize()}: {count} files ({size_mb:.2f} MB)")

    print("\nPERFORMANCE METRICS:")
    perf = metrics["performance"]
    if perf.get("last_build_time") is not None:
        print(f"  Last Build Time: {perf['last_build_time']:.2f} seconds")
    if perf.get("average_build_time") is not None:
        print(f"  Average Build Time: {perf['average_build_time']:.2f} seconds")
    if perf.get("build_success_rate") is not None:
        print(f"  Build Success Rate: {perf['build_success_rate']:.1f}%")
    print(f"  Recent Builds Processed: {perf.get('recent_builds', 0)}")

    print("\nSTORAGE USAGE:")
    storage = metrics["storage"]
    for dir_name, size_bytes in storage.items():
        size_mb = size_bytes / (1024 * 1024)
        print(f"  {dir_name.replace('_', ' ').title()}: {size_mb:.2f} MB")

    print("\nTREND DATA:")
    trends = metrics.get("trends", {})
    for trend_name, trend_value in trends.items():
        print(f"  {trend_name.replace('_', ' ').title()}: {trend_value}")


def main():
    parser = argparse.ArgumentParser(description="Monitor asset pipeline health and performance")
    parser.add_argument(
        "--config",
        default="tools/asset_pipeline_config.json",
        help="Path to configuration file",
    )
    parser.add_argument("--output", default=None, help="Output file for metrics (JSON)")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only summary, not full JSON output",
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run in continuous monitoring mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval in seconds for continuous mode (default: 5 minutes)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    def run_monitoring_cycle():
        """Run a single monitoring cycle."""
        # Get metrics
        metrics = get_pipeline_metrics(config)

        # Add trend data
        metrics["trends"] = get_trend_data(config)

        # Output based on args
        if args.output and not save_metrics(metrics, args.output):
            sys.exit(1)

        if not args.summary_only and not args.continuous:
            # Print full JSON if requested
            print(json.dumps(metrics, indent=2))
        elif args.summary_only or args.continuous:
            # Print formatted summary
            print_metrics_summary(metrics)

        return metrics

    if args.continuous:
        print(f"Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        try:
            while True:
                run_monitoring_cycle()
                print(f"\nNext update in {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            sys.exit(0)
    else:
        # Single run
        run_monitoring_cycle()
        sys.exit(0)


if __name__ == "__main__":
    main()
