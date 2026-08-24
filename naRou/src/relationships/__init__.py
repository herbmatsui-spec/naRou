"""
NPC Relationship Simulation Package
多層関係グラフ・ドラマエンジンのメインパッケージ
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .betrayal import BetrayalConflictSystem, BetrayalType, ConflictState
from .branching import (
    BranchingScenarioGenerator,
    GeneratedScenario,
    ScenarioBranch,
    ScenarioTriggerType,
)
from .decay_memory import (
    MemoryFragment,
    MemoryImportance,
    MemorySystem,
    MemoryType,
    RelationshipDecaySystem,
)
from .dialogue import DialogueContext, DialogueGenerationSystem, DialogueMood, GeneratedDialogue
from .dynamics import CumulativeEffect, DelayedEffect, DynamicRelationshipSystem
from .engine import RelationshipManager
from .event_integration import EventToInteractionMapper, GameEventType, RelationshipEventHandler
from .faction import FactionNode, FactionRelation, FactionRelationshipSystem
from .graph import RelationshipGraph
from .mentorship import MentorshipMechanics, MentorshipStage, MentorshipState
from .models import (
    FactionAffiliation,
    InteractionType,
    RelationshipEdge,
    RelationshipLevel,
    RelationshipModifier,
    RelationshipNode,
    RelationshipTemplate,
    RelationshipType,
)
from .persistence import ComprehensiveRelationshipSaveSystem, RelationshipPersistence, SaveFormat
from .personality import CharacterArchetype, PersonalityProfile, PersonalitySystem, PersonalityTrait
from .quest_integration import QuestRelationshipIntegration
from .romance import RomanceEventType, RomanceMechanics, RomanceStage, RomanceState
from .visualization import RelationshipVisualizer, VisualizationFormat
from .worldstate_integration import WorldStateRelationshipIntegration

__all__ = [
    # Betrayal
    "BetrayalConflictSystem",
    "BetrayalType",
    # Branching
    "BranchingScenarioGenerator",
    "CharacterArchetype",
    "ComprehensiveRelationshipSaveSystem",
    "ConflictState",
    "CumulativeEffect",
    "DelayedEffect",
    "DialogueContext",
    # Dialogue
    "DialogueGenerationSystem",
    "DialogueMood",
    "DynamicRelationshipSystem",
    "EventToInteractionMapper",
    "FactionAffiliation",
    "FactionNode",
    "FactionRelation",
    # Faction
    "FactionRelationshipSystem",
    "GameEventType",
    "GeneratedDialogue",
    "GeneratedScenario",
    "InteractionType",
    "MemoryFragment",
    # Memory
    "MemorySystem",
    "MemoryType",
    # Mentorship
    "MentorshipMechanics",
    "MentorshipStage",
    "MentorshipState",
    "PersonalityProfile",
    # Personality
    "PersonalitySystem",
    "PersonalityTrait",
    # Integration
    "QuestRelationshipIntegration",
    "RelationshipDecaySystem",
    "RelationshipEdge",
    # Event
    "RelationshipEventHandler",
    "RelationshipGraph",
    "RelationshipLevel",
    "RelationshipManager",
    "RelationshipModifier",
    "RelationshipNode",
    # Persistence
    "RelationshipPersistence",
    "RelationshipTemplate",
    # Core
    "RelationshipType",
    # Visualization
    "RelationshipVisualizer",
    "RomanceEventType",
    # Romance
    "RomanceMechanics",
    "RomanceStage",
    "RomanceState",
    "SaveFormat",
    "ScenarioBranch",
    "ScenarioTriggerType",
    "VisualizationFormat",
    "WorldStateRelationshipIntegration",
]


class RelationshipSimulationEngine:
    """
    関係シミュレーションエンジン（統合ファサード）
    すべての関係サブシステムを初期化・統合し、一貫したインターフェースを提供
    """

    def __init__(self, data_path: str = "data/character_relations.yaml"):
        # コアマネージャー
        self.manager = RelationshipManager(data_path)

        # サブシステム
        self.dynamics = DynamicRelationshipSystem(self.manager)
        self.event_handler = RelationshipEventHandler(self.manager)
        self.branching = BranchingScenarioGenerator(self.manager)
        self.faction = FactionRelationshipSystem(self.manager)
        self.romance = RomanceMechanics(self.manager)
        self.mentorship = MentorshipMechanics(self.manager)
        self.betrayal = BetrayalConflictSystem(self.manager)
        self.memory = MemorySystem(self.manager)
        self.decay = RelationshipDecaySystem(self.manager, self.memory)
        self.personality = PersonalitySystem(self.manager)
        self.dialogue = DialogueGenerationSystem(self.manager, self.personality)
        self.visualizer = RelationshipVisualizer(self.manager)
        self.quest_integration = QuestRelationshipIntegration(self.manager, self.branching)
        self.world_integration = WorldStateRelationshipIntegration(self.manager)

        # 包括的セーブシステム
        self.save_system = ComprehensiveRelationshipSaveSystem(self.manager)
        self._register_subsystems()

    def _register_subsystems(self) -> None:
        """サブシステムをセーブシステムに登録"""
        self.save_system.register_subsystem("romance_system", self.romance)
        self.save_system.register_subsystem("mentorship_system", self.mentorship)
        self.save_system.register_subsystem("betrayal_system", self.betrayal)
        self.save_system.register_subsystem("memory_system", self.memory)
        self.save_system.register_subsystem("personality_system", self.personality)
        self.save_system.register_subsystem("dialogue_system", self.dialogue)
        self.save_system.register_subsystem("faction_system", self.faction)
        self.save_system.register_subsystem("quest_integration", self.quest_integration)
        self.save_system.register_subsystem("world_integration", self.world_integration)

    def initialize_character(
        self,
        character_id: str,
        name: str,
        archetype: str | None = None,
        personality_traits: dict[str, float] | None = None,
    ) -> RelationshipNode:
        """キャラクターを初期化（パーソナリティ含む）"""
        node = self.manager.initialize_character(character_id, name, personality_traits)

        # アーキタイプに基づくパーソナリティを割り当て
        if archetype:
            from .personality import CharacterArchetype

            try:
                arch = CharacterArchetype(archetype)
                self.personality.assign_personality(character_id, personality_traits, arch)
            except ValueError:
                pass

        return node

    def establish_relationship(
        self,
        source_id: str,
        target_id: str,
        template_id: str,
        source_name: str | None = None,
        target_name: str | None = None,
    ) -> bool:
        """関係を確立"""
        return self.manager.establish_relationship(
            source_id, target_id, template_id, source_name, target_name
        )

    def modify_relationship(
        self,
        source_id: str,
        target_id: str,
        interaction_type: str,
        amount: int,
        context: dict[str, Any] | None = None,
    ) -> dict[Any, int]:
        """関係を変更（動的システムを使用）"""
        from .models import InteractionType as IT

        it = IT(interaction_type)
        return self.dynamics.apply_interaction_with_dynamics(
            source_id, target_id, it, amount, context
        )

    def update_decay(self) -> dict[str, dict[Any, int]]:
        """減衰を更新"""
        return self.decay.apply_decay()

    def generate_dialogue(
        self, speaker_id: str, listener_id: str, context: str
    ) -> GeneratedDialogue | None:
        """対話を生成"""
        from .dialogue import DialogueContext as DC

        return self.dialogue.generate_dialogue(speaker_id, listener_id, DC(context))

    def check_scenarios(self, player_id: str = "player") -> list[GeneratedScenario]:
        """シナリオをチェック"""
        return self.branching.check_for_scenarios(player_id)

    def save(
        self, filename: str = "relationship_save.json", format: str = "json"
    ) -> dict[str, Any]:
        """包括的にセーブ"""
        return self.save_system.save_comprehensive(filename, SaveFormat(format))

    def load(self, filename: str) -> dict[str, Any]:
        """包括的にロード"""
        return self.save_system.load_comprehensive(filename)

    def get_status_report(self) -> dict[str, Any]:
        """ステータスレポートを取得"""
        report = {
            "relationship_manager": self.manager.get_statistics(),
            "faction": self.faction.get_faction_statistics(),
            "romance": self.romance.get_romance_statistics(),
            "mentorship": self.mentorship.get_mentorship_statistics(),
            "betrayal": self.betrayal.get_betrayal_statistics(),
            "memory": self.memory.get_memory_statistics(),
            "quest_integration": self.quest_integration.get_integration_statistics(),
            "world_integration": self.world_integration.get_integration_statistics(),
            "graph_health": self.visualizer.analyze_graph_health(),
        }
        return report


def create_engine(
    data_path: str = "data/character_relations.yaml",
) -> RelationshipSimulationEngine:
    """関係シミュレーションエンジンを作成"""
    return RelationshipSimulationEngine(data_path)
