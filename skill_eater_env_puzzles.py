"""
Skill Eater Phase 2: Environmental Puzzles System (Steps 33-39)
サイバーパンク×ファンタジーの環境ギミック、複合属性による解除、トラップ判定、隠しエリア報酬。
"""

from typing import Any, Dict, List, Set


class EnvironmentalPuzzleManager:
    """
    環境ギミック・探索パズルマネージャー
    """

    def __init__(self):
        # Step 34: ギミック定義
        self.puzzles: Dict[str, Dict[str, Any]] = {
            "neon_security_gate": {
                "name": "高電圧ネオン隔壁",
                "required_skills": ["Lightning Magic", "Network Hacking"],
                "required_power": 50,
                "is_solved": False,
                "reward_secret": "Hidden Storage Room: 500 Junk & Rare Core",
                "failure_trap_damage": 35,
            },
            "toxic_steam_vent": {
                "name": "腐食性魔導蒸気弁",
                "required_skills": ["Dimensional Storage", "Frost Magic"],
                "required_power": 40,
                "is_solved": False,
                "reward_secret": "Old Resistance Cache: Master Skill Blueprint",
                "failure_trap_damage": 50,
            },
        }
        self.solved_puzzles: Set[str] = set()

    def inspect_puzzle(self, puzzle_id: str) -> Dict[str, Any]:
        """ギミックの詳細と要求スキル確認"""
        if puzzle_id not in self.puzzles:
            return {"error": "Puzzle not found"}
        puzzle = self.puzzles[puzzle_id]
        return {
            "puzzle_id": puzzle_id,
            "name": puzzle["name"],
            "required_skills": puzzle["required_skills"],
            "is_solved": puzzle["is_solved"],
        }

    def attempt_solve_puzzle(
        self, puzzle_id: str, player_equipped_skills: List[str], player_power: int
    ) -> Dict[str, Any]:
        """Step 35, 36, 37, 38, 39: 複合ギミック判定、フラグ管理、トラップ、隠し報酬"""
        if puzzle_id not in self.puzzles:
            return {"success": False, "message": "Puzzle does not exist."}

        puzzle = self.puzzles[puzzle_id]
        if puzzle["is_solved"]:
            return {"success": True, "message": "Puzzle already solved.", "already_open": True}

        req_skills = set(puzzle["required_skills"])
        player_skills = set(player_equipped_skills)

        # Step 36: 複合ギミックチェック（すべての要求スキルを所持しているか）
        has_all_skills = req_skills.issubset(player_skills)
        has_enough_power = player_power >= puzzle["required_power"]

        if has_all_skills and has_enough_power:
            # Step 37 & 39: 解除成功、ゲート開放、隠し報酬
            puzzle["is_solved"] = True
            self.solved_puzzles.add(puzzle_id)
            return {
                "success": True,
                "message": f"Puzzle [{puzzle['name']}] SOLVED! Security breached.",
                "opened_gate": True,
                "secret_reward": puzzle["reward_secret"],
            }
        else:
            # Step 38: 失敗時のトラップ発動
            missing_skills = list(req_skills - player_skills)
            return {
                "success": False,
                "message": "Failed to bypass security mechanism. Defensive countermeasure triggered!",
                "trap_damage": puzzle["failure_trap_damage"],
                "missing_skills": missing_skills,
                "power_sufficient": has_enough_power,
            }
