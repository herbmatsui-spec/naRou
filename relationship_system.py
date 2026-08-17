"""
Dynamic NPC Relationship System Module (Steps 60-66)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity


# Step 61: RelationshipTemplateData
@dataclass
class RelationshipTemplateData:
    """関係性テンプレートデータ (Step 61)"""
    id: str
    name: str = ""
    relationship_type: str = "friend"
    decay_rate: float = 0.0
    interaction_effects: List[Dict[str, Any]] = field(default_factory=list)
    benefits_at_levels: Dict[str, str] = field(default_factory=dict)
    memory_triggers: List[str] = field(default_factory=list)


# Step 62, 63: RelationshipRegistry
class RelationshipRegistry:
    """関係性レジストリ (Step 62, 63)"""
    _instance: Optional[RelationshipRegistry] = None

    def __new__(cls) -> RelationshipRegistry:
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

        with open(file_path, "r", encoding="utf-8") as f:
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
                memory_triggers=rdata.get("memory_triggers", [])
            )

    def get(self, template_id: str) -> Optional[RelationshipTemplateData]:
        return self._templates.get(template_id)

    def all_templates(self) -> Dict[str, RelationshipTemplateData]:
        return dict(self._templates)


REGISTRY = RelationshipRegistry()


# Step 64-66: RelationshipManager
class RelationshipManager:
    """キャラクター関係性管理 (Steps 64-66)"""
    def __init__(self, registry: Optional[RelationshipRegistry] = None):
        self.registry = registry or REGISTRY

    def get_relationship_level(self, player: "Entity", npc_id: str) -> int:
        """関係性レベルを算出 (Step 65)"""
        if not player or npc_id not in player.character_relationships:
            return 0
        rel = player.character_relationships[npc_id]
        trust = rel.get("trust", 0)
        if trust >= 50: return 3
        elif trust >= 25: return 2
        elif trust >= 10: return 1
        return 0

    def update_relationship(self, player: "Entity", npc_id: str, action: str = "talk", delta_trust: int = 5, delta_mood: int = 5) -> Tuple[int, int]:
        """関係性を更新 (Step 66)"""
        if npc_id not in player.character_relationships:
            player.character_relationships[npc_id] = {"trust": 0, "mood": 0}

        rel = player.character_relationships[npc_id]
        rel["trust"] = min(100, max(-100, rel["trust"] + delta_trust))
        rel["mood"] = min(100, max(-100, rel["mood"] + delta_mood))
        return (rel["trust"], rel["mood"])

    def get_relationship_benefits(self, player: "Entity", npc_id: str) -> List[str]:
        lvl = self.get_relationship_level(player, npc_id)
        return [f"benefit_level_{lvl}"] if lvl > 0 else []
