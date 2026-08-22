"""
ギルドクエストシステム
ギルドクエストデータの管理・進捗更新・達成判定・報酬付与
Steps 31-39
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class GuildQuestData:
    """ギルドクエストデータ (Step 32)"""

    id: str
    name: str
    description: str = ""
    requirements: dict[str, Any] = field(default_factory=dict)
    reward: dict[str, Any] = field(default_factory=dict)
    quest_type: str = "daily"  # daily / weekly


class GuildQuestRegistry:
    """ギルドクエストレジストリ (シングルトン) (Steps 33, 34)"""

    _instance: GuildQuestRegistry | None = None
    _quests: dict[str, dict[str, list[GuildQuestData]]] = {}  # guild_id -> {quest_type -> [quests]}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._quests = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/guild_quests.yaml") -> None:
        """YAMLからギルドクエスト定義をロード (Step 34)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            guild_quests_data = data.get("guild_quests", {})
            for guild_id, types_dict in guild_quests_data.items():
                self._quests[guild_id] = {}
                for q_type, q_list in types_dict.items():
                    quest_objs = []
                    for q in q_list:
                        quest_objs.append(
                            GuildQuestData(
                                id=q.get("id", ""),
                                name=q.get("name", ""),
                                description=q.get("description", ""),
                                requirements=q.get("requirements") or {},
                                reward=q.get("reward") or {},
                                quest_type=q_type,
                            )
                        )
                    self._quests[guild_id][q_type] = quest_objs
            self._loaded = True
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            self._loaded = True

    def get(self, guild_id: str, quest_type: str | None = None) -> list[GuildQuestData]:
        """ギルドIDとタイプに応じたクエストリストを取得 (Step 33)"""
        g_data = self._quests.get(guild_id, {})
        if quest_type:
            return g_data.get(quest_type, [])
        all_q = []
        for q_list in g_data.values():
            all_q.extend(q_list)
        return all_q

    def get_quest_by_id(self, quest_id: str) -> GuildQuestData | None:
        """IDから直接クエストデータを検索"""
        for g_dict in self._quests.values():
            for q_list in g_dict.values():
                for q in q_list:
                    if q.id == quest_id:
                        return q
        return None

    def all(self) -> dict[str, dict[str, list[GuildQuestData]]]:
        """すべてのギルドクエストを返す (Step 33)"""
        return self._quests


REGISTRY = GuildQuestRegistry()


class GuildQuestManager:
    """ギルドクエスト管理マネージャー (Steps 35-39)"""

    def __init__(self, registry: GuildQuestRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_available_quests(
        self, player: Entity, quest_type: str = "daily"
    ) -> list[GuildQuestData]:
        """プレイヤーが受領可能なギルドクエスト一覧を取得 (Step 36)"""
        gid = getattr(player, "guild_id", None)
        if not gid:
            return []
        return self.registry.get(gid, quest_type)

    def update_quest_progress(self, player: Entity, quest_id: str, amount: int = 1) -> bool:
        """ギルドクエスト進捗を加算 (Step 37)"""
        if not hasattr(player, "guild_quest_progress"):
            player.guild_quest_progress = {}

        cur = player.guild_quest_progress.get(quest_id, 0)
        new_val = min(100, cur + amount)
        player.guild_quest_progress[quest_id] = new_val
        return new_val >= 100

    def can_complete_quest(self, player: Entity, quest_id: str) -> bool:
        """クエスト達成可否判定 (Step 38)"""
        if not hasattr(player, "guild_quest_progress"):
            return False
        return player.guild_quest_progress.get(quest_id, 0) >= 100

    def complete_quest(self, player: Entity, quest_id: str) -> tuple[bool, str, dict[str, Any]]:
        """ギルドクエスト完了と報酬付与 (Step 39)"""
        if not self.can_complete_quest(player, quest_id):
            return False, "クエスト条件を達成していません。", {}

        quest = self.registry.get_quest_by_id(quest_id)
        reward = quest.reward if quest else {}

        contrib = reward.get("contribution", 30)
        gold = reward.get("gold", 50)
        reward.get("item")

        player.guild_contribution = getattr(player, "guild_contribution", 0) + contrib
        player.gold = getattr(player, "gold", 0) + gold

        # 進捗をリセット
        player.guild_quest_progress[quest_id] = 0

        msg = f"★ギルドクエスト【{quest.name if quest else quest_id}】達成！ 貢献度+{contrib}, 金貨+{gold}G 獲得！"
        return True, msg, reward
