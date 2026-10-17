"""
Balance Tool Module
Provides tools for balancing world events based on collected data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from community_goal_manager import COMMUNITY_GOAL_MANAGER
from feedback_system import FEEDBACK_SYSTEM
from world_event_system import RANKING_MANAGER, REGISTRY


class BalanceTool:
    def __init__(self):
        pass

    def get_event_statistics(self, event_id: str) -> dict[str, Any]:
        """
        イベントの統計情報を取得する。
        :param event_id: イベントID
        :return: 統計情報の辞書
        """
        event_data = REGISTRY.get(event_id)
        if not event_data:
            return {}

        stats = {
            "event_id": event_id,
            "event_name": event_data.name,
            "participant_count": 0,  # プレイヤー参加数 (ランキングにエントリーがあるプレイヤー数)
            "average_score": 0.0,
            "total_points_awarded": 0,
            "feedback_count": 0,
            "average_rating": None,
            "goal_achieved": False,
            "goal_progress": 0,
            "goal_target": 0,
        }

        # ランキングから参加数と平均スコアを計算
        ranking = RANKING_MANAGER.get_ranking(event_id)
        if ranking:
            stats["participant_count"] = len(ranking)
            total_score = sum(score for _, score in ranking)
            stats["average_score"] = total_score / len(ranking) if ranking else 0
            stats["total_points_awarded"] = total_score

        # フィードバック情報
        stats["feedback_count"] = len(FEEDBACK_SYSTEM.get_feedback_for_event(event_id))
        stats["average_rating"] = FEEDBACK_SYSTEM.get_average_rating(event_id)

        # コミュニティゴール情報
        if hasattr(event_data, "community_goal") and event_data.community_goal:
            goal_type = event_data.community_goal.get("type")
            if goal_type == "total_points":
                stats["goal_progress"] = COMMUNITY_GOAL_MANAGER.get_progress(event_id, goal_type)
                stats["goal_target"] = event_data.community_goal.get("target", 0)
                stats["goal_achieved"] = COMMUNITY_GOAL_MANAGER.is_goal_achieved(event_id)

        return stats

    def suggest_adjustments(self, event_id: str) -> dict[str, Any]:
        """
        イベントのバランス調整を提案する。
        :param event_id: イベントID
        :return: 調整提案の辞書
        """
        stats = self.get_event_statistics(event_id)
        suggestions = {}

        # 参加率に基づく調整
        if stats["participant_count"] < 5:
            suggestions["trigger_chance"] = "increase"  # 参加者が少なければ発生確率を上げる
        elif stats["participant_count"] > 50:
            suggestions["trigger_chance"] = "decrease"

        # 評価に基づく調整
        avg_rating = stats["average_rating"]
        if avg_rating is not None:
            if avg_rating < 3.0:
                suggestions["rewards"] = "increase"  # 評価が低ければ報酬を増やす
                suggestions["difficulty"] = "decrease"
            elif avg_rating > 4.0:
                suggestions["rewards"] = "decrease"  # 評価が高ければ報酬を減らしてもよい
                suggestions["difficulty"] = "increase"

        # ゴール達成率に基づく調整
        if stats.get("goal_achieved") is False and stats.get("goal_target", 0) > 0:
            progress = stats.get("goal_progress", 0)
            target = stats.get("goal_target", 0)
            if target > 0:
                ratio = progress / target
                if ratio < 0.5:
                    suggestions["goal_target"] = (
                        "decrease"  # ゴールが達成されにくければ目標を下げる
                    )
                elif ratio > 1.5:
                    suggestions["goal_target"] = "increase"

        return suggestions

    def apply_adjustments(self, event_id: str, adjustments: dict[str, Any]) -> bool:
        """
        提案された調整をイベントデータに適用する（実際にはYAMLファイルを更新する必要がある）。
        :param event_id: イベントID
        :param adjustments: 調整の辞書
        :return: 成功したかどうか
        """
        # ここではプレースホルダー：実際にはworld_events.yamlを読み書きする必要がある
        print(f"Adjustments for {event_id}: {adjustments}")
        # 実際の実装では、YAMLファイルをパースし、該当イベントのパラメータを更新し、ファイルに書き戻す
        return True


BALANCE_TOOL = BalanceTool()


# ============================================================
# 難易度カーブ・スナップショット (T33 R3案C)
#
# 「現行バランスの数値」を baseline.json の balance_snapshot セクションに
# 記録し、tests/test_balance_snapshot.py が再計算値と比較する。
# バランス変更を意図したときだけ `python3 balance_tool.py --update-baseline`
# でベースラインを更新する (差分はコミットで意図を説明する)。
# ============================================================

_REPO_ROOT = Path(__file__).resolve().parent
BASELINE_PATH = _REPO_ROOT / "baseline.json"
BALANCE_STANDARDS_PATH = _REPO_ROOT / "data" / "balance_standards.yaml"
MONSTERS_PATH = _REPO_ROOT / "data" / "monsters.yaml"
CONFIG_PATH = _REPO_ROOT / "config.yaml"

# スナップショットの対象範囲 (data/balance_standards.yaml difficulty_curve と同期)
SNAPSHOT_LEVELS = range(1, 21)  # プレイヤーレベル 1-20
SNAPSHOT_FLOORS = range(1, 11)  # ダンジョン 1-10F

# 撃破 EXP は managers/combat_manager.py:40 の固定式 (モンスター種に依存しない)
ENEMY_EXP_PER_FLOOR = 35

# data_manager.create_monster の階層スケーリング (data_manager.py:571)
#   scale_mult = 1.0 + (level_scale - 1) * 0.15
ENEMY_SCALE_STEP = 0.15


def _floor_monster_pool(monsters: dict[str, Any], floor: int) -> list[dict[str, Any]]:
    """``get_random_monster_for_floor`` (data_manager.py:640-643) と同一の抽出条件。"""
    return [
        body
        for body in monsters.values()
        if (body.get("min_floor") or 1) <= floor <= (body.get("max_floor") or 999) + 3
    ]


def _expected_player_stats(config: dict[str, Any], level: int) -> dict[str, float]:
    """期待プレイヤーレベルの maxHP / 攻撃を解析モデルで求める。

    成長は gain_exp (ecs/entity.py:1358-1377) の「1 レベルにつき 8 能力値から
    ランダム 2 個を +1」の期待値 (能力値あたり +0.25/レベル) を使う決定論モデル。
    maxHP は calculate_max_hp (ecs/entity.py:1283-1288) + 祭神jure の +10
    (packages/character/package.py で既定信仰) を再現する。
    攻撃は balance_simulator._collect_observations と同じ strength を代理指標にする。
    """
    attrs = config["player"]["attributes"]
    growth = (level - 1) * 2 / 8
    strength = attrs["strength"] + growth
    endurance = attrs["endurance"] + growth
    max_hp = endurance * 2 + strength + level * 5 + 10
    return {"max_hp": max_hp, "attack": strength}


def compute_balance_snapshot() -> dict[str, Any]:
    """現行データ・現行式から難易度カーブのスナップショットを再計算する。

    ランダム性を含まないので、同じリポジトリ状態なら常に同じ辞書を返す。
    数値は小数第 2 位に丸めて JSON との往復でビット一致するようにする。
    """
    import yaml

    standards = yaml.safe_load(BALANCE_STANDARDS_PATH.read_text(encoding="utf-8")) or {}
    monsters = yaml.safe_load(MONSTERS_PATH.read_text(encoding="utf-8")) or {}
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    curve = standards.get("exp_curve") or {}
    base = float(curve.get("base", 120))
    growth = float(curve.get("growth", 1.35))

    exp_levels: dict[str, dict[str, int]] = {}
    cumulative = 0
    kills_per_level: dict[str, float] = {}
    for level in SNAPSHOT_LEVELS:
        exp_next = int(base * (growth ** (level - 1)))  # ecs/entity.py:437 と同一式
        cumulative += exp_next
        exp_levels[str(level)] = {"exp_next": exp_next, "cumulative": cumulative}
        # 「階層 = プレイヤーレベル」の想定でレベル 1 上に必要な撃破数
        kills_per_level[str(level)] = round(exp_next / (ENEMY_EXP_PER_FLOOR * level), 2)

    enemy_floors: dict[str, dict[str, Any]] = {}
    ratio_floors: dict[str, dict[str, float]] = {}
    curve_levels = (standards.get("difficulty_curve") or {}).get("dungeon_levels") or {}
    for floor in SNAPSHOT_FLOORS:
        scale = 1.0 + (floor - 1) * ENEMY_SCALE_STEP
        pool = _floor_monster_pool(monsters, floor)
        hps = [int(body.get("max_hp", 0) * scale) for body in pool]
        attacks = [int((body.get("attributes") or {}).get("strength", 0) * scale) for body in pool]
        mean_hp = sum(hps) / len(hps) if hps else 0.0
        mean_attack = sum(attacks) / len(attacks) if attacks else 0.0
        enemy_floors[str(floor)] = {
            "enemy_hp_mean": round(mean_hp, 2),
            "enemy_hp_min": min(hps) if hps else 0,
            "enemy_hp_max": max(hps) if hps else 0,
            "enemy_attack_mean": round(mean_attack, 2),
            "enemy_exp": ENEMY_EXP_PER_FLOOR * floor,
        }
        # 比率は data/balance_standards.yaml の expected_player_level 基準
        expected_level = int(curve_levels.get(floor, {}).get("expected_player_level", floor))
        player = _expected_player_stats(config, expected_level)
        ratio_floors[str(floor)] = {
            "hp": round(mean_hp / player["max_hp"], 2) if player["max_hp"] else 0.0,
            "attack": round(mean_attack / player["attack"], 2) if player["attack"] else 0.0,
        }

    return {
        "schema": 1,
        "exp_curve": exp_levels,
        "kills_per_level": kills_per_level,
        "enemy_curve": enemy_floors,
        "player_enemy_ratio": ratio_floors,
    }


def load_balance_baseline() -> dict[str, Any]:
    """baseline.json を読み、balance_snapshot セクション (無ければ空) を返す。"""
    if not BASELINE_PATH.exists():
        return {}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    snapshot = data.get("balance_snapshot")
    return snapshot if isinstance(snapshot, dict) else {}


def update_balance_baseline() -> dict[str, Any]:
    """スナップショットを再計算して baseline.json へ書き込む (他キーは保持)。"""
    snapshot = compute_balance_snapshot()
    if BASELINE_PATH.exists():
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    else:
        data = {}
    data["balance_snapshot"] = snapshot
    BASELINE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return snapshot


def diff_balance_snapshot(
    current: dict[str, Any], baseline: dict[str, Any]
) -> list[str]:
    """スナップショット差分を人間可読な行リストで返す (空なら一致)。"""
    lines: list[str] = []

    def walk(node: Any, base: Any, path: str) -> None:
        if isinstance(node, dict) and isinstance(base, dict):
            for key in sorted(set(node) | set(base)):
                if key not in base:
                    lines.append(f"{path}.{key}: ベースラインに無い (追加)")
                elif key not in node:
                    lines.append(f"{path}.{key}: 現行から消えた")
                else:
                    walk(node[key], base[key], f"{path}.{key}")
        elif node != base:
            lines.append(f"{path}: {base} -> {node}")

    walk(current, baseline, "balance_snapshot")
    return lines


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="難易度カーブ・バランススナップショット操作")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="現行値を baseline.json の balance_snapshot へ書き込む (バランス変更を意図したときだけ実行)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="現行値と baseline.json の差分を表示 (差分があれば終了コード 1)",
    )
    args = parser.parse_args(argv)

    if args.update_baseline:
        snapshot = update_balance_baseline()
        print(f"baseline.json の balance_snapshot を更新しました ({len(snapshot)} セクション)")
        return 0
    if args.check:
        lines = diff_balance_snapshot(compute_balance_snapshot(), load_balance_baseline())
        if lines:
            print("ベースラインと現行値が乖離しています (意図した変更なら --update-baseline で更新):")
            for line in lines:
                print(f"  {line}")
            return 1
        print("ベースラインと一致しています")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
