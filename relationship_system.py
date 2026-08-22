"""
Dynamic NPC Relationship System Module (Steps 60-66)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from typing_extensions import Self

if TYPE_CHECKING:
    from entity import Entity

# Phase 2 連携：遅延インポート用
try:
    from npc_memory_system import GLOBAL_MEMORY_REGISTRY, MemoryImportance, MemoryType

    _HAS_NPC_MEMORY = True
except ImportError:
    _HAS_NPC_MEMORY = False


# Step 61: RelationshipTemplateData
@dataclass
class RelationshipTemplateData:
    """関係性テンプレートデータ (Step 61)"""

    id: str
    name: str = ""
    relationship_type: str = "friend"
    decay_rate: float = 0.0
    interaction_effects: list[dict[str, Any]] = field(default_factory=list)
    benefits_at_levels: dict[str, str] = field(default_factory=dict)
    memory_triggers: list[str] = field(default_factory=list)


# Step 62, 63: RelationshipRegistry
class RelationshipRegistry:
    """関係性レジストリ (Step 62, 63)"""

    _instance: RelationshipRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._templates = {}
        return cls._instance

    def load(self, file_path: str = "data/character_relations.yaml") -> None:
        """YAMLから関係性テンプレートを読み込む (Step 63)"""
        self._templates = {}
        if not os.path.exists(file_path):
            self._templates["saved_villager"] = RelationshipTemplateData(
                id="saved_villager", name="助けた村人"
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        r_dict = raw.get("relationship_templates", {})
        for rid, rdata in r_dict.items():
            self._templates[rid] = RelationshipTemplateData(
                id=rid,
                name=rdata.get("name", rid),
                relationship_type=rdata.get("relationship_type", "friend"),
                decay_rate=float(rdata.get("decay_rate", 0.0)),
                interaction_effects=rdata.get("interaction_effects", []),
                benefits_at_levels=rdata.get("benefits_at_levels", {}),
                memory_triggers=rdata.get("memory_triggers", []),
            )

    def get(self, template_id: str) -> RelationshipTemplateData | None:
        return self._templates.get(template_id)

    def all_templates(self) -> dict[str, RelationshipTemplateData]:
        return dict(self._templates)


REGISTRY = RelationshipRegistry()


# Step 64-66: RelationshipManager
class RelationshipManager:
    """キャラクター関係性管理 (Steps 64-66)"""

    def __init__(self, registry: RelationshipRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_relationship_level(self, player: Entity, npc_id: str) -> int:
        """関係性レベルを算出 (Step 65)"""
        if not player or npc_id not in player.character_relationships:
            return 0
        rel = player.character_relationships[npc_id]
        trust = rel.get("trust", 0)
        if trust >= 50:
            return 3
        elif trust >= 25:
            return 2
        elif trust >= 10:
            return 1
        return 0

    def update_relationship(
        self,
        player: Entity,
        npc_id: str,
        action: str = "talk",
        delta_trust: int = 5,
        delta_mood: int = 5,
    ) -> tuple[int, int]:
        """関係性を更新 (Step 66)"""
        if npc_id not in player.character_relationships:
            player.character_relationships[npc_id] = {"trust": 0, "mood": 0}

        rel = player.character_relationships[npc_id]
        rel["trust"] = min(100, max(-100, rel["trust"] + delta_trust))
        rel["mood"] = min(100, max(-100, rel["mood"] + delta_mood))
        return (rel["trust"], rel["mood"])

    def get_relationship_benefits(self, player: Entity, npc_id: str) -> list[str]:
        lvl = self.get_relationship_level(player, npc_id)
        return [f"benefit_level_{lvl}"] if lvl > 0 else []

    # Phase 2 連携メソッド
    def update_relationship_with_memory(
        self,
        player: Entity,
        npc: Entity,
        npc_id: str,
        action: str = "talk",
        delta_trust: int = 5,
        delta_mood: int = 5,
        importance: MemoryImportance | None = None,
    ) -> tuple[int, int]:
        """関係性更新＋NPC 記憶記録（Phase 2 Step 5/6 連携）"""
        trust, mood = self.update_relationship(player, npc_id, action, delta_trust, delta_mood)

        if _HAS_NPC_MEMORY:
            # プレイヤー側の NPC 記憶（クエストシステム連携用）
            mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
            mgr.record_personal_interaction(
                action=action,
                delta_trust=delta_trust,
                delta_mood=delta_mood,
                importance=importance or MemoryImportance.NOTABLE,
            )
        return (trust, mood)

    def get_reputation_for_gate(self, player: Entity, npc_id: str) -> int:
        """ReputationGate 用評判値取得（-100 to 100）"""
        level = self.get_relationship_level(player, npc_id)
        # レベル 0-3 -> -50, -10, 30, 70
        return level * 40 - 50

    def get_all_relationships(self, player: Entity) -> dict[str, dict[str, int]]:
        """全関係性取得（噂伝播・評判ゲート用）"""
        return dict(player.character_relationships)

    def apply_rumor_effect(
        self,
        player: Entity,
        npc_id: str,
        event_type: str,
        delta: int,
        source: str = "rumor",
    ) -> tuple[int, int]:
        """噂伝播による評判変動適用（Phase 2 Step 6 連携）"""
        return self.update_relationship_with_memory(
            player,
            None,
            npc_id,
            action=f"rumor:{event_type}",
            delta_trust=delta,
            delta_mood=delta,
        )
