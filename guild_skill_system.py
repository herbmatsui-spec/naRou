"""
ギルドスキルシステム
ギルドスキルデータの管理・習得可能スキル一覧・スキル効果適用
Steps 68-72
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
class GuildSkillData:
    """ギルドスキルデータ (Step 69)"""

    id: str
    name: str
    description: str = ""
    type: str = "passive"  # active / passive
    cost: int = 0
    cooldown: int = 0
    effects: list[dict[str, Any]] = field(default_factory=list)


class GuildSkillRegistry:
    """ギルドスキルレジストリ (シングルトン) (Steps 70, 71)"""

    _instance: GuildSkillRegistry | None = None
    _skills: dict[str, list[GuildSkillData]] = {}  # guild_id -> [GuildSkillData]
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._skills = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/guild_skills.yaml") -> None:
        """YAMLからギルドスキル定義をロード (Step 71)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            guild_skills_data = data.get("guild_skills", {})
            for guild_id, g_dict in guild_skills_data.items():
                skill_list = []
                for s in g_dict.get("skills", []):
                    skill = GuildSkillData(
                        id=s.get("id", ""),
                        name=s.get("name", ""),
                        description=s.get("description", ""),
                        type=s.get("type", "passive"),
                        cost=s.get("cost", 0),
                        cooldown=s.get("cooldown", 0),
                        effects=s.get("effects") or [],
                    )
                    skill_list.append(skill)
                self._skills[guild_id] = skill_list
            self._loaded = True
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            self._loaded = True

    def get(self, guild_id: str) -> list[GuildSkillData]:
        """ギルドIDごとのスキルリストを取得 (Step 70)"""
        return self._skills.get(guild_id, [])

    def all(self) -> dict[str, list[GuildSkillData]]:
        """すべてのギルドスキルを返す (Step 70)"""
        return self._skills


REGISTRY = GuildSkillRegistry()


class GuildSkillManager:
    """ギルドスキル管理マネージャー (Step 72)"""

    def __init__(self, registry: GuildSkillRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_available_skills(self, guild_id: str) -> list[GuildSkillData]:
        """ギルドが習得可能なスキルリストを取得 (Step 72)"""
        return self.registry.get(guild_id)

    def is_skill_active(self, player: Entity, skill_id: str) -> bool:
        """スキルが現在有効かどうか判定 (Step 72)"""
        gid = getattr(player, "guild_id", None)
        if not gid:
            return False
        skills = self.registry.get(gid)
        return any(s.id == skill_id for s in skills)

    def apply_skill_effects(self, player: Entity, skill_data: GuildSkillData) -> None:
        """スキル効果をプレイヤーに適用 (Step 72)"""
        for eff in skill_data.effects:
            eff_type = eff.get("type")
            eff.get("value")
            if eff_type == "exp_bonus" and hasattr(player, "attributes"):
                # 経験値ボーナス効果フック
                pass
            elif eff_type == "storage_capacity":
                pass
