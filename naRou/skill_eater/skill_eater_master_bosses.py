"""
Skill Eater Phase 3: Master Skill Bosses System (Steps 23-30)
スキル銀行本部の各部門を守護するマスタースキル保持者たち（四天王格）のバトルと弱点ハック、概念の鍵ドロップを管理。
"""

from typing import Any, Dict, List


class MasterBossManager:
    """
    マスタースキル保持者（四天王）戦闘マネージャー
    """

    def __init__(self):
        # Step 24: ボス定義
        self.bosses: Dict[str, Dict[str, Any]] = {
            "investment_boss": {
                "name": "増殖の投資卿バルバトス",
                "department": "投資信託部門",
                "hp": 8000,
                "max_hp": 8000,
                "master_skill": "Compound Multiplication (無限複利増殖)",
                "weakness_fusion_keyword": "Fire + Ice",  # 熱狂ショック合成が弱点
                "barrier_active": True,
                "is_defeated": False,
            },
            "debt_boss": {
                "name": "収奪の執行長レヴィアタン",
                "department": "負債回収部門",
                "hp": 12000,
                "max_hp": 12000,
                "master_skill": "Absolute Foreclosure (絶対差押領)",
                "weakness_fusion_keyword": "Defense + Sword",  # 剛剣両断合成が弱点
                "barrier_active": True,
                "is_defeated": False,
            },
        }
        self.collected_concept_keys: List[str] = []

    def attack_master_boss(self, boss_id: str, damage: int, used_skill_name: str) -> Dict[str, Any]:
        """Step 25, 26, 27, 28: ボス戦闘と専用弱点によるバリア解除"""
        if boss_id not in self.bosses:
            return {"error": "Boss not found"}

        boss = self.bosses[boss_id]
        if boss["is_defeated"]:
            return {"error": "Boss already defeated"}

        effective_damage = damage
        weakness_hit = False

        # Step 28: 専用弱点スキルの判定
        if boss["weakness_fusion_keyword"] in used_skill_name:
            boss["barrier_active"] = False
            effective_damage = damage * 3
            weakness_hit = True
            msg = f"WEAKNESS BREACH: [{used_skill_name}] shattered {boss['name']}'s Master Barrier!"
        else:
            if boss["barrier_active"]:
                effective_damage = int(damage * 0.20)  # バリア展開中はダメージ80%カット
                msg = f"BARRIER ACTIVE: Master Skill absorbed the attack. (Dealt {effective_damage} dmg)"
            else:
                msg = f"Direct hit! (Dealt {effective_damage} dmg)"

        boss["hp"] = max(0, boss["hp"] - effective_damage)

        if boss["hp"] <= 0:
            boss["is_defeated"] = True
            return self._resolve_boss_defeat(boss_id, weakness_hit=weakness_hit)

        return {
            "boss_name": boss["name"],
            "remaining_hp": boss["hp"],
            "max_hp": boss["max_hp"],
            "barrier_active": boss["barrier_active"],
            "weakness_hit": weakness_hit,
            "message": msg,
        }

    def _resolve_boss_defeat(self, boss_id: str, weakness_hit: bool = False) -> Dict[str, Any]:
        """Step 29 & 30: 撃破時のマスタースキル強奪と概念の鍵ドロップ"""
        boss = self.bosses[boss_id]
        concept_key = f"Concept Key of {boss['department']}"
        self.collected_concept_keys.append(concept_key)

        return {
            "boss_defeated": True,
            "weakness_hit": weakness_hit,
            "boss_name": boss["name"],
            "stolen_master_skill": boss["master_skill"],
            "dropped_concept_key": concept_key,
            "total_keys_collected": self.collected_concept_keys,
            "message": f"MASTER DEFEATED: {boss['name']} was neutralized! Acquired [{concept_key}]!",
        }
