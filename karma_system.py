"""
カーマシステム
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class KarmaData:
    """カーマデータクラス"""

    id: str
    name: str
    description: str
    alignment_ranges: dict[str, dict[str, Any]]
    actions: dict[str, dict[str, int]]
    reincarnation_effects: dict[str, Any]


class KarmaRegistry:
    """カーマレジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, KarmaData] = {}
        return cls._instance

    def load(self, path: str = "data/karma.yaml") -> None:
        """YAMLファイルからカーマデータを読み込み"""
        self._data.clear()
        alignment_ranges = {
            "law_chaos": {"range": [-100, 100], "neutral": 0},
            "good_evil": {"range": [-100, 100], "neutral": 0},
        }
        actions = {
            "help_innocent": {"law_chaos": 5, "good_evil": 10},
            "defeat_monster": {"law_chaos": 0, "good_evil": 1},
            "donate_to_temple": {"law_chaos": 1, "good_evil": 2},
            "steal": {"law_chaos": -1, "good_evil": -2},
            "murder_innocent": {"law_chaos": -2, "good_evil": -5},
        }
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if raw and "karma" in raw:
                    k = raw["karma"]
                    if "alignment" in k:
                        alignment_ranges = k["alignment"]
                    if "actions" in k:
                        actions.update(k["actions"])
            except Exception:
                logger.exception("Unhandled exception")
                # TODO: handle exception properly
                pass

        default_data = KarmaData(
            id="default",
            name="デフォルトカーマ",
            description="基本的なカーマシステム",
            alignment_ranges=alignment_ranges,
            actions=actions,
            reincarnation_effects={"stat_bonus": 5},
        )
        self._data["default"] = default_data

    def all(self) -> dict[str, KarmaData]:
        """全カーマデータを取得"""
        return self._data.copy()

    def get(self, karma_id: str = "default") -> KarmaData | None:
        """特定のカーマデータを取得"""
        return self._data.get(karma_id or "default")


# グローバルレジストリインスタンス
REGISTRY = KarmaRegistry()


class KarmaManager:
    """カーマ管理クラス"""

    def __init__(self, registry: KarmaRegistry | None = None):
        self.registry = registry or REGISTRY

    def update_karma(self, player: Any, action: str, amount: int = 1) -> tuple[int, int]:
        """カーマを更新"""
        karma_data = self.registry.get("default")
        if not karma_data:
            return getattr(player, "karma_law_chaos", 0), getattr(player, "karma_good_evil", 0)

        action_data = karma_data.actions.get(action, {"law_chaos": 0, "good_evil": 0})
        law_chaos_change = action_data.get("law_chaos", 0) * amount
        good_evil_change = action_data.get("good_evil", 0) * amount

        player.karma_law_chaos += law_chaos_change
        player.karma_good_evil += good_evil_change

        # 範囲制限
        law_chaos_range = karma_data.alignment_ranges.get("law_chaos", {}).get("range", [-100, 100])
        good_evil_range = karma_data.alignment_ranges.get("good_evil", {}).get("range", [-100, 100])

        player.karma_law_chaos = max(
            law_chaos_range[0], min(law_chaos_range[1], player.karma_law_chaos)
        )
        player.karma_good_evil = max(
            good_evil_range[0], min(good_evil_range[1], player.karma_good_evil)
        )
        return player.karma_law_chaos, player.karma_good_evil

    def get_karma_bonuses(self, player: Any) -> dict[str, Any]:
        """カーマボーナスを取得"""
        return {"stat_bonus": 5}
