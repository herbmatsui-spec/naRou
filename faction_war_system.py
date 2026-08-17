"""
派閥抗争システム (ファクションウォー)
派閥データの管理・影響力変動計算・抗争条件判定・影響力適用
Steps 52-58
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import yaml
from pathlib import Path

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class FactionWarData:
    """派閥抗争マスターデータ (Step 53)"""
    id: str
    name: str
    color: List[int] = field(default_factory=lambda: [255, 255, 255])
    territories: List[str] = field(default_factory=list)
    allied_factions: List[str] = field(default_factory=list)
    rival_factions: List[str] = field(default_factory=list)
    influence: int = 50


class FactionWarRegistry:
    """派閥抗争レジストリ (シングルトン) (Steps 54, 55)"""
    _instance: Optional['FactionWarRegistry'] = None
    _factions: Dict[str, FactionWarData] = {}
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
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            fw_data = data.get('faction_war_conditions', {})
            for fid, f_dict in fw_data.items():
                faction = FactionWarData(
                    id=fid,
                    name=f_dict.get('name', fid),
                    color=f_dict.get('color') or [255, 255, 255],
                    territories=f_dict.get('territories') or [],
                    allied_factions=f_dict.get('allied_factions') or [],
                    rival_factions=f_dict.get('rival_factions') or [],
                    influence=f_dict.get('influence', 50)
                )
                self._factions[fid] = faction
            self._loaded = True
        except Exception:
            self._loaded = True

    def get(self, faction_id: str) -> Optional[FactionWarData]:
        """特定派閥抗争データを取得 (Step 54)"""
        return self._factions.get(faction_id)

    def all(self) -> Dict[str, FactionWarData]:
        """すべての派閥抗争データ辞書を返す (Step 54)"""
        return self._factions


REGISTRY = FactionWarRegistry()


class FactionWarManager:
    """派閥抗争管理マネージャー (Steps 56-58)"""

    def __init__(self, registry: Optional[FactionWarRegistry] = None):
        self.registry = registry or REGISTRY

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
        if faction2_id in f1.rival_factions or faction1_id in f2.rival_factions:
            return True
        return False

    def apply_influence_effects(self, faction_id: str, change: int) -> None:
        """影響力変動を適用 (Step 56)"""
        faction = self.registry.get(faction_id)
        if not faction:
            return
        faction.influence = max(0, min(100, faction.influence + change))
