"""Slum Map and Husk NPC Interaction System for Skill Eater World.

Handles exploration, Husk memory extraction, and hidden safe unlocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class HuskNPC:
    """A drained victim whose skills were extracted by Midas Trading Co."""

    npc_id: str
    name: str
    pos: Tuple[int, int]
    memory_key: str
    memory_text: str
    unlocked_secret_type: str  # 'SAFE_CODE', 'SECRET_ROUTE', 'LORE'
    secret_value: str
    is_extracted: bool = False


class SlumMapManager:
    """Manages Slum exploration and interactable environmental secrets."""

    def __init__(self) -> None:
        self.husks: List[HuskNPC] = []
        self.discovered_secrets: Dict[str, str] = {}
        self.unlocked_routes: List[str] = []
        self.journal_log: List[Dict[str, str]] = []
        self.populate_slum_husks()

    def populate_slum_husks(self) -> None:
        """Places Husk NPCs across key slum locations."""
        self.husks = [
            HuskNPC(
                npc_id="HUSK_01",
                name="元査定係の老人",
                pos=(2, 4),
                memory_key="SAFE_PASSWORD_MIDAS_SLUM",
                memory_text="『わしの…スキル帳簿…裏路地の配電盤裏…暗証コードは4989じゃ…』",
                unlocked_secret_type="SAFE_CODE",
                secret_value="4989",
            ),
            HuskNPC(
                npc_id="HUSK_02",
                name="虚ろな目の元傭兵",
                pos=(7, 1),
                memory_key="SECRET_TUNNEL_MARKET",
                memory_text="『あそこの瓦礫の山…押し込めば…闇市へ直通する地下水路がある…』",
                unlocked_secret_type="SECRET_ROUTE",
                secret_value="TUNNEL_SEWER_MARKET",
            ),
        ]

    def analyze_husk(self, npc_id: str) -> Dict[str, Any]:
        """Uses Analysis skill on a Husk NPC to detect residue memories."""
        for husk in self.husks:
            if husk.npc_id == npc_id:
                if husk.is_extracted:
                    return {"success": False, "error": "ALREADY_EXTRACTED", "message": "魂の残滓は完全に枯渇している。"}
                return {
                    "success": True,
                    "npc_id": husk.npc_id,
                    "target_name": husk.name,
                    "detectable_memory": True,
                    "prompt": f"【記憶抽出可能】{husk.name}の脳内に残存する暗号・知識をサルベージしますか？",
                }
        return {"success": False, "error": "NPC_NOT_FOUND"}

    def extract_memory_data(self, npc_id: str) -> Dict[str, Any]:
        """Extracts and salvages memory data from a Husk NPC."""
        for husk in self.husks:
            if husk.npc_id == npc_id:
                if husk.is_extracted:
                    return {"success": False, "error": "ALREADY_EXTRACTED"}
                husk.is_extracted = True
                self.discovered_secrets[husk.memory_key] = husk.secret_value
                if husk.unlocked_secret_type == "SECRET_ROUTE":
                    self.unlocked_routes.append(husk.secret_value)
                self.journal_log.append({"key": husk.memory_key, "entry": husk.memory_text})
                return {
                    "success": True,
                    "npc_id": husk.npc_id,
                    "memory_key": husk.memory_key,
                    "secret_type": husk.unlocked_secret_type,
                    "secret_value": husk.secret_value,
                    "dialogue": husk.memory_text,
                    "message": f"【記憶抽出成功】{husk.name}から重要な知識をサルベージしました。",
                }
        return {"success": False, "error": "NPC_NOT_FOUND"}

    def unlock_slum_hidden_safe(self, entered_code: str) -> Dict[str, Any]:
        """Attempts to open Midas Slum stash using the extracted safe code."""
        correct_code = self.discovered_secrets.get("SAFE_PASSWORD_MIDAS_SLUM", "4989")
        if entered_code == correct_code:
            return {
                "success": True,
                "reward_gold": 1200,
                "reward_item": "RARE_SCRAP_METEOR_FRAGMENT",
                "message": "隠し金庫が開いた！【1200G】と【星屑の破片】を獲得！",
            }
        return {"success": False, "error": "WRONG_CODE", "message": "暗証コードが一致しません。"}

    def check_route_access(self, route_id: str) -> bool:
        """Checks if a secret blocked shortcut route is accessible."""
        return route_id in self.unlocked_routes

    def get_extraction_presentation_fx(self) -> Dict[str, Any]:
        """Provides glitch audio/visual presentation config for memory extraction."""
        return {
            "sound": "se_memory_glitch_extract.ogg",
            "screen_effect": "CRT_WARP_DISTORTION",
            "particles": "FLOATING_TEXT_BINARY_FALL",
            "duration_ms": 1200,
        }
