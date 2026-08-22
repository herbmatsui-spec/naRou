"""
Skill Eater Phase 3: Concept Trials System (Steps 33-37)
9柱の概念（時間・破壊・空間等）が支配する特殊ルール付き試練空間を管理。
"""

from typing import Any, Dict, List


class ConceptTrialsManager:
    """
    9柱の概念試練マネージャー
    """

    def __init__(self):
        # Step 34: 試練空間定義
        self.trials: Dict[str, Dict[str, Any]] = {
            "trial_of_time": {
                "name": "時間領域の試練 (Chrono Trial)",
                "required_key": "Concept Key of 投資信託部門",
                "special_rule": "REVERSE_TURN_ORDER",
                "cleared": False,
                "reward_passive": "Chrono Mastery (先行確定)",
            },
            "trial_of_destruction": {
                "name": "破壊領域の試練 (Ruin Trial)",
                "required_key": "Concept Key of 負債回収部門",
                "special_rule": "DOUBLE_DAMAGE_REDUCED_MAX_HP",
                "cleared": False,
                "reward_passive": "Ruin Overcharge (クリティカル威力+100%)",
            },
        }
        self.cleared_trials: List[str] = []
        self.unlocked_passives: List[str] = []

    def enter_trial(self, trial_id: str, player_keys: List[str]) -> Dict[str, Any]:
        """Step 34: 試練領域への入場判定"""
        if trial_id not in self.trials:
            return {"success": False, "message": "Trial not found."}

        trial = self.trials[trial_id]
        if trial["required_key"] not in player_keys:
            return {
                "success": False,
                "message": f"Access Denied: Requires [{trial['required_key']}].",
            }

        return {
            "success": True,
            "trial_name": trial["name"],
            "rule": trial["special_rule"],
            "message": f"Entered [{trial['name']}]. Special rule active: {trial['special_rule']}",
        }

    def apply_trial_rule_effect(
        self, trial_id: str, player_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 35 & 36: 時間領域・破壊領域等の特殊ルール処理"""
        if trial_id not in self.trials:
            return player_stats

        rule = self.trials[trial_id]["special_rule"]
        modified = dict(player_stats)

        if rule == "REVERSE_TURN_ORDER":
            # ターン巻き戻し効果：毎ターンHPが微量回復するがクールダウン増加
            modified["auto_regen"] = 50
            modified["turn_penalty"] = True
        elif rule == "DOUBLE_DAMAGE_REDUCED_MAX_HP":
            # 火力倍増・最大HP半減
            modified["damage_multiplier"] = modified.get("damage_multiplier", 1.0) * 2.0
            modified["max_hp"] = max(1, modified.get("max_hp", 100) // 2)

        return modified

    def complete_trial(self, trial_id: str) -> Dict[str, Any]:
        """Step 37: 試練クリアと理の克服パッシブアンロック"""
        if trial_id not in self.trials:
            return {"success": False, "message": "Trial not found."}

        trial = self.trials[trial_id]
        trial["cleared"] = True
        self.cleared_trials.append(trial_id)
        self.unlocked_passives.append(trial["reward_passive"])

        return {
            "success": True,
            "trial_name": trial["name"],
            "unlocked_passive": trial["reward_passive"],
            "all_passives": self.unlocked_passives,
            "message": f"TRIAL OVERCOME: Mastered the concept! Granted [{trial['reward_passive']}].",
        }
