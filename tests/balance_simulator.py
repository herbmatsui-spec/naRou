"""バランス計測器。

実ゲームと同じ戦闘ループ (``player_act`` / ``advance_world``) を回して測る。
判定基準は ``data/balance_standards.yaml`` に置き、コードには閾値を埋めない。
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecs.entity import Attributes

# 実ゲームのレベルアップ規則 (ecs/entity.py gain_exp) が触る能力値。
ATTRIBUTE_KEYS = (
    "strength",
    "endurance",
    "dexterity",
    "perception",
    "learning",
    "will",
    "magic",
    "charisma",
)

# 生成済みエンジンと計測用の戦闘タイル。Engine() の生成は 2 秒程度かかり、
# 試行ごとに生成すると計測時間が桁で増えるためプロセス内で 1 つだけ共有する。
_WORLD: dict[str, Any] = {}

# 計測用の世界 (ダンジョン生成) を固定するシード。レポートの再生成が同じ数値になるようにする。
WORLD_SEED = 20261004


def acquire_world() -> tuple[Any, tuple[int, int]]:
    """実エンジンと計測用の戦闘タイルを返す (初回の呼び出しで生成)。"""
    if "engine" not in _WORLD:
        from game import Engine

        # ダンジョンは乱数生成なので、生成時の乱数を固定してレポートを再現可能にする。
        # 呼び出し元の乱数状態は復元するので、戦闘ロールは呼び出し側の seed のまま。
        caller_state = random.getstate()
        random.seed(WORLD_SEED)
        try:
            engine = Engine()
        finally:
            random.setstate(caller_state)

        altar = getattr(engine, "altar_pos", None)
        altar = tuple(altar) if altar else None
        # 祭壇タイルは player_act が ``GodInfo`` を import できず例外を投げる
        # (packages/gameplay/package.py) ため、計測は祭壇から離れたタイルで行う。
        arena, best_distance = None, -1
        for x in range(engine.game_map.width):
            for y in range(engine.game_map.height):
                if not engine.game_map.is_walkable(x, y):
                    continue
                distance = 10**6 if altar is None else max(abs(x - altar[0]), abs(y - altar[1]))
                if distance > best_distance:
                    arena, best_distance = (x, y), distance
        _WORLD["engine"] = engine
        _WORLD["arena"] = arena
        _WORLD["altar"] = altar
        _WORLD["base_attributes"] = {
            name: getattr(engine.player.attributes, name) for name in ATTRIBUTE_KEYS
        }
    return _WORLD["engine"], _WORLD["arena"]


class BattleScenario:
    """自動戦闘シナリオ定義クラス (Step 36, 37)"""

    def __init__(
        self,
        name: str,
        player_level: int,
        monster_type: str,
        trials: int = 100,
        expected_win_rate: float = 0.5,
    ):
        self.name = name
        self.player_level = player_level
        self.monster_type = monster_type
        self.trials = trials
        self.expected_win_rate = expected_win_rate

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BattleScenario:
        return cls(
            name=data.get("name", "Scenario"),
            player_level=data.get("player_level", 1),
            monster_type=data.get("monster_type", "slime"),
            trials=data.get("trials", 100),
            expected_win_rate=data.get("expected_win_rate", 0.5),
        )


class BalanceChecker:
    """YAML基準値に基づくバランス整合性検証クラス (Step 44-47)"""

    def __init__(self, standards_path: str = "data/balance_standards.yaml"):
        import yaml

        self.standards_path = standards_path
        self.standards = {}
        if os.path.exists(standards_path):
            with open(standards_path, encoding="utf-8") as f:
                self.standards = yaml.safe_load(f) or {}

    @property
    def judgement(self) -> dict[str, Any]:
        """判定基準 (勝率の許容範囲・ダメージ比下限など)。"""
        return self.standards.get("judgement") or {}

    @property
    def max_turns(self) -> int:
        """膠着とみなすターン上限。"""
        return int((self.standards.get("simulation") or {}).get("max_turns", 100))

    def check_standards(self, observations: dict[str, Any] | None = None) -> dict[str, Any]:
        """実測値を ``data/balance_standards.yaml`` の基準値と照合する。

        ``observations`` は ``{"levels": {レベル: {"hp": ..., "attack": ...}},"economy": {"gold_per_dungeon_floor": ...}}``
        の形。実測値が無い項目は「確認できていない」ので PASS にはしない。
        """
        issues: list[dict[str, Any]] = []
        standards = self.standards.get("standards") or {}
        observed_levels = self._normalize_levels(observations)
        for level, limits in sorted((standards.get("levels") or {}).items()):
            measured = observed_levels.get(int(level))
            if not measured:
                issues.append(
                    {
                        "standard": f"standards.levels.{level}",
                        "level": int(level),
                        "message": f"Lv{level} の実測値が計測されていない (基準は確認できない)",
                    }
                )
                continue
            for field, lower, upper in (
                ("hp", "min_hp", "max_hp"),
                ("attack", "min_attack", "max_attack"),
            ):
                value = measured.get(field)
                if value is None:
                    continue
                for key in (lower, upper):
                    limit = limits.get(key)
                    if limit is None:
                        continue
                    violated = value < limit if key == lower else value > limit
                    if violated:
                        issues.append(
                            {
                                "standard": f"standards.levels.{level}.{key}",
                                "level": int(level),
                                "field": field,
                                "value": value,
                                "limit": limit,
                                "message": (
                                    f"Lv{level} の {field} が実測 {value} で、"
                                    f"基準 {key}={limit} を外れている"
                                ),
                            }
                        )

        economy = self.standards.get("economy") or {}
        max_gold = economy.get("max_gold_per_dungeon_floor")
        gold = ((observations or {}).get("economy") or {}).get("gold_per_dungeon_floor")
        if max_gold is not None and gold is not None and gold > max_gold:
            issues.append(
                {
                    "standard": "economy.max_gold_per_dungeon_floor",
                    "field": "gold_per_dungeon_floor",
                    "value": gold,
                    "limit": max_gold,
                    "message": (
                        f"1 ダンジョンフロアあたりの획取ゴールドが実測 {gold} で、"
                        f"基準 {max_gold} を超えている"
                    ),
                }
            )

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "standards_loaded": bool(self.standards),
        }

    @staticmethod
    def _normalize_levels(observations: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
        """``{"levels": {...}}`` と ``{レベル: {...}}`` の両方を受け取る。"""
        if not isinstance(observations, dict):
            return {}
        raw = observations.get("levels", observations)
        if not isinstance(raw, dict):
            return {}
        return {int(level): stats for level, stats in raw.items() if isinstance(stats, dict)}


class BalanceSimulator:
    """実ゲームの戦闘ループをそのまま回して測るバランス計測器。"""

    # 実攻撃のたびに config.yaml を読み直すため 1 試行は実測 0.1〜0.5 秒かかる。
    # レポート既定の試行回数はこの実測時間に合わせて抑える (判定基準は YAML 側)。
    SCENARIO_TRIALS = 30

    def __init__(self):
        self.report = {}
        self.checker = BalanceChecker()

    # --- 実戦ループ -----------------------------------------------------

    def _prepare_trial(self, player_level: int) -> tuple[Any, Any]:
        """1 試行の開始時に世界を初期状態へ戻し、指定レベルのプレイヤーを用意する。"""
        engine, arena = acquire_world()
        player = engine.player

        # 実ゲームと同じレベルアップ規則 (1レベルにつき 8 能力値からランダムに 2 つを +1)。
        attributes = dict(_WORLD["base_attributes"])
        for _ in range(max(0, player_level - 1)):
            for name in random.sample(ATTRIBUTE_KEYS, 2):
                attributes[name] += 1
        if getattr(player, "_base_attributes", None) is not None:
            player._base_attributes = Attributes(**attributes)
        for name, value in attributes.items():
            setattr(player.attributes, name, value)
        player.level = player_level
        player.recalculate_stats()

        player.x, player.y = arena
        player.hp = player.max_hp
        player.mp = player.max_mp
        player.energy = 0
        # 計測対象の戦闘 1 体を置く。マップ・AI・進行系は実物のまま使う。
        engine.entity_manager.entities = [player]
        engine.entity_manager.items_on_ground.clear()
        engine.turns = 0
        return engine, player

    def _spawn_monster(self, engine: Any, monster_type: str) -> Any | None:
        """データ定義からモンスターを生成する (階層補正はプレイヤーLvに合わせる)。"""
        player = engine.player
        altar = _WORLD.get("altar")
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            x, y = player.x + dx, player.y + dy
            if altar is not None and (x, y) == altar:
                continue
            if engine.game_map.is_walkable(x, y):
                return engine.data_manager.create_monster(
                    monster_type, x, y, level_scale=player.level
                )
        return None

    def _step_toward(self, engine: Any, monster: Any) -> tuple[int, int]:
        """モンスターへ向かう 1 手。隣接していれば攻撃、それ以外は歩けるタイルを選ぶ。"""
        player = engine.player
        dx = (monster.x > player.x) - (monster.x < player.x)
        dy = (monster.y > player.y) - (monster.y < player.y)
        altar = _WORLD.get("altar")
        for step in ((dx, dy), (dx, 0), (0, dy), (dy, dx), (0, dx), (dy, 0)):
            if step == (0, 0):
                continue
            x, y = player.x + step[0], player.y + step[1]
            if altar is not None and (x, y) == altar:
                continue
            occupant = engine.get_entity_at(x, y)
            if occupant is monster:
                return step
            if occupant is None and engine.game_map.is_walkable(x, y):
                return step
        return (0, 0)

    def _run_trial(self, scenario: BattleScenario) -> dict[str, Any] | None:
        """1 回の遭遇を実エンジンで最後まで回す。"""
        engine, player = self._prepare_trial(scenario.player_level)
        monster = self._spawn_monster(engine, scenario.monster_type)
        if monster is None:
            return None
        engine.entity_manager.add_entity(monster)

        player_hp_start = player.hp
        monster_hp_start = monster.hp
        dealt = taken = regen = 0
        turns = 0
        one_shot = False
        outcome = "timeout"

        while turns < self.checker.max_turns:
            turns += 1

            monster_hp_before = monster.hp
            engine.player_act(*self._step_toward(engine, monster))
            dealt_this_action = max(0, monster_hp_before - monster.hp)
            dealt += dealt_this_action
            if dealt_this_action >= monster_hp_start:
                one_shot = True
            if monster.hp <= 0:
                outcome = "win" if player.hp > 0 else "draw"
                break

            hp_before = player.hp
            # 敵 AI の行動選択と turn ベースの自然回復はここ ([[engine.py:advance_world]]) で起きる。
            engine.advance_world()
            damage = hp_before - player.hp
            if damage > 0:
                taken += damage
                if damage >= player_hp_start:
                    one_shot = True
            else:
                regen += -damage
            if player.hp <= 0:
                outcome = "loss"
                break

        engine.entity_manager.remove_entity(monster)
        return {
            "outcome": outcome,
            "turns": turns,
            "dmg_dealt": dealt,
            "dmg_taken": taken,
            "hp_regen": regen,
            "one_shot": one_shot,
        }

    # --- 判定 -----------------------------------------------------------

    def _judge(self, scenario: BattleScenario, stats: dict[str, Any]) -> tuple[bool, list[str]]:
        """YAML の判定基準で「バランス良好」かを決める。"""
        criteria = self.checker.judgement
        reasons: list[str] = []

        if stats["stalled_rate"] > 0:
            reasons.append(
                f"{stats['stalled_count']} 回の戦闘が {self.checker.max_turns} ターンで終わらなかった"
            )
        if stats["one_shot_rate"] > criteria.get("max_one_shot_rate", 0.1):
            reasons.append(
                f"一撃決着の割合 {stats['one_shot_rate']:.2f} が上限 "
                f"{criteria.get('max_one_shot_rate')} を超えた"
            )
        if stats["damage_taken_ratio"] < criteria.get("min_damage_taken_ratio", 0.1):
            reasons.append(
                f"被与ダメージ比 {stats['damage_taken_ratio']:.2f} が下限 "
                f"{criteria.get('min_damage_taken_ratio')} を下回った"
            )

        expected = scenario.expected_win_rate
        absolute = criteria.get("absolute_victory_win_rate", 1.0)
        if expected is not None:
            if expected < absolute and stats["win_rate"] >= absolute:
                reasons.append(
                    f"期待勝率 {expected} に対し勝率 {stats['win_rate']} (絶対勝利) となった"
                )
            elif abs(stats["win_rate"] - expected) > criteria.get("win_rate_tolerance", 0.3):
                reasons.append(
                    f"勝率 {stats['win_rate']} が期待値 {expected} から許容範囲 "
                    f"{criteria.get('win_rate_tolerance')} を超えた"
                )
        return not reasons, reasons

    def simulate_battle(
        self,
        player_level: int = 1,
        monster_type: str = "slime",
        trials: int = 100,
        expected_win_rate: float | None = None,
    ) -> dict[str, Any]:
        scenario = BattleScenario(
            name=f"lvl{player_level}_vs_{monster_type}",
            player_level=player_level,
            monster_type=monster_type,
            trials=trials,
            expected_win_rate=expected_win_rate,
        )

        results = [self._run_trial(scenario) for _ in range(trials)]
        completed = [r for r in results if r is not None]
        if not completed:
            return {
                "player_level": player_level,
                "monster_type": monster_type,
                "trials": trials,
                "completed_trials": 0,
                "win_rate": 0.0,
                "expected_win_rate": expected_win_rate,
                "win_rate_alert": True,
                "avg_turns": 0.0,
                "std_dev_turns": 0.0,
                "avg_dmg_dealt": 0.0,
                "avg_dmg_taken": 0.0,
                "avg_hp_regen": 0.0,
                "damage_taken_ratio": 0.0,
                "one_shot_count": 0,
                "one_shot_rate": 1.0,
                "stalled_count": 0,
                "stalled_rate": 1.0,
                "is_balanced": False,
                "unbalanced_reasons": ["戦闘を開始できなかった"],
            }

        count = len(completed)
        turns_list = [r["turns"] for r in completed]
        avg_turns = sum(turns_list) / count
        variance = sum((x - avg_turns) ** 2 for x in turns_list) / count
        avg_dealt = sum(r["dmg_dealt"] for r in completed) / count
        avg_taken = sum(r["dmg_taken"] for r in completed) / count
        one_shot_count = sum(1 for r in completed if r["one_shot"])
        stalled_count = sum(1 for r in completed if r["outcome"] == "timeout")
        win_rate = round(sum(1 for r in completed if r["outcome"] == "win") / count, 3)

        stats = {
            "win_rate": win_rate,
            "avg_turns": avg_turns,
            "one_shot_rate": one_shot_count / count,
            "stalled_count": stalled_count,
            "stalled_rate": stalled_count / count,
            # 被与ダメージ比。0 に近いほど相手が何もできない一方的な戦闘。
            "damage_taken_ratio": (avg_taken / avg_dealt) if avg_dealt else float("inf"),
        }
        is_balanced, reasons = self._judge(scenario, stats)

        return {
            "player_level": player_level,
            "monster_type": monster_type,
            "trials": trials,
            "completed_trials": count,
            "win_rate": win_rate,
            "expected_win_rate": expected_win_rate,
            "win_rate_alert": bool(reasons),
            "avg_turns": round(avg_turns, 2),
            "std_dev_turns": round(math.sqrt(variance), 2),
            "avg_dmg_dealt": round(avg_dealt, 2),
            "avg_dmg_taken": round(avg_taken, 2),
            "avg_hp_regen": round(sum(r["hp_regen"] for r in completed) / count, 2),
            "damage_taken_ratio": round(
                stats["damage_taken_ratio"]
                if stats["damage_taken_ratio"] != float("inf")
                else 999.0,
                3,
            ),
            "one_shot_count": one_shot_count,
            "one_shot_rate": round(stats["one_shot_rate"], 3),
            "stalled_count": stalled_count,
            "stalled_rate": round(stats["stalled_rate"], 3),
            "is_balanced": is_balanced,
            "unbalanced_reasons": reasons,
        }

    # --- レポート -------------------------------------------------------

    def _floor_gold(self) -> int:
        """現在フロアの獲得ゴールド。"""
        engine, _ = acquire_world()
        return int(engine.survival.gold)

    def _collect_observations(self, gold_per_floor: float) -> dict[str, Any]:
        """YAML の基準に照合するための実測値を集める。"""
        engine, _ = acquire_world()
        levels = sorted(
            int(level)
            for level in ((self.checker.standards.get("standards") or {}).get("levels") or {})
        )
        measured: dict[int, dict[str, Any]] = {}
        for level in levels:
            _, player = self._prepare_trial(level)
            measured[level] = {"hp": player.max_hp, "attack": player.attributes.strength}
        return {
            "levels": measured,
            "economy": {"gold_per_dungeon_floor": gold_per_floor},
        }

    def generate_html_report(
        self, report_data: dict[str, Any], output_html: str = "balance_report.html"
    ) -> str:
        """シミュレーション結果をHTMLレポートとして出力 (Step 42)"""
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='ja'>",
            "<head><meta charset='UTF-8'><title>Elona Battle Balance Report</title>",
            "<style>",
            "body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }",
            "table { width: 100%; border-collapse: collapse; margin-top: 16px; background: #1e293b; border-radius: 8px; overflow: hidden; }",
            "th, td { padding: 12px; border: 1px solid #334155; text-align: left; }",
            "th { background: #3b82f6; color: white; }",
            ".pass { color: #4ade80; font-weight: bold; }",
            ".warn { color: #f87171; font-weight: bold; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>⚔️ Elona Commercial Battle Balance Report: <span class='{'pass' if report_data.get('summary') == 'PASS' else 'warn'}'>{report_data.get('summary')}</span></h1>",
            "<table>",
            "<tr><th>シナリオ</th><th>プレイヤーLv</th><th>対象モンスター</th><th>勝率</th>"
            "<th>期待勝率</th><th>平均ターン</th><th>与/被</th><th>判定理由</th><th>判定</th></tr>",
        ]
        for key, sc in report_data.get("scenarios", {}).items():
            status_cls = "pass" if sc.get("is_balanced") else "warn"
            status_txt = "BALANCED" if sc.get("is_balanced") else "WARNING"
            reasons = " / ".join(sc.get("unbalanced_reasons", []))
            html_lines.append(
                f"<tr><td>{key}</td><td>{sc.get('player_level')}</td><td>{sc.get('monster_type')}</td>"
                f"<td>{sc.get('win_rate')}</td><td>{sc.get('expected_win_rate')}</td>"
                f"<td>{sc.get('avg_turns')}</td><td>{sc.get('damage_taken_ratio')}</td>"
                f"<td>{reasons}</td><td class='{status_cls}'>{status_txt}</td></tr>"
            )

        html_lines.extend(["</table>", "</body>", "</html>"])
        html_str = "\n".join(html_lines)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_str)
        return output_html

    def run_full_validation(self, output_path: str = "balance_report.json") -> dict[str, Any]:
        scenarios = [(1, "slime", 0.95), (3, "goblin", 0.85), (5, "orc", 0.70)]
        gold_before = self._floor_gold()
        results = {}
        all_passed = True
        for lvl, mtype, exp_rate in scenarios:
            key = f"lvl{lvl}_vs_{mtype}"
            res = self.simulate_battle(
                player_level=lvl,
                monster_type=mtype,
                trials=self.SCENARIO_TRIALS,
                expected_win_rate=exp_rate,
            )
            results[key] = res
            if not res["is_balanced"]:
                all_passed = False

        # 経済基準は「1 フロアで獲得できたゴールド」として実測する。
        gold_per_floor = self._floor_gold() - gold_before
        checker_res = self.checker.check_standards(self._collect_observations(gold_per_floor))

        self.report = {
            "summary": (
                "PASS" if all_passed and checker_res["status"] == "PASS" else "WARNINGS_DETECTED"
            ),
            "judgement_criteria": self.checker.judgement,
            "scenarios": results,
            "balance_standards": checker_res,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        # HTML も JSON と同じ出力先に置く (CWD をハードコードしない)。
        self.generate_html_report(self.report, os.path.splitext(output_path)[0] + ".html")
        return self.report


if __name__ == "__main__":
    sim = BalanceSimulator()
    rep = sim.run_full_validation()
    print("Balance validation completed:", rep["summary"])
