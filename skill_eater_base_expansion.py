"""
Skill Eater Phase 2: Base Expansion System (Steps 7-14)
ジャンクや余剰スキルをレジスタンス拠点（スラム地下闇市場）に投資し、拠点レベル（Tier）を上げ、
施設、商人、パッシブバフ、モニュメントをアンロックする。
"""

from typing import Any, Dict, List, Optional


class SlumBaseExpansionManager:
    """
    レジスタンス拠点拡張・復興マネージャー
    """

    def __init__(self):
        self.invested_junk = 0
        self.invested_skill_points = 0
        self.base_tier = 1  # 1: 泥水のスラム, 2: ネオン地下街, 3: 解放戦線要塞
        self.max_tier = 3
        self.unlocked_facilities: List[str] = ["basic_workshop"]
        self.unlocked_merchants: List[str] = ["junk_trader"]
        self.passive_buffs: Dict[str, float] = {
            "exploration_efficiency": 1.0,
            "crafting_success_rate": 0.85,
            "trap_damage_bonus": 0.0,
        }
        self.built_monuments: List[str] = []
        self._tier_thresholds = {2: {"junk": 500, "skills": 5}, 3: {"junk": 2000, "skills": 20}}

    def invest_resources(self, junk_amount: int = 0, skill_point_amount: int = 0) -> Dict[str, Any]:
        """Step 8 & 13: リソースプール管理と不可逆な投資（ロールバック防止）"""
        if junk_amount < 0 or skill_point_amount < 0:
            return {"success": False, "message": "Invalid investment amount"}

        self.invested_junk += junk_amount
        self.invested_skill_points += skill_point_amount

        tier_up_res = self.check_and_update_tier()

        return {
            "success": True,
            "current_tier": self.base_tier,
            "invested_junk": self.invested_junk,
            "invested_skill_points": self.invested_skill_points,
            "tier_up_event": tier_up_res,
        }

    def check_and_update_tier(self) -> Optional[Dict[str, Any]]:
        """Step 9, 10, 11: Tier判定、アンロック、パッシブバフ付与"""
        new_tier = self.base_tier
        if self.base_tier < 2:
            req = self._tier_thresholds[2]
            if self.invested_junk >= req["junk"] and self.invested_skill_points >= req["skills"]:
                new_tier = 2
        if new_tier == 2 or self.base_tier == 2:
            req = self._tier_thresholds[3]
            if self.invested_junk >= req["junk"] and self.invested_skill_points >= req["skills"]:
                new_tier = 3

        if new_tier > self.base_tier:
            old_tier = self.base_tier
            self.base_tier = new_tier
            self._apply_tier_unlocks(new_tier)
            return {
                "old_tier": old_tier,
                "new_tier": new_tier,
                "message": f"Slum Base Upgraded to Tier {new_tier}!",
                "unlocked_facilities": self.unlocked_facilities,
                "passive_buffs": self.passive_buffs,
            }
        return None

    def _apply_tier_unlocks(self, tier: int):
        """Tierごとの施設・商人・バフ反映"""
        if tier == 2:
            self.unlocked_facilities.extend(["cyber_lab", "underground_arena"])
            self.unlocked_merchants.append("black_market_hacker")
            self.passive_buffs["exploration_efficiency"] = 1.25
            self.passive_buffs["crafting_success_rate"] = 0.95
            self.passive_buffs["trap_damage_bonus"] = 0.20
        elif tier == 3:
            self.unlocked_facilities.extend(["resistance_command_center", "meta_reactor"])
            self.unlocked_merchants.append("legendary_broker")
            self.passive_buffs["exploration_efficiency"] = 1.50
            self.passive_buffs["crafting_success_rate"] = 1.00
            self.passive_buffs["trap_damage_bonus"] = 0.50

    def unlock_special_monument(self, rare_skill_name: str) -> Dict[str, Any]:
        """Step 12: 特定レアスキル投資によるモニュメントアンロック"""
        monument_id = f"Monument of {rare_skill_name}"
        if monument_id in self.built_monuments:
            return {"success": False, "message": f"{monument_id} already exists."}

        self.built_monuments.append(monument_id)
        # モニュメント効果: 拠点全体のトラップ威力さらに+10%
        self.passive_buffs["trap_damage_bonus"] += 0.10
        return {
            "success": True,
            "monument": monument_id,
            "message": f"Special monument constructed: {monument_id}!",
            "bonus": "Trap Damage +10%",
        }

    def get_base_status_ui(self) -> Dict[str, Any]:
        """Step 14: フレーバーテキスト / UI用ステータス出力"""
        tier_names = {
            1: "泥水のスラム地下街 (Muddy Slum Outpost)",
            2: "ネオン輝くサイバー闇市場 (Neon Cyber Black Market)",
            3: "解放戦線・最終難攻不落要塞 (Resistance Megafortress)",
        }
        return {
            "base_name": tier_names.get(self.base_tier, "Unknown"),
            "tier": self.base_tier,
            "total_junk": self.invested_junk,
            "total_skills": self.invested_skill_points,
            "facilities": list(set(self.unlocked_facilities)),
            "merchants": list(set(self.unlocked_merchants)),
            "buffs": self.passive_buffs,
            "monuments": self.built_monuments,
        }
