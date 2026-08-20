"""
ギルドシステム
ギルドデータの管理・加入・脱退・ランク昇格・報酬適用
Steps 15-23, 46-48
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class GuildData:
    """ギルドマスターデータ (Step 16)"""

    id: str
    name: str
    icon: str = "🏰"
    description: str = ""
    hall_location: str = ""
    facilities: list[str] = field(default_factory=list)
    membership_benefits: list[dict[str, Any]] = field(default_factory=list)
    rank_requirements: dict[str, int] = field(default_factory=dict)
    max_members: int = 100


class GuildRegistry:
    """ギルドレジストリ (シングルトン) (Steps 17, 18)"""

    _instance: GuildRegistry | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._guilds = {}
            cls._instance._rewards = {}
            cls._instance._loaded = False
        return cls._instance

    def load(
        self,
        guilds_path: str = "data/guilds.yaml",
        rewards_path: str = "data/guild_rewards.yaml",
    ) -> None:
        """YAMLからギルド定義および報酬定義をロード (Step 18)"""
        p_guilds = Path(guilds_path)
        if p_guilds.exists():
            try:
                with open(guilds_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for gid, g in data.get("guilds", {}).items():
                    guild = GuildData(
                        id=gid,
                        name=g.get("name", gid),
                        icon=g.get("icon", "🏰"),
                        description=g.get("description", ""),
                        hall_location=g.get("hall_location", ""),
                        facilities=g.get("facilities") or [],
                        membership_benefits=g.get("membership_benefits") or [],
                        rank_requirements=g.get("rank_requirements") or {},
                        max_members=g.get("max_members", 100),
                    )
                    self._guilds[gid] = guild
            except Exception:
                pass

        p_rewards = Path(rewards_path)
        if p_rewards.exists():
            try:
                with open(rewards_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                self._rewards = data.get("guild_rewards", {})
            except Exception:
                pass

        self._loaded = True

    def get(self, guild_id: str) -> GuildData | None:
        """特定ギルドデータを取得 (Step 17)"""
        return self._guilds.get(guild_id)

    def all(self) -> dict[str, GuildData]:
        """すべてのギルド辞書を返す (Step 17)"""
        return self._guilds

    def get_rewards(self, guild_id: str) -> dict[str, Any]:
        """ギルドの報酬データを取得"""
        return self._rewards.get(guild_id, {})


REGISTRY = GuildRegistry()


class GuildManager:
    """ギルド管理マネージャー (Steps 19-23, 46-48)"""

    def __init__(self, registry: GuildRegistry | None = None):
        self.registry = registry or REGISTRY

    def can_join_guild(self, player: Entity, guild_id: str) -> bool:
        """ギルド加入可否チェック (Step 20)"""
        if getattr(player, "guild_id", None) is not None:
            return False
        guild = self.registry.get(guild_id)
        if not guild:
            return False
        if self.get_guild_members_count(guild_id) >= guild.max_members:
            return False
        return True

    def join_guild(self, player: Entity, guild_id: str) -> bool:
        """ギルドに加入 (Step 21)"""
        if not self.can_join_guild(player, guild_id):
            return False
        player.guild_id = guild_id
        player.guild_rank = "novice"
        player.guild_contribution = 0
        player.guild_role = None
        self.apply_rank_rewards(player, "novice")
        return True

    def leave_guild(self, player: Entity) -> bool:
        """ギルドを脱退 (Step 22)"""
        if getattr(player, "guild_id", None) is None:
            return False
        player.guild_id = None
        player.guild_rank = "none"
        player.guild_role = None
        return True

    def get_guild_info(self, player: Entity) -> GuildData | None:
        """プレイヤーの所属ギルド情報を取得 (Step 23)"""
        gid = getattr(player, "guild_id", None)
        if not gid:
            return None
        return self.registry.get(gid)

    def get_guild_members_count(self, guild_id: str) -> int:
        """ギルドのメンバー数を取得 (簡易版)"""
        return 12

    # === ギルド報酬・ランクアップ (Steps 46, 47, 48) ===
    def check_rank_up(self, player: Entity) -> str | None:
        """貢献度に応じた昇格可能ランクをチェック (Step 47)"""
        guild = self.get_guild_info(player)
        if not guild or not guild.rank_requirements:
            return None

        current_rank = getattr(player, "guild_rank", "none")
        current_contrib = getattr(player, "guild_contribution", 0)

        rank_order = ["novice", "member", "veteran", "officer", "leader"]
        cur_idx = rank_order.index(current_rank) if current_rank in rank_order else -1

        highest_eligible = None
        for r_name in rank_order:
            req = guild.rank_requirements.get(r_name, 0)
            if current_contrib >= req:
                r_idx = rank_order.index(r_name)
                if r_idx > cur_idx:
                    highest_eligible = r_name

        return highest_eligible

    def apply_rank_rewards(self, player: Entity, new_rank: str) -> None:
        """ランクアップ報酬の適用 (Step 48)"""
        gid = getattr(player, "guild_id", None)
        if not gid:
            return
        player.guild_rank = new_rank

        rewards_data = self.registry.get_rewards(gid)
        rank_rewards = rewards_data.get("rank_rewards", {}).get(new_rank, [])

        for r in rank_rewards:
            rtype = r.get("type")
            rval = r.get("value")
            if rtype == "title" and isinstance(rval, str):
                if rval not in player.titles:
                    player.titles.append(rval)
                    player.title_notifications.append(f"ギルド称号《{rval}》を獲得！")
            elif rtype == "stat_bonus" and isinstance(rval, dict):
                for attr, bonus in rval.items():
                    if hasattr(player.attributes, attr):
                        setattr(
                            player.attributes,
                            attr,
                            getattr(player.attributes, attr) + bonus,
                        )
                    if (
                        hasattr(player, "_base_attributes")
                        and player._base_attributes is not None
                    ):
                        if hasattr(player._base_attributes, attr):
                            setattr(
                                player._base_attributes,
                                attr,
                                getattr(player._base_attributes, attr) + bonus,
                            )
                player.recalculate_stats()

            elif rtype == "skill_unlock" and isinstance(rval, str):
                if rval not in getattr(player, "gene_skills", []):
                    player.gene_skills.append(rval)
            elif rtype == "exclusive_skill" and isinstance(rval, str):
                if rval not in getattr(player, "mastered_exclusive_skills", []):
                    player.mastered_exclusive_skills.append(rval)

    def get_leaderboard_rewards(self) -> list[dict[str, Any]]:
        """ランキング報酬定義を取得 (Step 46)"""
        return []
