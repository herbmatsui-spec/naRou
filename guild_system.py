"""
ギルドシステム
ギルドデータの管理・加入・脱退・ランク昇格・報酬適用
Steps 15-23, 46-48
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from ecs.entity import Entity


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


# 既定の昇格段階 (README: novice → member → veteran → officer → leader の5段階)
DEFAULT_RANK_ORDER: list[str] = ["novice", "member", "veteran", "officer", "leader"]


@dataclass
class GuildRankData:
    """昇格段階データ (T41 案C: data/guild_ranks.yaml)"""

    rank: str
    order: int = 0
    label: str = ""
    contribution: int = 0
    completed_quests: int = 0
    reward_multiplier: float = 1.0
    unlocked_quests: list[str] = field(default_factory=list)


class GuildRankRegistry:
    """昇格段階レジストリ (シングルトン) (T41 案C)"""

    _instance: GuildRankRegistry | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ranks: dict[str, dict[str, GuildRankData]] = {}
            cls._instance._loaded = False
        return cls._instance

    def load(self, path: str = "data/guild_ranks.yaml") -> None:
        """YAMLから昇格段階定義をロード (T41 案C)"""
        p = Path(path)
        if not p.exists():
            logger.warning("昇格段階定義が見つかりません: %s", path)
            self._loaded = True
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for gid, g_dict in (data.get("guild_ranks", {}) or {}).items():
                rank_map: dict[str, GuildRankData] = {}
                for r_name, r in (g_dict.get("ranks", {}) or {}).items():
                    rank_map[r_name] = GuildRankData(
                        rank=r_name,
                        order=int(r.get("order", 0)),
                        label=str(r.get("label", "")),
                        contribution=int(r.get("contribution", 0)),
                        completed_quests=int(r.get("completed_quests", 0)),
                        reward_multiplier=float(r.get("reward_multiplier", 1.0)),
                        unlocked_quests=list(r.get("unlocked_quests") or []),
                    )
                self._ranks[gid] = rank_map
            logger.info("Loaded guild ranks for: %s", list(self._ranks.keys()))
        except Exception:
            logger.exception("昇格段階定義のロードに失敗: %s", path)
        self._loaded = True

    def get(self, guild_id: str) -> dict[str, GuildRankData]:
        """ギルドIDごとの昇格段階マップを取得"""
        return self._ranks.get(guild_id, {})

    def all(self) -> dict[str, dict[str, GuildRankData]]:
        """すべての昇格段階定義を返す"""
        return self._ranks


RANK_REGISTRY = GuildRankRegistry()


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
                # TODO: handle exception properly
                logger.exception("Unhandled exception")
                pass

        p_rewards = Path(rewards_path)
        if p_rewards.exists():
            try:
                with open(rewards_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                self._rewards = data.get("guild_rewards", {})
            except Exception:
                logger.exception("Unhandled exception")
                # TODO: handle exception properly
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
    """ギルド管理マネージャー (Steps 19-23, 46-48, T41 案C)"""

    def __init__(
        self,
        registry: GuildRegistry | None = None,
        rank_registry: GuildRankRegistry | None = None,
    ):
        self.registry = registry or REGISTRY
        self.rank_registry = rank_registry or RANK_REGISTRY

    def can_join_guild(self, player: Entity, guild_id: str) -> bool:
        """ギルド加入可否チェック (Step 20)"""
        if getattr(player, "guild_id", None) is not None:
            return False
        guild = self.registry.get(guild_id)
        if not guild:
            return False
        return not self.get_guild_members_count(guild_id) >= guild.max_members

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
        """貢献度に応じた昇格可能ランクをチェック (Step 47)

        貢献度のみでの簡易判定 (段階の飛び越しを許容するレガシーAPI)。
        昇格フロー本体は get_promotable_rank / process_promotion を使用する。
        """
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

    # === 昇格フロー (T41 案C) ===
    def get_rank_order(self, player: Entity) -> list[str]:
        """所属ギルドの昇格段階順序を返す (未定義ギルドは既定の5段階)"""
        gid = getattr(player, "guild_id", None)
        rank_map = self.rank_registry.get(gid) if gid else {}
        if rank_map:
            return sorted(rank_map, key=lambda r: rank_map[r].order)
        return list(DEFAULT_RANK_ORDER)

    def get_rank_data(self, player: Entity, rank_name: str) -> GuildRankData | None:
        """指定段階の昇格データを取得 (未定義時は None)"""
        gid = getattr(player, "guild_id", None)
        if not gid:
            return None
        return self.rank_registry.get(gid).get(rank_name)

    def get_next_rank(self, player: Entity) -> str | None:
        """現在ランクの1つ上の段階を返す (最上位段階なら None)"""
        order = self.get_rank_order(player)
        current = getattr(player, "guild_rank", "none")
        cur_idx = order.index(current) if current in order else -1
        if cur_idx + 1 < len(order):
            return order[cur_idx + 1]
        return None

    def _contribution_requirement(self, player: Entity, rank_name: str) -> int:
        """昇格に必要な貢献度 (guilds.yaml の既存定義を優先し、未定義時は guild_ranks.yaml)"""
        guild = self.get_guild_info(player)
        if guild and rank_name in guild.rank_requirements:
            return int(guild.rank_requirements[rank_name])
        rank_data = self.get_rank_data(player, rank_name)
        if rank_data is not None:
            return rank_data.contribution
        return 0

    def meets_promotion_requirements(self, player: Entity, rank_name: str) -> bool:
        """指定段階の昇格条件 (貢献度+ギルドクエスト達成数) を満たすか判定 (T41 案C)"""
        if getattr(player, "guild_contribution", 0) < self._contribution_requirement(
            player, rank_name
        ):
            return False
        rank_data = self.get_rank_data(player, rank_name)
        required_quests = rank_data.completed_quests if rank_data is not None else 0
        return getattr(player, "guild_completed_quests", 0) >= required_quests

    def get_promotable_rank(self, player: Entity) -> str | None:
        """昇格条件を満たす次の段階を返す (T41 案C)

        段階の飛び越しは認めない (novice から officer への直接昇格は不可)。
        現在の1つ上の段階のみを判定し、条件未達なら None を返す。
        """
        next_rank = self.get_next_rank(player)
        if next_rank is None:
            return None
        if self.meets_promotion_requirements(player, next_rank):
            return next_rank
        return None

    def process_promotion(self, player: Entity, engine: Any | None = None) -> str | None:
        """昇格検知からイベント・特典反映までの一連フローを実行 (T41 案C)

        昇格条件を満たしていれば1段階昇格し、apply_rank_rewards で特典を適用した
        上で昇格イベント (ログ+FloatingText+SE) を発行する。条件未達なら
        何もせず None を返す。engine が渡らない場合 (テスト等) は演出を省略する。
        """
        new_rank = self.get_promotable_rank(player)
        if new_rank is None:
            return None
        self.apply_rank_rewards(player, new_rank)
        self._emit_promotion_event(player, new_rank, engine)
        return new_rank

    def get_reward_multiplier(self, player: Entity) -> float:
        """現在ランクの報酬倍率を返す (未所属・未定義ランクは 1.0)"""
        current = getattr(player, "guild_rank", "none")
        rank_data = self.get_rank_data(player, current)
        if rank_data is not None:
            return rank_data.reward_multiplier
        return 1.0

    def get_unlocked_quest_ids(self, player: Entity) -> list[str]:
        """現在ランクまでに解放された専用クエストID一覧 (累積) を返す"""
        order = self.get_rank_order(player)
        current = getattr(player, "guild_rank", "none")
        cur_idx = order.index(current) if current in order else -1
        unlocked: list[str] = []
        for r_name in order[: cur_idx + 1]:
            rank_data = self.get_rank_data(player, r_name)
            if rank_data is None:
                continue
            for qid in rank_data.unlocked_quests:
                if qid not in unlocked:
                    unlocked.append(qid)
        return unlocked

    def is_rank_at_or_above(self, player: Entity, rank_name: str) -> bool:
        """現在ランクが指定段階以上か判定 (専用クエストの解放判定に使用)"""
        order = self.get_rank_order(player)
        current = getattr(player, "guild_rank", "none")
        if rank_name not in order or current not in order:
            return False
        return order.index(current) >= order.index(rank_name)

    def _emit_promotion_event(self, player: Entity, new_rank: str, engine: Any | None) -> None:
        """昇格イベントを発行する (ログ+FloatingText+SE)

        engine が演出手段を持たない場合 (テスト用のモックなど) は黙って省略する。
        """
        if engine is None:
            return
        guild = self.get_guild_info(player)
        rank_data = self.get_rank_data(player, new_rank)
        label = (rank_data.label if rank_data is not None else "") or new_rank
        guild_name = guild.name if guild is not None else ""
        message = (
            f"★【{guild_name}】ランクが【{label}】に昇格した！"
            f" (報酬倍率×{self.get_reward_multiplier(player):.2f})"
        )
        quest_names = self._resolve_unlocked_quest_names(player)
        if quest_names:
            message += f" 専用クエスト解放: {'、'.join(quest_names)}"

        log_func = getattr(engine, "log", None)
        if callable(log_func):
            log_func(message, (255, 215, 0))

        fx_manager = getattr(engine, "fx_manager", None)
        if fx_manager is not None and hasattr(fx_manager, "add_floating_text"):
            fx_manager.add_floating_text(
                f"昇格: {label}",
                getattr(player, "x", 0.0),
                getattr(player, "y", 0.0) - 1.5,
                (255, 215, 0),
            )

        try:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
        except Exception:
            logger.debug("昇格SEの再生に失敗", exc_info=True)

    def _resolve_unlocked_quest_names(self, player: Entity) -> list[str]:
        """現在ランクで新たに解放された専用クエスト名を解決する (未ロード時は空)"""
        current = getattr(player, "guild_rank", "none")
        rank_data = self.get_rank_data(player, current)
        if rank_data is None or not rank_data.unlocked_quests:
            return []
        try:
            from guild_quest_system import GuildQuestRegistry

            quest_registry = GuildQuestRegistry()
        except Exception:
            return []
        names: list[str] = []
        for qid in rank_data.unlocked_quests:
            quest = quest_registry.get_quest_by_id(qid)
            names.append(quest.name if quest is not None else qid)
        return names

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
                        hasattr(player, "_base_attributes") and player._base_attributes is not None
                    ) and hasattr(player._base_attributes, attr):
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
