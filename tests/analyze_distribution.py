#!/usr/bin/env python3
"""
分布分析スクリプト: auto_playtestの結果からクリア/死亡/クリア時間の分布表・グラフを生成
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import Any
from collections import Counter
import statistics

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import matplotlib
    matplotlib.use('Agg')  # ヘッドレス環境用
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("matplotlib未インストール: グラフ生成をスキップ (pip install matplotlib で有効化)")

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def load_latest_playtest_log() -> list[dict[str, Any]] | None:
    """最新のplaytestログを読み込み"""
    log_dir = Path("playtest_logs")
    if not log_dir.exists():
        return None
    
    playtest_files = sorted(log_dir.glob("playtest_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not playtest_files:
        return None
    
    latest = playtest_files[0]
    print(f"読み込み中: {latest}")
    with open(latest, encoding="utf-8") as f:
        return json.load(f)


def load_latest_summary() -> dict[str, Any] | None:
    """最新のsummaryを読み込み"""
    log_dir = Path("playtest_logs")
    if not log_dir.exists():
        return None
    
    summary_files = sorted(log_dir.glob("summary_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not summary_files:
        return None
    
    latest = summary_files[0]
    with open(latest, encoding="utf-8") as f:
        return json.load(f)


def print_distribution_table(data: list[dict[str, Any]]) -> None:
    """分布表をコンソール出力"""
    if not data:
        print("データがありません")
        return
    
    # 生存/死亡の分布
    survived = [r for r in data if r.get("survived")]
    died = [r for r in data if not r.get("survived")]
    
    print(f"\n{'='*60}")
    print(f"プレイスルー分布分析 (総試行数: {len(data)})")
    print(f"{'='*60}")
    
    # 生存率
    print(f"\n【生存/死亡】")
    print(f"  生存: {len(survived)} 回 ({len(survived)/len(data)*100:.1f}%)")
    print(f"  死亡: {len(died)} 回 ({len(died)/len(data)*100:.1f}%)")
    
    # ターン数分布（生存・死亡別）
    print(f"\n【生存ターン数統計】")
    for label, runs in [("生存者", survived), ("死亡者", died), ("全体", data)]:
        if not runs:
            continue
        turns = [r["total_turns"] for r in runs]
        print(f"  {label}: 平均={statistics.mean(turns):.1f}, 中央値={statistics.median(turns)}, "
              f"最小={min(turns)}, 最大={max(turns)}, 標準偏差={statistics.stdev(turns) if len(turns)>1 else 0:.1f}")
    
    # 到達階層分布
    print(f"\n【到達階層分布】")
    depths = [r["max_dungeon_level"] for r in data]
    depth_dist = Counter(depths)
    for depth in sorted(depth_dist.keys()):
        count = depth_dist[depth]
        bar = "#" * (count * 20 // len(data))
        print(f"  B{depth:2d}F: {count:3d}回 ({count/len(data)*100:5.1f}%) {bar}")
    
    # 最終レベル分布
    print(f"\n【最終レベル分布】")
    levels = [r["final_level"] for r in data]
    level_dist = Counter(levels)
    for level in sorted(level_dist.keys()):
        count = level_dist[level]
        bar = "#" * (count * 20 // len(data))
        print(f"  Lv{level:2d}: {count:3d}回 ({count/len(data)*100:5.1f}%) {bar}")
    
    # 戦略別
    print(f"\n【戦略別結果】")
    strategies = set(r.get("strategy", "unknown") for r in data)
    for strat in sorted(strategies):
        strat_runs = [r for r in data if r.get("strategy") == strat]
        s_survived = sum(1 for r in strat_runs if r.get("survived"))
        avg_turns = statistics.mean([r["total_turns"] for r in strat_runs])
        avg_depth = statistics.mean([r["max_dungeon_level"] for r in strat_runs])
        avg_level = statistics.mean([r["final_level"] for r in strat_runs])
        print(f"  {strat:10s}: {len(strat_runs)}回, 生存{s_survived}/{len(strat_runs)} ({s_survived/len(strat_runs)*100:.0f}%), "
              f"平均ターン{avg_turns:.0f}, 平均深度{avg_depth:.1f}, 平均Lv{avg_level:.1f}")
    
    # 死亡原因（死亡者のみ）
    if died:
        print(f"\n【死亡原因分析】")
        death_causes = Counter(r.get("death_log", {}).get("cause", "不明") for r in died)
        for cause, count in death_causes.most_common():
            print(f"  {cause}: {count}回")
        
        death_turns = [r["death_log"].get("turn", 0) for r in died if r.get("death_log")]
        if death_turns:
            print(f"  平均死亡ターン: {statistics.mean(death_turns):.1f}")
            print(f"  死亡ターン範囲: {min(death_turns)} - {max(death_turns)}")


def generate_histograms(data: list[dict[str, Any]], output_dir: Path) -> None:
    """ヒストグラムグラフを生成 (matplotlibが必要)"""
    if not HAS_MATPLOTLIB:
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    survived = [r for r in data if r.get("survived")]
    died = [r for r in data if not r.get("survived")]
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Playtest Distribution Analysis', fontsize=16)
    
    # 1. 生存ターン数分布
    ax = axes[0, 0]
    all_turns = [r["total_turns"] for r in data]
    surv_turns = [r["total_turns"] for r in survived]
    dead_turns = [r["total_turns"] for r in died]
    bins = np.histogram_bin_edges(all_turns, bins='auto')
    ax.hist(surv_turns, bins=bins, alpha=0.7, label='Survived', color='green', density=True)
    ax.hist(dead_turns, bins=bins, alpha=0.7, label='Died', color='red', density=True)
    ax.set_xlabel('Turns')
    ax.set_ylabel('Density')
    ax.set_title('Survival Turns Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. 到達階層分布
    ax = axes[0, 1]
    depths = [r["max_dungeon_level"] for r in data]
    depth_counts = Counter(depths)
    ax.bar(depth_counts.keys(), depth_counts.values(), color='skyblue', edgecolor='black')
    ax.set_xlabel('Dungeon Level Reached')
    ax.set_ylabel('Count')
    ax.set_title('Dungeon Depth Distribution')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3. 最終レベル分布
    ax = axes[0, 2]
    levels = [r["final_level"] for r in data]
    level_counts = Counter(levels)
    ax.bar(level_counts.keys(), level_counts.values(), color='gold', edgecolor='black')
    ax.set_xlabel('Final Level')
    ax.set_ylabel('Count')
    ax.set_title('Final Level Distribution')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. 戦略別生存率
    ax = axes[1, 0]
    strategies = sorted(set(r.get("strategy", "unknown") for r in data))
    strat_survive = []
    strat_total = []
    for strat in strategies:
        runs = [r for r in data if r.get("strategy") == strat]
        strat_total.append(len(runs))
        strat_survive.append(sum(1 for r in runs if r.get("survived")))
    strat_rate = [s/t*100 for s, t in zip(strat_survive, strat_total)]
    bars = ax.bar(strategies, strat_rate, color=['green' if r>50 else 'orange' if r>25 else 'red' for r in strat_rate])
    ax.set_ylabel('Survival Rate (%)')
    ax.set_title('Survival Rate by Strategy')
    ax.set_ylim(0, 100)
    for bar, rate in zip(bars, strat_rate):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{rate:.0f}%', 
                ha='center', va='bottom')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5. ターン数 vs 到達階層 (散布図)
    ax = axes[1, 1]
    surv_turns = [r["total_turns"] for r in survived]
    surv_depths = [r["max_dungeon_level"] for r in survived]
    dead_turns = [r["total_turns"] for r in died]
    dead_depths = [r["max_dungeon_level"] for r in died]
    ax.scatter(surv_turns, surv_depths, alpha=0.6, label='Survived', color='green', s=30)
    ax.scatter(dead_turns, dead_depths, alpha=0.6, label='Died', color='red', s=30)
    ax.set_xlabel('Total Turns')
    ax.set_ylabel('Max Dungeon Level')
    ax.set_title('Turns vs Depth Reached')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 6. 累積生存曲線
    ax = axes[1, 2]
    all_turns_sorted = sorted(all_turns)
    cum_surv = np.arange(1, len(all_turns_sorted) + 1) / len(all_turns_sorted) * 100
    ax.plot(all_turns_sorted, 100 - cum_surv, 'b-', linewidth=2)
    ax.fill_between(all_turns_sorted, 100 - cum_surv, alpha=0.3)
    ax.set_xlabel('Turns')
    ax.set_ylabel('Survival Rate (%)')
    ax.set_title('Cumulative Survival Curve')
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "distribution_analysis.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\nグラフ保存: {output_path}")


def generate_percentile_table(data: list[dict[str, Any]]) -> None:
    """パーセンタイル表を出力"""
    if not data:
        return
    
    turns = sorted(r["total_turns"] for r in data)
    depths = sorted(r["max_dungeon_level"] for r in data)
    levels = sorted(r["final_level"] for r in data)
    
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    
    print(f"\n{'='*60}")
    print(f"パーセンタイル分析")
    print(f"{'='*60}")
    
    print(f"\n  ターン数:")
    for p in percentiles:
        idx = int(len(turns) * p / 100)
        print(f"    P{p:2d}: {turns[min(idx, len(turns)-1)]:4d} ターン")
    
    print(f"\n  到達階層:")
    for p in percentiles:
        idx = int(len(depths) * p / 100)
        print(f"    P{p:2d}: B{depths[min(idx, len(depths)-1)]}F")
    
    print(f"\n  最終レベル:")
    for p in percentiles:
        idx = int(len(levels) * p / 100)
        print(f"    P{p:2d}: Lv{levels[min(idx, len(levels)-1)]}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Playtest分布分析")
    parser.add_argument("--runs", type=int, help="新規実行する試行数（指定時はauto_playtestを実行）")
    parser.add_argument("--max-turns", type=int, default=5000, help="最大ターン数")
    parser.add_argument("--max-depth", type=int, default=20, help="最大ダンジョン深度")
    parser.add_argument("--strategies", nargs="+", default=["melee", "mage", "hybrid", "tank", "speed"], 
                        help="テストする戦略")
    parser.add_argument("--no-graph", action="store_true", help="グラフ生成をスキップ")
    parser.add_argument("--latest-only", action="store_true", help="最新ログのみ分析（再実行しない）")
    args = parser.parse_args()
    
    # 新規実行モード
    if args.runs and not args.latest_only:
        print(f"=== {args.runs}回の自動プレイテストを実行 ===")
        from auto_playtest import PlayTestRunner
        
        runner = PlayTestRunner(
            max_turns=args.max_turns,
            max_dungeon_level=args.max_depth,
            strategies=args.strategies,
        )
        results = runner.run_multiple(args.runs)
        runner.save_results(results)
        
        # 結果をデータ形式に変換
        data = results
    else:
        # 既存ログ分析モード
        print("=== 既存ログを分析 ===")
        data = load_latest_playtest_log()
        if not data:
            print("ログファイルが見つかりません。先に --runs で実行してください。")
            return
    
    # 分析実行
    print_distribution_table(data)
    generate_percentile_table(data)
    
    # グラフ生成
    if not args.no_graph and HAS_MATPLOTLIB:
        generate_histograms(data, Path("playtest_logs"))
    elif not HAS_MATPLOTLIB and not args.no_graph:
        print("\n[注意] matplotlib未インストールのためグラフ生成をスキップしました")
        print("       pip install matplotlib tabulate でインストール可能です")


if __name__ == "__main__":
    main()