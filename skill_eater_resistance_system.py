"""Skill Liberation Front (Resistance) and Underground Black Market System.

Handles faction reputation, turn-in contributions, and progressive unlock of facilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DONATION_VALUE_TABLE: Dict[str, int] = {
    "SCRAP_BEAST_FANG": 25,
    "SCRAP_AGILITY_FRAGMENT": 30,
    "SCRAP_IRON_GUARD": 40,
    "SCRAP_DIRTY_BLOW": 25,
    "SCRAP_ACID_DROP": 35,
    "SAFE_PASSWORD_MIDAS_SLUM": 100,
    "SECRET_TUNNEL_MARKET": 150,
}


@dataclass
class ResistanceFactionState:
    """Tracks player standing with the Skill Liberation Front."""

    reputation_points: int = 0
    reputation_level: int = 0  # 0 to 3
    unlocked_facilities: List[str] = field(default_factory=list)
    main_quest_unlocked: bool = False


class ResistanceMarketManager:
    """Manages the Cyber-Fantasy Underground Market and donation rewards."""

    def __init__(self) -> None:
        self.state = ResistanceFactionState()
        self.liaison_npc_name = "レジスタンス連絡員カレン"

    def check_reputation_level_up(self) -> bool:
        """Evaluates thresholds and unlocks new facility tiers."""
        pts = self.state.reputation_points
        old_level = self.state.reputation_level
        if pts >= 300 and self.state.reputation_level < 3:
            self.state.reputation_level = 3
            self.state.main_quest_unlocked = True
        elif pts >= 150 and self.state.reputation_level < 2:
            self.state.reputation_level = 2
            if "ADVANCED_SYNTHESIS_FORGE" not in self.state.unlocked_facilities:
                self.state.unlocked_facilities.append("ADVANCED_SYNTHESIS_FORGE")
        elif pts >= 50 and self.state.reputation_level < 1:
            self.state.reputation_level = 1
            if "FREE_MEDICAL_STATION" not in self.state.unlocked_facilities:
                self.state.unlocked_facilities.append("FREE_MEDICAL_STATION")
        return self.state.reputation_level > old_level

    def donate_items_to_resistance(self, item_ids: List[str]) -> Dict[str, Any]:
        """Donates scraps or salvaged Midas intelligence to raise resistance reputation."""
        earned_rep = 0
        for item_id in item_ids:
            pts = DONATION_VALUE_TABLE.get(item_id, 10)
            earned_rep += pts

        self.state.reputation_points += earned_rep
        new_level_unlocked = self.check_reputation_level_up()

        return {
            "success": True,
            "earned_reputation": earned_rep,
            "total_reputation": self.state.reputation_points,
            "current_level": self.state.reputation_level,
            "level_up": new_level_unlocked,
            "message": f"【解放戦線への貢献】+{earned_rep} 貢献度獲得！（累計: {self.state.reputation_points}）",
        }

    def use_medical_station(self) -> Dict[str, Any]:
        """Uses the unlocked Level 1 Resistance Medical Station to clear toxicity."""
        if "FREE_MEDICAL_STATION" not in self.state.unlocked_facilities:
            return {"success": False, "error": "FACILITY_LOCKED", "message": "貢献度Lv1に達していないため医療設備は利用不可です。"}
        return {
            "success": True,
            "detox_amount": 100,
            "hp_heal": 100,
            "message": "【解放戦線 簡易診療所】にて生体魔力透析を実施。拒絶反応が完全に除去されました。",
        }

    def access_advanced_forge(self) -> Dict[str, Any]:
        """Provides access to Level 2 permanent skill synthesis forge."""
        if "ADVANCED_SYNTHESIS_FORGE" not in self.state.unlocked_facilities:
            return {"success": False, "error": "FACILITY_LOCKED", "message": "貢献度Lv2に達していないため高度合成炉は利用不可です。"}
        return {
            "success": True,
            "can_craft_permanent_skills": True,
            "message": "【解放戦線 高度スキル合成炉】が稼働可能になりました。永続スキルの精製が可能です。",
        }

    def check_main_quest_progression(self) -> Dict[str, Any]:
        """Checks if Level 3 reputation milestone was met to launch the anti-Midas raid."""
        if not self.state.main_quest_unlocked:
            return {"ready": False, "required_points": 300, "current": self.state.reputation_points}
        return {
            "ready": True,
            "quest_id": "QUEST_SE_02_MIDAS_WAREHOUSE_RAID",
            "title": "決戦準備：ミダス商会 第四倉庫襲撃作戦",
            "message": "『よくぞここまで信頼を勝ち取ってくれた！奴らの倉庫を強襲し、奪われた魂を取り戻すぞ！』",
        }

    def get_market_ambient_presentation(self) -> Dict[str, Any]:
        """Provides Cyberpunk x Fantasy hybrid underground market ambient setting."""
        return {
            "bgm": "bgm_resistance_cyber_fantasy_slum.ogg",
            "ambient_sfx": ["amb_neon_hum.ogg", "amb_dripping_water.ogg", "amb_black_market_whisper.ogg"],
            "visual_lighting": "CYAN_MAGENTA_NEON_ON_ANCIENT_STONE",
            "dialogue_tone": "REBEL_SOLIDARITY" if self.state.reputation_level >= 2 else "SUSPICIOUS_WATCHFUL",
        }
