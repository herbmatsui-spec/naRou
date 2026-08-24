"""Quest generation registry (Steps 15-18)."""
from __future__ import annotations

import logging
from typing import Any

from typing_extensions import Self

from .models import (
    DifficultyTier,
    NPCQuestTheme,
    QuestArchetype,
    RewardTable,
    StageSetting,
)

logger = logging.getLogger(__name__)


# Step 15, 16: QuestGenerationRegistry (シングルトン)
class QuestGenerationRegistry:
    """クエスト生成設定レジストリ (Step 15, 16)"""

    _instance: QuestGenerationRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._archetypes: dict[str, QuestArchetype] = {}
            cls._difficulties: dict[str, DifficultyTier] = {}
            cls._rewards: dict[str, RewardTable] = {}
            cls._settings: dict[str, StageSetting] = {}
            cls._npc_themes: dict[str, NPCQuestTheme] = {}
            cls._board_config: dict[str, Any] = {}
            cls._display_names: dict[str, dict[str, str]] = {}
            cls._chain_config: dict[str, Any] = {}
            cls._loaded = False
        return cls._instance

    # Step 17: load()
    def load(self, file_path: str = "data/procedural_scenarios.yaml") -> None:
        """YAML(procedural_scenarios.yaml) から quest_generation を読み込む (Step 17)"""
        import os

        import yaml

        # Reset all data
        self._archetypes = {}
        self._difficulties = {}
        self._rewards = {}
        self._settings = {}
        self._npc_themes = {}
        self._board_config = {}
        self._display_names = {}
        self._chain_config = {}
        self._pet_quest_templates = {}

        loaded = False
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "quest_generation" in data:
                    self._build(data.get("quest_generation", {}))
                    loaded = True
            except Exception as e:
                logger.warning("Failed to load %s: %s", file_path, e)

        if not loaded:
            self._load_fallback()

        self._loaded = True

    def _build(self, qg: dict[str, Any]) -> None:
        for aid, a in (qg.get("archetypes") or {}).items():
            self._archetypes[aid] = QuestArchetype(
                id=aid,
                name=a.get("name", aid),
                objective_type=a.get("objective_type", "kill"),
                title_template=a.get("title_template", "{setting}のクエスト"),
                desc_template=a.get("desc_template", "{setting}で任務を遂行せよ。"),
                reward_weight=float(a.get("reward_weight", 1.0)),
                base_complexity=int(a.get("base_complexity", 1)),
            )
        for did, d in (qg.get("difficulty_tiers") or {}).items():
            self._difficulties[did] = DifficultyTier(
                id=did,
                name=d.get("name", did),
                level_range=d.get("level_range", [1, 5]),
                enemy_multiplier=float(d.get("enemy_multiplier", 1.0)),
                objective_complexity=float(d.get("objective_complexity", 1.0)),
                recommended_power=int(d.get("recommended_power", 10)),
            )
        for rid, r in (qg.get("reward_tables") or {}).items():
            self._rewards[rid] = RewardTable(
                id=rid,
                name=r.get("name", rid),
                gold_range=r.get("gold_range", [20, 80]),
                exp_range=r.get("exp_range", [10, 40]),
                item_pool=r.get("item_pool", []),
                bonus=r.get("bonus", {}),
            )
        for sid, s in (qg.get("stage_settings") or {}).items():
            self._settings[sid] = StageSetting(
                id=sid,
                name=s.get("name", sid),
                flavor=s.get("flavor", ""),
                enemy_pool=s.get("enemy_pool", []),
                hazard=s.get("hazard", ""),
                depth_modifier=float(s.get("depth_modifier", 1.0)),
                environmental_modifier=float(s.get("environmental_modifier", 1.0)),
            )
        for nid, n in (qg.get("npc_quest_themes") or {}).items():
            self._npc_themes[nid] = NPCQuestTheme(
                npc_type=n.get("npc_type", nid),
                quest_pool=n.get("quest_pool", []),
                relationship_gate=int(n.get("relationship_gate", 1)),
                flavor=n.get("flavor", "{npc}「頼んだよ。」"),
            )
        self._board_config = qg.get("request_board", {}) or {}
        self._display_names = qg.get("display_names", {}) or {}
        self._chain_config = qg.get("chain_config", {}) or {}

    def _load_fallback(self) -> None:
        self._archetypes = {
            "slay": QuestArchetype("slay", "討伐", "kill", "{setting}の討伐", "", 1.0, 1),
        }
        self._difficulties = {
            "normal": DifficultyTier("normal", "中", [15, 35], 2.6, 1.6, 120),
        }
        self._rewards = {
            "gold": RewardTable("gold", "金", [250, 800], [120, 400], ["gem"], {"fame": 8}),
        }
        self._settings = {
            "forest": StageSetting("forest", "森", "深い森", ["wolf", "goblin"], "毒", 1.0, 1.0),
        }
        self._npc_themes = {
            "villager": NPCQuestTheme("villager", ["rescue"], 1, "{npc}「お願い…」"),
        }
        self._board_config = {"max_active": 8, "type_weights": {"slay": 3}}
        self._display_names = {}
        self._chain_config = {}
        self._pet_quest_templates = {}

    # Step 18: 取得メソッド群
    def get_display_name(self, category: str, id: str) -> str:
        """英語IDを日本語表示名へ変換（未定義なら元のIDを返す・フォールバック）(Step 10)"""
        return self._display_names.get(category, {}).get(id, id)

    def get_archetype(self, aid: str) -> QuestArchetype | None:
        return self._archetypes.get(aid)

    def get_difficulty(self, did: str) -> DifficultyTier | None:
        return self._difficulties.get(did)

    def get_reward(self, rid: str) -> RewardTable | None:
        return self._rewards.get(rid)

    def get_setting(self, sid: str) -> StageSetting | None:
        return self._settings.get(sid)

    def get_npc_theme(self, npc_type: str) -> NPCQuestTheme | None:
        return self._npc_themes.get(npc_type)

    def board_config(self) -> dict[str, Any]:
        return self._board_config

    def chain_config(self) -> dict[str, Any]:
        """連鎖クエスト設定 (Step 16)"""
        return self._chain_config

    def display_names(self) -> dict[str, dict[str, str]]:
        return self._display_names

    def all_archetypes(self) -> dict[str, QuestArchetype]:
        return dict(self._archetypes)

    def all_difficulties(self) -> dict[str, DifficultyTier]:
        return dict(self._difficulties)

    def all_rewards(self) -> dict[str, RewardTable]:
        return dict(self._rewards)

    def all_settings(self) -> dict[str, StageSetting]:
        return dict(self._settings)

    def all_npc_themes(self) -> dict[str, NPCQuestTheme]:
        return dict(self._npc_themes)

    def difficulty_order(self) -> list[str]:
        """ティアを難易度順（低→高）に並べたIDリスト"""
        tiers = list(self._difficulties.values())
        tiers.sort(key=lambda t: t.recommended_power)
        return [t.id for t in tiers]


REGISTRY = QuestGenerationRegistry()
