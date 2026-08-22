#!/usr/bin/env python3
"""Playtest log analyzer - generates distribution tables and statistics."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from collections import Counter
from datetime import datetime


def load_latest_logs(log_dir: str = "playtest_logs") -> tuple[list[dict], list[dict]]:
    """Load the latest playtest and summary logs."""
    log_path = Path(log_dir)
    playtest_files = sorted(log_path.glob("playtest_*.json"))
    summary_files = sorted(log_path.glob("summary_*.json"))
    
    if not playtest_files:
        print("No playtest logs found.")
        return [], []
    
    latest_playtest = playtest_files[-1]
    latest_summary = summary_files[-1] if summary_files else None
    
    with open(latest_playtest, encoding="utf-8") as f:
        runs = json.load(f)
    
    summary = {}
    if latest_summary:
        with open(latest_summary, encoding="utf-8") as f:
            summary = json.load(f)
    
    return runs, summary


def analyze_distributions(runs: list[dict]) -> dict[str, Any]:
    """Analyze distributions from playthrough data."""
    if not runs:
        return {}
    
    total = len(runs)
    survived = [r for r in runs if r.get("survived")]
    died = [r for r in runs if not r.get("survived")]
    
    # Survival time distribution (turns)
    survival_turns = [r["total_turns"] for r in survived]
    death_turns = [r["total_turns"] for r in died]
    all_turns = [r["total_turns"] for r in runs]
    
    # Dungeon level distribution
    depths = [r["max_dungeon_level"] for r in runs]
    survived_depths = [r["max_dungeon_level"] for r in survived]
    died_depths = [r["max_dungeon_level"] for r in died]
    
    # Level distribution
    levels = [r["final_level"] for r in runs]
    survived_levels = [r["final_level"] for r in survived]
    died_levels = [r["final_level"] for r in died]
    
    # Strategy distribution
    strategies = [r.get("strategy", "unknown") for r in runs]
    strategy_survival = {}
    for r in runs:
        strat = r.get("strategy", "unknown")
        if strat not in strategy_survival:
            strategy_survival[strat] = {"total": 0, "survived": 0}
        strategy_survival[strat]["total"] += 1
        if r.get("survived"):
            strategy_survival[strat]["survived"] += 1
    
    # Time distribution (if timestamps available)
    durations = []
    for r in runs:
        try:
            start = datetime.fromisoformat(r["start_time"])
            end = datetime.fromisoformat(r["end_time"])
            durations.append((end - start).total_seconds())
        except (KeyError, ValueError):
            pass
    
    def percentile(data: list[float], p: float) -> float:
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        idx = min(idx, len(sorted_data) - 1)
        return sorted_data[idx]
    
    def stats(data: list[float]) -> dict:
        if not data:
            return {"count": 0, "mean": 0, "min": 0, "max": 0, "p25": 0, "p50": 0, "p75": 0, "p90": 0, "p99": 0}
        return {
            "count": len(data),
            "mean": sum(data) / len(data),
            "min": min(data),
            "max": max(data),
            "p25": percentile(data, 25),
            "p50": percentile(data, 50),
            "p75": percentile(data, 75),
            "p90": percentile(data, 90),
            "p99": percentile(data, 99),
        }
    
    return {
        "overview": {
            "total_runs": total,
            "survived": len(survived),
            "died": len(died),
            "survival_rate": len(survived) / total * 100 if total > 0 else 0,
        },
        "turns": {
            "all": stats(all_turns),
            "survived": stats(survival_turns),
            "died": stats(death_turns),
        },
        "dungeon_level": {
            "all": stats(depths),
            "survived": stats(survived_depths),
            "died": stats(died_depths),
            "distribution": dict(Counter(depths)),
        },
        "final_level": {
            "all": stats(levels),
            "survived": stats(survived_levels),
            "died": stats(died_levels),
            "distribution": dict(Counter(levels)),
        },
        "strategy": strategy_survival,
        "real_time_seconds": stats(durations) if durations else {},
    }


def print_distribution_table(title: str, data: dict, unit: str = "") -> None:
    """Print a formatted distribution table."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    if not data or data.get("count", 0) == 0:
        print("  No data")
        return
    
    print(f"  Count:     {data['count']:>8}")
    print(f"  Mean:      {data['mean']:>8.1f} {unit}")
    print(f"  Min:       {data['min']:>8.1f} {unit}")
    print(f"  Max:       {data['max']:>8.1f} {unit}")
    print(f"  25th %ile: {data['p25']:>8.1f} {unit}")
    print(f"  50th %ile: {data['p50']:>8.1f} {unit}")
    print(f"  75th %ile: {data['p75']:>8.1f} {unit}")
    print(f"  90th %ile: {data['p90']:>8.1f} {unit}")
    print(f"  99th %ile: {data['p99']:>8.1f} {unit}")


def print_histogram(data: list[int], bins: int = 10, label: str = "") -> None:
    """Print a simple ASCII histogram."""
    if not data:
        return
    
    min_val = min(data)
    max_val = max(data)
    if min_val == max_val:
        print(f"  {label}: All values = {min_val}")
        return
    
    bin_width = max(1, (max_val - min_val + 1) // bins)
    hist = Counter()
    for v in data:
        bin_start = (v // bin_width) * bin_width
        hist[bin_start] += 1
    
    max_count = max(hist.values()) if hist else 1
    print(f"\n  {label} Histogram:")
    for bin_start in sorted(hist.keys()):
        count = hist[bin_start]
        bar_len = int(count / max_count * 30)
        bar = "#" * bar_len
        print(f"    {bin_start:>4}-{bin_start+bin_width-1:<4} | {bar} ({count})")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze playtest logs and generate distribution tables")
    parser.add_argument("--log-dir", default="playtest_logs", help="Log directory")
    parser.add_argument("--all", action="store_true", help="Analyze all log files combined")
    parser.add_argument("--export-csv", help="Export combined data to CSV")
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    
    if args.all:
        # Combine all playtest logs
        all_runs = []
        for f in sorted(log_dir.glob("playtest_*.json")):
            with open(f, encoding="utf-8") as fp:
                all_runs.extend(json.load(fp))
        runs = all_runs
        print(f"Combined {len(runs)} runs from {len(list(log_dir.glob('playtest_*.json')))} files")
    else:
        runs, summary = load_latest_logs(args.log_dir)
        if not runs:
            return
        print(f"Analyzing latest run: {len(runs)} playthroughs")
    
    if not runs:
        print("No data to analyze.")
        return
    
    results = analyze_distributions(runs)
    
    # Overview
    ov = results["overview"]
    print(f"\n{'#'*60}")
    print(f"# PLAYTEST DISTRIBUTION ANALYSIS")
    print(f"#{'#'*58}")
    print(f"# Total Runs:     {ov['total_runs']}")
    print(f"# Survived:       {ov['survived']} ({ov['survival_rate']:.1f}%)")
    print(f"# Died:           {ov['died']}")
    
    # Turns distribution
    print_distribution_table("TURNS DISTRIBUTION", results["turns"]["all"], "turns")
    print_distribution_table("  - Survived Runs", results["turns"]["survived"], "turns")
    print_distribution_table("  - Death Runs", results["turns"]["died"], "turns")
    print_histogram([r["total_turns"] for r in runs], label="Turns")
    
    # Dungeon level distribution
    print_distribution_table("DUNGEON LEVEL DISTRIBUTION", results["dungeon_level"]["all"], "floors")
    print_distribution_table("  - Survived", results["dungeon_level"]["survived"], "floors")
    print_distribution_table("  - Died", results["dungeon_level"]["died"], "floors")
    print_histogram([r["max_dungeon_level"] for r in runs], label="Dungeon Level")
    
    print(f"\n  Dungeon Level Frequency:")
    for level, count in sorted(results["dungeon_level"]["distribution"].items()):
        pct = count / ov['total_runs'] * 100
        bar = "#" * int(pct / 5)
        print(f"    Level {level}: {count:>3} ({pct:>5.1f}%) {bar}")
    
    # Final level distribution
    print_distribution_table("FINAL CHARACTER LEVEL", results["final_level"]["all"], "level")
    print_histogram([r["final_level"] for r in runs], label="Final Level")
    
    # Strategy comparison
    print(f"\n{'='*60}")
    print(f" STRATEGY COMPARISON")
    print(f"{'='*60}")
    print(f"  {'Strategy':<12} {'Runs':>6} {'Survived':>10} {'Rate':>8}")
    print(f"  {'-'*12} {'-'*6} {'-'*10} {'-'*8}")
    for strat, data in results["strategy"].items():
        rate = data["survived"] / data["total"] * 100 if data["total"] > 0 else 0
        print(f"  {strat:<12} {data['total']:>6} {data['survived']:>10} {rate:>7.1f}%")
    
    # Real time
    if results["real_time_seconds"].get("count", 0) > 0:
        print_distribution_table("REAL TIME DURATION", results["real_time_seconds"], "seconds")
    
    # Export CSV if requested
    if args.export_csv:
        import csv
        with open(args.export_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["seed", "strategy", "survived", "turns", "max_depth", "final_level", "final_exp", "final_gold", "duration_sec"])
            for r in runs:
                try:
                    start = datetime.fromisoformat(r["start_time"])
                    end = datetime.fromisoformat(r["end_time"])
                    duration = (end - start).total_seconds()
                except (KeyError, ValueError):
                    duration = 0
                writer.writerow([
                    r.get("seed", ""),
                    r.get("strategy", ""),
                    r.get("survived", False),
                    r.get("total_turns", 0),
                    r.get("max_dungeon_level", 0),
                    r.get("final_level", 0),
                    r.get("final_exp", 0),
                    r.get("final_gold", 0),
                    duration,
                ])
        print(f"\nExported to {args.export_csv}")


if __name__ == "__main__":
    main()
