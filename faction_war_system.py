"""
派閥抗争システム (ファクションウォー)
派閥データの管理・影響力変動計算・抗争条件判定・影響力適用
Steps 52-58
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecs.entity import Entity

import yaml

from protocols import MemoryRegistryProtocol

# Phase 2 連携：遅延インポート
try:
    from npc_memory_system import GLOBAL_MEMORY_REGISTRY, MemoryImportance, MemoryType

    _HAS_NPC_MEMORY = True
except ImportError:
    GLOBAL_MEMORY_REGISTRY = None
    MemoryType = None
    MemoryImportance = None
    _HAS_NPC_MEMORY = False


@dataclass
class FactionWarData:
    """派閥抗争マスターデータ (Step 53)"""

    id: str
    name: str
    color: list[int] = field(default_factory=lambda: [255, 255, 255])
    territories: list[str] = field(default_factory=list)
    allied_factions: list[str] = field(default_factory=list)
    rival_factions: list[str] = field(default_factory=list)
    influence: int = 50


class FactionWarRegistry:
    """派閥抗争レジストリ (シングルトン) (Steps 54, 55)"""

    _instance: FactionWarRegistry | None = None
    _factions: dict[str, FactionWarData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._factions = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/faction_war.yaml") -> None:
        """YAMLから派閥抗争定義をロード (Step 55)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            fw_data = data.get("faction_war_conditions", {})
            for fid, f_dict in fw_data.items():
                faction = FactionWarData(
                    id=fid,
                    name=f_dict.get("name", fid),
                    color=f_dict.get("color") or [255, 255, 255],
                    territories=f_dict.get("territories") or [],
                    allied_factions=f_dict.get("allied_factions") or [],
                    rival_factions=f_dict.get("rival_factions") or [],
                    influence=f_dict.get("influence", 50),
                )
                self._factions[fid] = faction
            self._loaded = True
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            self._loaded = True

    def get(self, faction_id: str) -> FactionWarData | None:
        """特定派閥抗争データを取得 (Step 54)"""
        return self._factions.get(faction_id)

    def all(self) -> dict[str, FactionWarData]:
        """すべての派閥抗争データ辞書を返す (Step 54)"""
        return self._factions


REGISTRY = FactionWarRegistry()


class FactionWarManager:
    """派閥抗争管理マネージャー (Steps 56-58)"""

    def __init__(
        self,
        registry: FactionWarRegistry | None = None,
        memory_registry: MemoryRegistryProtocol | None = None,
    ):
        self.registry = registry or REGISTRY
        self.memory_registry = memory_registry or (
            GLOBAL_MEMORY_REGISTRY if _HAS_NPC_MEMORY else None
        )

    def calculate_influence_change(self, faction_id: str, game_state: Any = None) -> int:
        """影響力の自然変動量を計算 (Step 57)"""
        faction = self.registry.get(faction_id)
        if not faction:
            return 0
        # 領土数による影響力補正 (+1/領土)
        territory_bonus = len(faction.territories)
        # 同盟数によるプラス影響
        ally_bonus = len(faction.allied_factions)
        # ライバル存在による牽制
        rival_penalty = len(faction.rival_factions)
        change = territory_bonus + ally_bonus - rival_penalty
        return max(-5, min(5, change))

    def check_war_conditions(self, faction1_id: str, faction2_id: str) -> bool:
        """2つの派閥間で抗争が発生する条件をチェック (Step 58)"""
        f1 = self.registry.get(faction1_id)
        f2 = self.registry.get(faction2_id)
        if not f1 or not f2:
            return False
        # ライバル関係にあるか
        return bool(faction2_id in f1.rival_factions or faction1_id in f2.rival_factions)

    def apply_influence_effects(self, faction_id: str, change: int) -> None:
        """影響力変動を適用 (Step 56)"""
        faction = self.registry.get(faction_id)
        if not faction:
            return
        faction.influence = max(0, min(100, faction.influence + change))

        # Phase 2 連携：派閥影響力変動を NPC 記憶に記録
        if self.memory_registry and change != 0:
            for mgr in self.memory_registry.all_managers().values():
                # 同派閥 NPC に記録
                if getattr(mgr.npc, "faction_id", None) == faction_id:
                    importance = (
                        MemoryImportance.SIGNIFICANT
                        if (MemoryImportance and abs(change) > 5)
                        else (MemoryImportance.NOTABLE if MemoryImportance else None)
                    )
                    mgr.record_reputation_event(
                        subject_id=faction_id,
                        event_type="faction_influence_change",
                        delta=change,
                        source="faction_system",
                        importance=importance,
                    )

    # Phase 2 連携メソッド
    def get_faction_reputation_for_gate(self, player: Entity, faction_id: str) -> int:
        """ReputationGate 用派閥評判値取得（0-100 -> -100 to 100）"""
        faction = self.registry.get(faction_id)
        if not faction:
            return -50
        # 派閥影響力 0-100 を -100 to 100 にマッピング
        # プレイヤーの faction_reputation も加味
        player_rep = player.faction_reputation.get(faction_id, 0)
        return (faction.influence - 50) + player_rep

    def get_all_faction_reputations(self, player: Entity) -> dict[str, int]:
        """全派閥評判取得（噂伝播・評判ゲート用）"""
        result = {}
        for fid in self.registry.all():
            result[fid] = self.get_faction_reputation_for_gate(player, fid)
        return result

    def apply_rumor_influence(
        self,
        faction_id: str,
        delta: int,
        source: str = "rumor",
    ) -> bool:
        """噂伝播による派閥影響力変動（Phase 2 Step 6 連携）"""
        faction = self.registry.get(faction_id)
        if not faction:
            return False
        old = faction.influence
        faction.influence = max(0, min(100, faction.influence + delta))
        return faction.influence != old

    def get_rumor_spread_modifier(self, from_faction: str, to_faction: str) -> float:
        """噂伝播修正値取得（同盟=+0.2, 敵対=-0.3, 中立=0）"""
        if from_faction == to_faction:
            return 0.2
        f1 = self.registry.get(from_faction)
        f2 = self.registry.get(to_faction)
        if not f1 or not f2:
            return 0.0
        if self.check_war_conditions(from_faction, to_faction):
            return -0.3
        if to_faction in f1.allied_factions:
            return 0.2
        return 0.0
