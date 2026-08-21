"""
輪廻転生システム
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ReincarnationData:
    """転生データクラス"""

    id: str
    min_level: int
    max_level: int
    stat_bonus: int
    level_reset_multiplier: float
    name: str
    description: str


class ReincarnationRegistry:
    """称号レジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, ReincarnationData] = {}
        return cls._instance

    def load(self, path: str = "data/reincarnation.yaml") -> None:
        """YAMLファイルから転生データを読み込み"""
        self._data.clear()

        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data and "reincarnation" in data:
                    # 基本要件を全転生データに適用
                    base_req = data["reincarnation"].get("base_requirements", {})

                    # デフォルト転生データを作成（実際のゲームでは複数の転生タイプがあるかもしれない）
                    default_data = ReincarnationData(
                        id="default",
                        min_level=base_req.get("min_level", 50),
                        max_level=base_req.get("max_level", 200),
                        stat_bonus=base_req.get("stat_bonus_per_reincarnation", 5),
                        level_reset_multiplier=base_req.get(
                            "level_reset_multiplier", 0.1
                        ),
                        name="輪廻転生",
                        description="一定レベルに到達すると転生が可能になる",
                    )
                    self._data["default"] = default_data
            else:
                # ファイルが存在しない場合のデフォルトデータ
                default_data = ReincarnationData(
                    id="default",
                    min_level=50,
                    max_level=200,
                    stat_bonus=5,
                    level_reset_multiplier=0.1,
                    name="輪廻転生",
                    description="一定レベルに到達すると転生が可能になる",
                )
                self._data["default"] = default_data

        except Exception as e:
            logger.warning("Error loading reincarnation data from yaml: %s", e)
            # エラー時のデフォルトデータ
            default_data = ReincarnationData(
                id="default",
                min_level=50,
                max_level=200,
                stat_bonus=5,
                level_reset_multiplier=0.1,
                name="輪廻転生",
                description="一定レベルに到達すると転生が可能になる",
            )
            self._data["default"] = default_data

    def all(self) -> dict[str, ReincarnationData]:
        """全転生データを取得"""
        return self._data.copy()

    def get(self, reincarnation_id: str) -> ReincarnationData | None:
        """特定の転生データを取得"""
        return self._data.get(reincarnation_id)


# グローバルレジストリインスタンス
REGISTRY = ReincarnationRegistry()


class ReincarnationManager:
    """転生管理クラス"""

    def __init__(self, registry: ReincarnationRegistry | None = None):
        self.registry = registry or REGISTRY

    def can_reincarnate(self, player: Any) -> bool:
        """転生可能かチェック"""
        # 基本的なレベルチェック
        reincarnation_data = self.registry.get("default")
        if not reincarnation_data:
            return False

        return (
            player.level >= reincarnation_data.min_level
            and player.level <= reincarnation_data.max_level
        )

    def reincarnate(self, player: Any, engine: Any | None = None) -> bool:
        """転生を実行"""
        if not self.can_reincarnate(player):
            return False

        # 転生データを取得
        reincarnation_data = self.registry.get("default")
        if not reincarnation_data:
            return False

        # 1. 前世の総括と動的記憶の欠片の生成・付与
        try:
            from meta_progression_system import (
                MemoryFragmentGenerator,
                MetaProgressionManager,
            )

            frag = MemoryFragmentGenerator.generate(
                player=player,
                trigger_type="reincarnation",
                context={"reincarnation_count": player.reincarnation_count},
            )
            # メタ進行マネージャー経由で記憶を付与
            if engine and hasattr(engine, "meta_progression_manager"):
                engine.meta_progression_manager.add_memory_fragment(
                    player, frag, engine
                )
            else:
                MetaProgressionManager().add_memory_fragment(player, frag, engine)
        except Exception as e:
            logger.warning("[ReincarnationManager] Memory fragment creation failed: %s", e)

        # 2. 次世代のランダム周回特異点・フラグの抽選
        try:
            from meta_progression_system import MetaProgressionManager

            mgr = (
                engine.meta_progression_manager
                if (engine and hasattr(engine, "meta_progression_manager"))
                else MetaProgressionManager()
            )
            mods = mgr.roll_cycle_modifiers(count=2)
            player.cycle_modifiers = mods
        except Exception as e:
            logger.warning("[ReincarnationManager] Cycle modifier rolling failed: %s", e)

        # 3. 転生処理
        player.reincarnation_count += 1
        if hasattr(player, "total_level_earned"):
            player.total_level_earned += player.level

        # レベルをリセット（初期レベル1に戻る）
        player.level = 1
        player.exp = 0
        if hasattr(player, "exp_next"):
            player.exp_next = 100

        # 4. 永続ボーナスの再計算とステータス初期化
        try:
            from meta_progression_system import MetaProgressionManager

            mgr = (
                engine.meta_progression_manager
                if (engine and hasattr(engine, "meta_progression_manager"))
                else MetaProgressionManager()
            )
            mgr.recalculate_and_apply_bonuses(player)
        except Exception as e:
            logger.warning("[ReincarnationManager] Bonus recalculation failed: %s", e)

        if engine and hasattr(engine, "log"):
            engine.log(
                f"★転生を実行した！ (転生回数: {player.reincarnation_count}, 累計レベル: {getattr(player, 'total_level_earned', 0)})",
                (255, 215, 0),
            )
            if player.cycle_modifiers:
                mod_names = "、".join(
                    [
                        m.get("name", "")
                        for m in player.cycle_modifiers
                        if isinstance(m, dict)
                    ]
                )
                engine.log(
                    f"⚡【運命の特異点】新たな時代の法則: {mod_names}", (150, 220, 255)
                )

        return True
