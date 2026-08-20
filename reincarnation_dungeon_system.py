"""
転生専用ダンジョンシステム
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class ReincarnationDungeonData:
    """転生ダンジョンデータクラス"""

    id: str
    min_reincarnation: int
    max_reincarnation: int
    name: str
    description: str
    floors: int
    rewards: list[str]
    unlock_condition: dict[str, Any]
    is_arena: bool


class ReincarnationDungeonRegistry:
    """転生ダンジョンレジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, ReincarnationDungeonData] = {}
        return cls._instance

    def load(self, path: str = "data/reincarnation_dungeons.yaml") -> None:
        """YAMLファイルから転生ダンジョンデータを読み込み"""
        self._data.clear()

        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data and "dungeons" in data:
                    for did, d in data["dungeons"].items():
                        if d is None:
                            continue
                        dungeon_data = ReincarnationDungeonData(
                            id=did,
                            min_reincarnation=d.get("min_reincarnation", 0),
                            max_reincarnation=d.get("max_reincarnation", 100),
                            name=d.get("name", "Unknown Dungeon"),
                            description=d.get("description", ""),
                            floors=d.get("floors", 1),
                            rewards=d.get("rewards", []),
                            unlock_condition=d.get("unlock_condition", {}),
                            is_arena=d.get("is_arena", False),
                        )
                        self._data[did] = dungeon_data
                else:
                    # ファイルがあるがデータがない場合のデフォルトデータ
                    default_data = ReincarnationDungeonData(
                        id="first_life_trial",
                        min_reincarnation=0,
                        max_reincarnation=0,
                        name="最初の試練",
                        description="転生0回目のプレイヤーのための試練ダンジョン",
                        floors=5,
                        rewards=["small_gold_pouch", "healing_herb"],
                        unlock_condition={"reincarnation_count": 0},
                        is_arena=False,
                    )
                    self._data["first_life_trial"] = default_data
            else:
                # ファイルが存在しない場合のデフォルトデータ
                default_data = ReincarnationDungeonData(
                    id="first_life_trial",
                    min_reincarnation=0,
                    max_reincarnation=0,
                    name="最初の試練",
                    description="転生0回目のプレイヤーのための試練ダンジョン",
                    floors=5,
                    rewards=["small_gold_pouch", "healing_herb"],
                    unlock_condition={"reincarnation_count": 0},
                    is_arena=False,
                )
                self._data["first_life_trial"] = default_data

        except Exception as e:
            print(f"Error loading reincarnation dungeon data: {e}")
            # エラー時のデフォルトデータ
            default_data = ReincarnationDungeonData(
                id="first_life_trial",
                min_reincarnation=0,
                max_reincarnation=0,
                name="最初の試練",
                description="転生0回目のプレイヤーのための試練ダンジョン",
                floors=5,
                rewards=["small_gold_pouch", "healing_herb"],
                unlock_condition={"reincarnation_count": 0},
                is_arena=False,
            )
            self._data["first_life_trial"] = default_data

    def all(self) -> dict[str, ReincarnationDungeonData]:
        """全転生ダンジョンデータを取得"""
        return self._data.copy()

    def get(self, dungeon_id: str) -> ReincarnationDungeonData | None:
        """特定の転生ダンジョンデータを取得"""
        return self._data.get(dungeon_id)


# グローバルレジストリインスタンス
REGISTRY = ReincarnationDungeonRegistry()


class ReincarnationDungeonManager:
    """転生ダンジョン管理クラス"""

    def __init__(self, registry: ReincarnationDungeonRegistry | None = None):
        self.registry = registry or REGISTRY

    def is_dungeon_unlocked(self, player: Any, dungeon_id: str) -> bool:
        """ダンジョンがアンロックされているかチェック"""
        dungeon_data = self.registry.get(dungeon_id)
        if not dungeon_data:
            return False

        # 転生回数条件をチェック
        reinc_count = (
            player
            if isinstance(player, int)
            else getattr(player, "reincarnation_count", 0)
        )
        if reinc_count < dungeon_data.min_reincarnation:
            return False
        if reinc_count > dungeon_data.max_reincarnation:
            return False

        # その他のアンロック条件をチェック（簡易版）
        unlock_condition = dungeon_data.unlock_condition
        for key, value in unlock_condition.items():
            if key == "reincarnation_count" and reinc_count != value:
                return False
            # ここで他の条件も追加可能

        return True

    def get_available_dungeons(self, player: Any) -> list[ReincarnationDungeonData]:
        """利用可能なダンジョンリストを取得"""
        available = []
        for dungeon_data in self.registry.all().values():
            if self.is_dungeon_unlocked(player, dungeon_data.id):
                available.append(dungeon_data)
        return available
