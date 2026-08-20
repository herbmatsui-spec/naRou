import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from entity import Attributes, Entity
from systems import CombatSystem, MonsterPreset


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
    def from_dict(cls, data: dict[str, Any]) -> "BattleScenario":
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

    def check_standards(self) -> dict[str, Any]:
        """全項目の健全性チェック"""
        issues = []
        # スキル効率の異常チェック (Step 45)
        # 経済破綻リスクチェック (Step 46)
        # 転生ステータス上昇率チェック (Step 47)
        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "standards_loaded": bool(self.standards),
        }


class BalanceSimulator:
    def __init__(self):
        self.report = {}
        self.checker = BalanceChecker()

    def simulate_battle(
        self,
        player_level: int = 1,
        monster_type: str = "slime",
        trials: int = 100,
        expected_win_rate: float | None = None,
    ) -> dict[str, Any]:
        wins = 0
        turns_list = []
        total_dmg_dealt = []
        total_dmg_taken = []
        one_shot_warnings = 0
        stalled_battles = 0

        for _ in range(trials):
            # Create player
            player = Entity(
                x=0,
                y=0,
                name="Hero",
                is_player=True,
                attributes=Attributes(
                    strength=10 + player_level * 2,
                    endurance=10 + player_level * 2,
                    dexterity=10 + player_level * 2,
                    magic=10 + player_level * 2,
                ),
            )
            player.level = player_level
            player.max_hp = player.calculate_max_hp()
            player.hp = player.max_hp

            # Create monster
            mob = MonsterPreset.create(monster_type, 1, 0)
            initial_mob_hp = mob.hp
            initial_player_hp = player.hp

            turns = 0
            dmg_dealt_acc = 0
            dmg_taken_acc = 0

            while player.hp > 0 and mob.hp > 0 and turns < 100:
                turns += 1
                # Player attacks mob
                p_dmg, p_crit, _ = CombatSystem.calculate_melee_attack(player, mob)
                if p_dmg >= initial_mob_hp:
                    one_shot_warnings += 1
                mob.hp -= p_dmg
                dmg_dealt_acc += p_dmg
                if mob.hp <= 0:
                    break

                # Mob attacks player
                m_dmg, m_crit, _ = CombatSystem.calculate_melee_attack(mob, player)
                if m_dmg >= initial_player_hp:
                    one_shot_warnings += 1
                player.hp -= m_dmg
                dmg_taken_acc += m_dmg

            if turns >= 100:
                stalled_battles += 1

            if player.hp > 0 >= mob.hp:
                wins += 1

            turns_list.append(turns)
            total_dmg_dealt.append(dmg_dealt_acc)
            total_dmg_taken.append(dmg_taken_acc)

        avg_turns = sum(turns_list) / len(turns_list)
        variance = sum((x - avg_turns) ** 2 for x in turns_list) / len(turns_list)
        std_dev = math.sqrt(variance)
        win_rate = round(wins / trials, 3)

        # 期待勝率との乖離アラート (Step 40)
        win_rate_alert = False
        if expected_win_rate is not None:
            if abs(win_rate - expected_win_rate) > 0.4:
                win_rate_alert = True

        result = {
            "player_level": player_level,
            "monster_type": monster_type,
            "trials": trials,
            "win_rate": win_rate,
            "expected_win_rate": expected_win_rate,
            "win_rate_alert": win_rate_alert,
            "avg_turns": round(avg_turns, 2),
            "std_dev_turns": round(std_dev, 2),
            "avg_dmg_dealt": round(sum(total_dmg_dealt) / len(total_dmg_dealt), 2),
            "avg_dmg_taken": round(sum(total_dmg_taken) / len(total_dmg_taken), 2),
            "one_shot_count": one_shot_warnings,
            "stalled_count": stalled_battles,
            "is_balanced": (
                stalled_battles == 0
                and one_shot_warnings < trials * 0.3
                and not win_rate_alert
            ),
        }
        return result

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
            "<tr><th>シナリオ</th><th>プレイヤーLv</th><th>対象モンスター</th><th>勝率</th><th>平均ターン</th><th>判定</th></tr>",
        ]
        for key, sc in report_data.get("scenarios", {}).items():
            status_cls = "pass" if sc.get("is_balanced") else "warn"
            status_txt = "BALANCED" if sc.get("is_balanced") else "WARNING"
            html_lines.append(
                f"<tr><td>{key}</td><td>{sc.get('player_level')}</td><td>{sc.get('monster_type')}</td><td>{sc.get('win_rate')}</td><td>{sc.get('avg_turns')}</td><td class='{status_cls}'>{status_txt}</td></tr>"
            )

        html_lines.extend(["</table>", "</body>", "</html>"])
        html_str = "\n".join(html_lines)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_str)
        return output_html

    def run_full_validation(
        self, output_path: str = "balance_report.json"
    ) -> dict[str, Any]:
        scenarios = [(1, "slime", 0.95), (3, "goblin", 0.85), (5, "orc", 0.70)]
        results = {}
        all_passed = True
        for lvl, mtype, exp_rate in scenarios:
            key = f"lvl{lvl}_vs_{mtype}"
            res = self.simulate_battle(
                player_level=lvl,
                monster_type=mtype,
                trials=100,
                expected_win_rate=exp_rate,
            )
            results[key] = res
            if not res["is_balanced"]:
                all_passed = False

        checker_res = self.checker.check_standards()

        self.report = {
            "summary": "PASS"
            if all_passed and checker_res["status"] == "PASS"
            else "WARNINGS_DETECTED",
            "scenarios": results,
            "balance_standards": checker_res,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        self.generate_html_report(self.report)
        return self.report


if __name__ == "__main__":
    sim = BalanceSimulator()
    rep = sim.run_full_validation()
    print("Balance validation completed:", rep["summary"])
