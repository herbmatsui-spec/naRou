"""Combat-related constants and small data classes (status effects, resistances, aggro)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)
from naRou.constants import Element

# 状態異常
STATUS_POISON = "毒"
STATUS_PARALYSIS = "麻痺"
STATUS_CONFUSION = "混乱"
STATUS_BLIND = "盲目"
STATUS_BLEEDING = "出血"  # ステップ45
STATUS_HASTE = "加速"
STATUS_SLOW = "鈍足"
STATUS_RETURN = "帰還待機"  # ステップ63 遅延ワープ

# ファクション (ステップ42)
FACTION_PLAYER = "player"
FACTION_MONSTER = "monster"
FACTION_TOWNSFOLK = "townsfolk"
FACTION_GUARD = "guard"


@dataclass
class StatusEffect:
    """状態異常 - Tick連動(ステップ16)"""

    name: str
    remaining_ticks: int  # 残り持続Tick
    power: int = 1  # 効果の強さ
    source: str | None = None


class ResistanceSet:
    """属性耐性セット (ステップ37)"""

    def __init__(self):
        self.fire = 0  # -100〜100, 0=通常, 100=無効, -50=弱点(1.5倍)
        self.cold = 0
        self.lightning = 0
        self.darkness = 0
        self.chaos = 0
        self.magic = 0

    def get(self, element: Element) -> int:
        mapping = {
            Element.FIRE: self.fire,
            Element.COLD: self.cold,
            Element.LIGHTNING: self.lightning,
            Element.DARKNESS: self.darkness,
            Element.CHAOS: self.chaos,
            Element.MAGIC: self.magic,
        }
        return mapping.get(element, 0)


class AggroList:
    """ヘイトリスト (ステップ42)"""

    def __init__(self):
        self._table: dict[str, int] = {}  # entity name -> hate_value

    def add_hate(self, target_name: str, amount: int) -> None:
        self._table[target_name] = self._table.get(target_name, 0) + amount

    def top_target(self) -> str | None:
        if not self._table:
            return None
        return max(self._table, key=lambda k: self._table[k])
