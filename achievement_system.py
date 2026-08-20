"""
Achievement and Trophy System Module (Steps 18-24, 35, 40, 44, 47, 50, 54, 58, 62, 64, 69)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity


# Step 19: AchievementData クラス定義
@dataclass
class AchievementData:
    """実績データクラス (Step 19)"""

    id: str
    name: str
    description: str
    icon: str = "🏆"
    reward_title: str | None = None
    reward_gold: int = 0
    reward_item: str | None = None
    reward_skill_points: int = 0
    hidden: bool = False
    prerequisites: list[str] = field(default_factory=list)
    trigger_condition: dict[str, Any] = field(default_factory=dict)
    auto_equip_title: bool = False
    status_bonus: dict[str, int] = field(default_factory=dict)
    time_limit: int | None = None
    available_dates: list[str] = field(default_factory=list)
    collection_type: str | None = None
    target_count: int = 0
    social_based: bool = False
    meta_progression_based: bool = False
    requirement: dict[str, Any] = field(default_factory=dict)


# Step 20, 21: AchievementRegistry シングルトン
class AchievementRegistry:
    """実績マスタデータ管理 (Step 20, 21)"""

    _instance: AchievementRegistry | None = None

    def __new__(cls) -> AchievementRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._achievements = {}
        return cls._instance

    def load(self, file_path: str = "data/achievements.yaml") -> None:
        """YAMLから全実績データを読み込む (Step 21)"""
        self._achievements = {}
        if not os.path.exists(file_path):
            # デフォルト実績作成
            self._achievements["first_blood"] = AchievementData(
                id="first_blood",
                name="最初の血",
                description="初めてモンスターを討伐する。",
                icon="⚔️",
                reward_gold=100,
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        ach_dict = raw.get("achievements", {})
        for ach_id, data in ach_dict.items():
            self._achievements[ach_id] = AchievementData(
                id=ach_id,
                name=data.get("name", ach_id),
                description=data.get("description", ""),
                icon=data.get("icon", "🏆"),
                reward_title=data.get("reward_title"),
                reward_gold=data.get("reward_gold", 0),
                reward_item=data.get("reward_item"),
                reward_skill_points=data.get("reward_skill_points", 0),
                hidden=data.get("hidden", False),
                prerequisites=data.get("prerequisites", []),
                trigger_condition=data.get("condition", {}),
                auto_equip_title=data.get("auto_equip_title", False),
                status_bonus=data.get("status_bonus", {}),
                time_limit=data.get("time_limit"),
                available_dates=data.get("available_dates", []),
                collection_type=data.get("collection_type"),
                target_count=data.get("target_count", 0),
                social_based=data.get("social_based", False),
                meta_progression_based=data.get("meta_progression_based", False),
                requirement=data.get("requirement", {}),
            )

    def get(self, achievement_id: str) -> AchievementData | None:
        return self._achievements.get(achievement_id)

    def all(self) -> dict[str, AchievementData]:
        return dict(self._achievements)


REGISTRY = AchievementRegistry()


# Step 22-24, 35, 40, 44, 47, 50, 54, 58, 62, 64, 69: AchievementManager
class AchievementManager:
    """実績進行管理・判定・報酬付与 (Step 22-24)"""

    def __init__(self, registry: AchievementRegistry | None = None):
        self.registry = registry or REGISTRY

    def check_achievement(
        self, player: Entity, ach_id: str, engine: Any | None = None
    ) -> bool:
        """個別実績の達成条件チェック (Steps 23, 35, 40, 44, 47, 50, 54, 58, 62, 64, 69)"""
        if ach_id in player.achievements:
            return False

        data = self.registry.get(ach_id)
        if not data:
            return False

        cond = data.trigger_condition
        ctype = cond.get("type", "")

        # 1. 討伐数 (Step 2, 23)
        if ctype == "kill_count":
            target = cond.get("target", 1)
            tot_kills = (
                sum(player.kill_counts.values())
                if hasattr(player, "kill_counts")
                else 0
            )
            return tot_kills >= target

        # 2. モンスター種族討伐数 (Step 3)
        elif ctype == "monster_type_kill":
            mkey = cond.get("monster_key", "")
            target = cond.get("target", 10)
            kcount = player.monster_killed_types.get(mkey, 0)
            return kcount >= target

        # 3. ダンジョン探検家 (Step 32, 35)
        elif ctype == "dungeon_floors":
            target = cond.get("target", 10)
            return (
                len(player.dungeon_floors_visited) >= target
                or getattr(player, "max_dungeon_depth", 0) >= target
            )

        # 4. スピードランナー (Step 37, 40)
        elif ctype == "speedrun":
            limit = cond.get("time_limit_seconds", 3600)
            return (
                player.play_time_seconds <= limit
                and getattr(player, "max_dungeon_depth", 0) >= 5
            )

        # 5. 祭り参加者 (Step 41, 44)
        elif ctype == "festival_date":
            today_str = player.last_festival_check or datetime.now().strftime("%m-%d")
            return today_str in data.available_dates

        # 6. モンスター収集家 (Step 45, 47)
        elif ctype == "unique_monsters_killed":
            target = cond.get("target", 5)
            return len(player.monster_killed_types) >= target

        # 7. アイテム収集家 (Step 48, 50)
        elif ctype == "unique_items_obtained":
            target = cond.get("target", 5)
            return len(player.unique_items_obtained) >= target

        # 8. 週間チャンピオン (Step 51, 54)
        elif ctype == "weekly_time":
            target = cond.get("target", 1800)
            return player.weekly_play_time >= target

        # 9. 友達助っ人 (Step 55, 58)
        elif ctype == "friend_helps":
            target = cond.get("target", 5)
            return player.friend_helps >= target

        # 10. 転生英雄 (Step 59, 62)
        elif ctype == "reincarnation":
            req_reinc = cond.get("reincarnation_count", 5)
            req_lvl = cond.get("total_level_earned", 1000)
            return (
                player.reincarnation_count >= req_reinc
                and player.total_level_earned >= req_lvl
            )

        # 11. メタマスター (Step 63, 64)
        elif ctype == "meta_progression_all":
            # 3つ以上のメタ進行マイルストーンを記録
            return len(player.meta_progression) >= 3

        # 12. 秘密の牛レベル (Step 66, 69)
        elif ctype == "special_combo":
            req_items = cond.get("required_items", [])
            return all(item in player.special_items_combo for item in req_items)

        return False

    def grant_achievement(
        self, player: Entity, ach_id: str, engine: Any | None = None
    ) -> bool:
        """実績付与および報酬付与 (Step 24)"""
        if ach_id in player.achievements:
            return False

        data = self.registry.get(ach_id)
        if not data:
            return False

        # 実績リスト追加
        player.achievements.append(ach_id)

        # 通知リスト追加
        notif_msg = f"🏆【実績解除】{data.name} ({data.description})"
        player.achievement_notifications.append(notif_msg)

        # 報酬ゴールド付与
        if data.reward_gold > 0:
            if hasattr(player, "gold"):
                player.gold += data.reward_gold
            if engine and hasattr(engine, "survival"):
                engine.survival.gold += data.reward_gold

        # 報酬スキルポイント付与
        if data.reward_skill_points > 0:
            player.skill_points += data.reward_skill_points
            player.total_skill_points_earned += data.reward_skill_points

        # 報酬称号付与
        if data.reward_title:
            if not hasattr(player, "titles"):
                player.titles = []
            if data.reward_title not in player.titles:
                player.titles.append(data.reward_title)
            if data.auto_equip_title:
                player.equipped_title = data.reward_title

        # ステータスボーナス
        if data.status_bonus:
            for attr_name, b_val in data.status_bonus.items():
                if hasattr(player.attributes, attr_name):
                    setattr(
                        player.attributes,
                        attr_name,
                        getattr(player.attributes, attr_name) + b_val,
                    )

        # SE再生 & ログ
        if engine:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
            engine.log(f"★実績解除: 【{data.name}】を獲得！", (255, 215, 0))

        return True

    def check_all_achievements(
        self, player: Entity, engine: Any | None = None
    ) -> list[str]:
        """全未達成実績を一括チェックして付与"""
        granted = []
        for ach_id in self.registry.all().keys():
            if ach_id not in player.achievements:
                if self.check_achievement(player, ach_id, engine):
                    if self.grant_achievement(player, ach_id, engine):
                        granted.append(ach_id)
        return granted
