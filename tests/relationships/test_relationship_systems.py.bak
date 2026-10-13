"""
NPC Relationship Simulation - Test Suite
Step 19: Testing and validation
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.relationships import (
    BetrayalConflictSystem,
    BetrayalType,
    BranchingScenarioGenerator,
    CharacterArchetype,
    ComprehensiveRelationshipSaveSystem,
    ConflictState,
    DialogueContext,
    DialogueGenerationSystem,
    DynamicRelationshipSystem,
    FactionAffiliation,
    FactionRelationshipSystem,
    InteractionType,
    MemoryImportance,
    MemorySystem,
    MemoryType,
    MentorshipMechanics,
    PersonalitySystem,
    PersonalityTrait,
    RelationshipEdge,
    RelationshipGraph,
    RelationshipLevel,
    RelationshipManager,
    RelationshipNode,
    RelationshipType,
    RelationshipVisualizer,
    RomanceMechanics,
    RomanceStage,
    create_engine,
)


class TestRelationshipModels(unittest.TestCase):
    """関係モデルのテスト"""

    def test_relationship_types(self):
        """関係タイプの列挙型テスト"""
        self.assertEqual(RelationshipType.FAVORABILITY.value, "favorability")
        self.assertEqual(RelationshipType.ROMANCE.value, "romance")
        self.assertIn(RelationshipType.MENTORSHIP, list(RelationshipType))

    def test_relationship_levels(self):
        """関係レベルのテスト"""
        self.assertEqual(RelationshipLevel.MAXIMUM_TRUST.value, 100)
        self.assertEqual(RelationshipLevel.MAXIMUM_HATRED.value, -100)

    def test_relationship_edge(self):
        """関係エッジのテスト"""
        edge = RelationshipEdge("a", "b", RelationshipType.FAVORABILITY, level=50)
        self.assertEqual(edge.level, 50)
        edge.add_modifier(
            __import__(
                "src.relationships.models", fromlist=["RelationshipModifier"]
            ).RelationshipModifier(InteractionType.TALK, 10)
        )
        self.assertEqual(edge.level, 60)
        self.assertEqual(edge.get_level_category(), RelationshipLevel.VERY_LIKED)


class TestRelationshipGraph(unittest.TestCase):
    """関係グラフのテスト"""

    def setUp(self):
        self.graph = RelationshipGraph()
        self.graph.add_node(RelationshipNode("alice", "Alice"))
        self.graph.add_node(RelationshipNode("bob", "Bob"))
        self.graph.add_node(RelationshipNode("charlie", "Charlie"))

    def test_node_operations(self):
        """ノード操作のテスト"""
        self.assertTrue(self.graph.has_node("alice"))
        self.assertFalse(self.graph.has_node("dave"))
        self.assertEqual(len(self.graph.nodes), 3)

    def test_edge_operations(self):
        """エッジ操作のテスト"""
        edge = RelationshipEdge("alice", "bob", RelationshipType.FAVORABILITY, level=30)
        self.graph.add_edge(edge)
        self.assertTrue(self.graph.has_edge("alice", "bob", RelationshipType.FAVORABILITY))

        # 取得テスト
        retrieved = self.graph.get_edge("alice", "bob", RelationshipType.FAVORABILITY)
        self.assertEqual(retrieved.level, 30)

        # 関連ノード取得
        related = self.graph.get_related_nodes("alice")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0][0], "bob")

    def test_multi_layer_graph(self):
        """多層グラフのテスト"""
        self.graph.add_edge(
            RelationshipEdge("alice", "bob", RelationshipType.FAVORABILITY, level=30)
        )
        self.graph.add_edge(RelationshipEdge("alice", "bob", RelationshipType.FRIENDSHIP, level=50))
        self.graph.add_edge(RelationshipEdge("alice", "bob", RelationshipType.ROMANCE, level=70))

        edges = self.graph.get_edges_between("alice", "bob")
        self.assertEqual(len(edges), 3)

        # 関係タイプ別フィルタ
        romance_edges = self.graph.get_edges_by_type(RelationshipType.ROMANCE)
        self.assertEqual(len(romance_edges), 1)

    def test_graph_statistics(self):
        """グラフ統計のテスト"""
        self.graph.add_edge(
            RelationshipEdge("alice", "bob", RelationshipType.FAVORABILITY, level=30)
        )
        self.graph.add_edge(
            RelationshipEdge("bob", "charlie", RelationshipType.FAVORABILITY, level=-40)
        )

        stats = self.graph.get_graph_statistics()
        self.assertEqual(stats["node_count"], 3)
        self.assertEqual(stats["edge_count"], 2)
        self.assertIn("favorability", stats["relationship_type_distribution"])

    def test_serialization(self):
        """シリアライゼーションのテスト"""
        self.graph.add_edge(
            RelationshipEdge("alice", "bob", RelationshipType.FAVORABILITY, level=30)
        )
        self.graph.add_edge(
            RelationshipEdge("bob", "charlie", RelationshipType.FAVORABILITY, level=-40)
        )

        data = self.graph.to_dict()
        restored = RelationshipGraph.from_dict(data)

        self.assertEqual(len(restored.nodes), 3)
        self.assertEqual(len(restored.edges), 2)
        self.assertEqual(restored.get_edge("alice", "bob", RelationshipType.FAVORABILITY).level, 30)


class TestRelationshipManager(unittest.TestCase):
    """関係マネージャーのテスト"""

    def setUp(self):
        # テンポラリファイルを作成
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        self._create_test_data()
        self.manager = RelationshipManager(self.data_file)

    def _create_test_data(self):
        """テスト用データを作成"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 30
    decay_rate: 0.01
    romance_potential: 0.3
    betrayal_risk: 0.1
    mentorship_value: 0.2
    faction_influence: 0.2

global_settings:
  max_single_change: 25
  min_relationship_level: -100
  max_relationship_level: 100
"""
            )

    def test_initialization(self):
        """初期化のテスト"""
        self.assertTrue(self.manager._is_initialized)
        self.assertIn("friends", self.manager.templates)

    def test_character_initialization(self):
        """キャラクター初期化のテスト"""
        node = self.manager.initialize_character("npc1", "NPC1")
        self.assertEqual(node.name, "NPC1")
        self.assertTrue(self.manager.graph.has_node("npc1"))

    def test_relationship_establishment(self):
        """関係確立のテスト"""
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")

        success = self.manager.establish_relationship("npc1", "npc2", "friends")
        self.assertTrue(success)

        level = self.manager.get_relationship_level("npc1", "npc2", RelationshipType.FAVORABILITY)
        self.assertEqual(level, 30)

    def test_relationship_modification(self):
        """関係変更のテスト"""
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")
        self.manager.establish_relationship("npc1", "npc2", "friends")

        changes = self.manager.modify_relationship("npc1", "npc2", InteractionType.TALK, 10)
        self.assertIn(RelationshipType.FAVORABILITY, changes)
        self.assertEqual(changes[RelationshipType.FAVORABILITY], 40)


class TestDynamicSystem(unittest.TestCase):
    """動的システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 30
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")
        self.manager.establish_relationship("npc1", "npc2", "friends")
        self.dynamics = DynamicRelationshipSystem(self.manager)

    def test_dynamic_interaction(self):
        """動的インタラクションのテスト"""
        changes = self.dynamics.apply_interaction_with_dynamics(
            "npc1", "npc2", InteractionType.TALK, 15
        )
        self.assertIn(RelationshipType.FAVORABILITY, changes)
        # 即時効果 + 累積効果が適用される
        self.assertGreaterEqual(changes[RelationshipType.FAVORABILITY], 15)


class TestFactionSystem(unittest.TestCase):
    """派閥システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 30
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.graph = self.manager.graph
        self.faction_system = FactionRelationshipSystem(self.manager)

    def test_faction_registration(self):
        """派閥登録のテスト"""
        self.faction_system.register_faction("guild_a", "Guild A", power_level=50)
        self.assertIn("guild_a", self.faction_system.factions)

    def test_member_assignment(self):
        """メンバー所属のテスト"""
        self.manager.initialize_character("npc1", "NPC1")
        self.faction_system.register_faction("guild_a", "Guild A")
        self.faction_system.assign_to_faction("npc1", "guild_a", FactionAffiliation.MEMBER)

        node = self.graph.get_node("npc1")
        self.assertIn("guild_a", node.faction_affiliations)

    def test_faction_relation(self):
        """派閥間関係のテスト"""
        self.faction_system.register_faction("guild_a", "Guild A")
        self.faction_system.register_faction("guild_b", "Guild B")

        relation = self.faction_system.update_faction_relation("guild_a", "guild_b", 30)
        self.assertIsNotNone(relation)
        self.assertGreater(relation.relation_strength, 0)


class TestRomanceSystem(unittest.TestCase):
    """ロマンスシステムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  lovers:
    id: "lovers"
    name: "恋人"
    relationship_type: "romance"
    initial_level: 70
    decay_rate: 0.003
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("player", "Player")
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.establish_relationship("player", "npc1", "lovers")
        self.romance = RomanceMechanics(self.manager)

    def test_romance_initiation(self):
        """ロマンス開始のテスト"""
        state = self.romance.initiate_romance("player", "npc1")
        self.assertIsNotNone(state)
        self.assertIn(RomanceStage.DATING, [state.stage])

    def test_compatibility(self):
        """相性計算のテスト"""
        # パーソナリティを設定
        self.manager.graph.get_node("player").personality_traits = {
            "openness": 0.7,
            "extraversion": 0.6,
        }
        self.manager.graph.get_node("npc1").personality_traits = {
            "openness": 0.7,
            "extraversion": 0.6,
        }

        compat = self.romance.calculate_compatibility("player", "npc1")
        self.assertGreater(compat, 0.5)


class TestMentorshipSystem(unittest.TestCase):
    """師弟システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  master_apprentice:
    id: "master_apprentice"
    name: "師弟"
    relationship_type: "mentorship"
    initial_level: 50
    decay_rate: 0.001
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("master", "Master")
        self.manager.initialize_character("apprentice", "Apprentice")
        self.manager.establish_relationship("master", "apprentice", "master_apprentice")
        self.mentorship = MentorshipMechanics(self.manager)

    def test_mentorship_establishment(self):
        """師弟関係確立のテスト"""
        state = self.mentorship.establish_mentorship("master", "apprentice")
        self.assertIsNotNone(state)

    def test_skill_teaching(self):
        """スキル教授のテスト"""
        self.mentorship.establish_mentorship("master", "apprentice")
        # レベルを上げる
        self.manager.modify_relationship(
            "master", "apprentice", InteractionType.KNOWLEDGE_SHARE, 50
        )

        result = self.mentorship.teach_skill("master", "apprentice", "basic_sword")
        self.assertTrue(result["success"])


class TestBetrayalSystem(unittest.TestCase):
    """裏切りシステムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 60
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")
        self.manager.establish_relationship("npc1", "npc2", "friends")
        self.betrayal = BetrayalConflictSystem(self.manager)

    def test_betrayal_commit(self):
        """裏切り実行のテスト"""
        result = self.betrayal.commit_betrayal(
            "npc1",
            "npc2",
            BetrayalType.BACKSTAB,
            context={"evidence_available": True, "witnesses": ["npc3"]},
        )
        self.assertTrue(result["success"])
        self.assertLess(result["impact"]["favorability"], 60)

    def test_conflict_state(self):
        """対立状態のテスト"""
        self.betrayal.commit_betrayal("npc1", "npc2", BetrayalType.BACKSTAB)
        state = self.betrayal.get_conflict_state("npc1", "npc2")
        self.assertEqual(state, ConflictState.HOSTILE.value)


class TestMemorySystem(unittest.TestCase):
    """記憶システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 30
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")
        self.memory = MemorySystem(self.manager)

    def test_memory_creation(self):
        """記憶作成のテスト"""
        memory = self.memory.create_memory(
            "npc1",
            MemoryType.POSITIVE_EVENT,
            "Good event",
            MemoryImportance.SIGNIFICANT,
            other_id="npc2",
        )
        self.assertEqual(memory.character_id, "npc1")
        self.assertEqual(len(self.memory.memories), 1)

    def test_memory_recording_from_event(self):
        """イベントからの記憶記録テスト"""
        memory = self.memory.record_relationship_event(
            "npc1", "npc2", RelationshipType.FAVORABILITY, 25
        )
        self.assertIsNotNone(memory)


class TestPersonalitySystem(unittest.TestCase):
    """パーソナリティシステムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 30
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("npc1", "NPC1")
        self.personality = PersonalitySystem(self.manager)

    def test_personality_assignment(self):
        """パーソナリティ割り当てのテスト"""
        profile = self.personality.assign_personality(
            "npc1", {PersonalityTrait.EXTRAVERSION: 0.8}, CharacterArchetype.HERO
        )
        self.assertEqual(profile.get_trait(PersonalityTrait.EXTRAVERSION), 0.8)
        self.assertEqual(profile.archetype, CharacterArchetype.HERO)

    def test_interaction_modifier(self):
        """インタラクション修正子のテスト"""
        self.personality.assign_personality("npc1", {PersonalityTrait.EXTRAVERSION: 0.8})
        modifier = self.personality.get_interaction_modifier(
            "npc1", "npc2", InteractionType.TALK, RelationshipType.FAVORABILITY
        )
        self.assertGreater(modifier, 0.0)


class TestDialogueSystem(unittest.TestCase):
    """対話システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 60
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("player", "Player")
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.establish_relationship("player", "npc1", "friends")
        self.personality = PersonalitySystem(self.manager)
        self.dialogue = DialogueGenerationSystem(self.manager, self.personality)

    def test_dialogue_generation(self):
        """対話生成のテスト（乱数を固定して決定的にする）"""
        import random

        random.seed(0)
        dialogue = self.dialogue.generate_dialogue("npc1", "player", DialogueContext.GREETING)
        self.assertIsNotNone(dialogue)
        self.assertTrue(isinstance(dialogue.text, str) and len(dialogue.text) > 0)


class TestVisualization(unittest.TestCase):
    """可視化システムのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 60
    decay_rate: 0.01
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.initialize_character("npc2", "NPC2")
        self.manager.establish_relationship("npc1", "npc2", "friends")
        self.visualizer = RelationshipVisualizer(self.manager)

    def test_text_visualization(self):
        """テキスト可視化のテスト"""
        text = self.visualizer.visualize_as_text("npc1")
        self.assertIn("NPC1", text)
        self.assertIn("NPC2", text)

    def test_json_visualization(self):
        """JSON可視化のテスト"""
        import json

        json_str = self.visualizer.visualize_as_json("npc1")
        data = json.loads(json_str)
        self.assertIn("relationships", data)

    def test_graph_health(self):
        """グラフ健全性のテスト"""
        health = self.visualizer.analyze_graph_health()
        self.assertIn("health_score", health)


class TestSaveLoad(unittest.TestCase):
    """セーブ/ロードのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 60
    decay_rate: 0.01
  lovers:
    id: "lovers"
    name: "恋人"
    relationship_type: "romance"
    initial_level: 70
    decay_rate: 0.003
"""
            )
        self.engine = create_engine(self.data_file)
        self.engine.initialize_character("player", "Player")
        self.engine.initialize_character("npc1", "NPC1", "hero")
        self.engine.establish_relationship("player", "npc1", "friends")
        self.engine.establish_relationship("player", "npc1", "lovers")

        # ロマンス状態を作成
        self.engine.romance.initiate_romance("player", "npc1")

        # 記憶を作成
        self.engine.memory.create_memory(
            "player",
            MemoryType.POSITIVE_EVENT,
            "Test memory",
            MemoryImportance.MAJOR,
            other_id="npc1",
        )

        self.save_file = os.path.join(self.temp_dir, "save.json")

    def test_comprehensive_save(self):
        """包括的セーブのテスト"""
        result = self.engine.save(self.save_file)
        self.assertTrue(result["success"])
        self.assertTrue(os.path.exists(self.save_file))

    def test_comprehensive_load(self):
        """包括的ロードのテスト"""
        # セーブ
        save_result = self.engine.save(self.save_file)
        self.assertTrue(save_result["success"])

        # 新しいエンジンでロード
        new_engine = create_engine(self.data_file)
        load_result = new_engine.load(self.save_file)
        self.assertTrue(load_result["success"])

        # 関係が復元されているかチェック
        level = new_engine.manager.get_relationship_level(
            "player", "npc1", RelationshipType.FAVORABILITY
        )
        self.assertEqual(level, 60)

        # ロマンス状態が復元されているかチェック
        romance_state = new_engine.romance.get_romance_state("player", "npc1")
        self.assertIsNotNone(romance_state)

    def test_backup_creation(self):
        """バックアップ作成のテスト"""
        persistence = ComprehensiveRelationshipSaveSystem(self.engine.manager)
        backup = persistence.create_incremental_save(self.save_file, time.time())
        self.assertIn("success", backup)


class TestIntegrationEngine(unittest.TestCase):
    """統合エンジンのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 60
    decay_rate: 0.01
  lovers:
    id: "lovers"
    name: "恋人"
    relationship_type: "romance"
    initial_level: 70
    decay_rate: 0.003
  master_apprentice:
    id: "master_apprentice"
    name: "師弟"
    relationship_type: "mentorship"
    initial_level: 50
    decay_rate: 0.001
"""
            )
        self.engine = create_engine(self.data_file)

    def test_engine_initialization(self):
        """エンジン初期化のテスト"""
        self.assertIsNotNone(self.engine.manager)
        self.assertIsNotNone(self.engine.romance)
        self.assertIsNotNone(self.engine.mentorship)
        self.assertIsNotNone(self.engine.betrayal)

    def test_full_workflow(self):
        """完全なワークフローのテスト"""
        # キャラクター初期化
        self.engine.initialize_character("player", "Player", "hero")
        self.engine.initialize_character("npc1", "NPC1", "sage")
        self.engine.initialize_character("npc2", "NPC2", "villain")

        # 関係確立
        self.engine.establish_relationship("player", "npc1", "friends")
        self.engine.establish_relationship("player", "npc1", "lovers")
        self.engine.establish_relationship("player", "npc2", "friends")

        # 関係変更
        self.engine.modify_relationship("player", "npc1", "talk", 10)
        self.engine.modify_relationship("player", "npc2", "gift", -5)

        # シナリオチェック
        scenarios = self.engine.check_scenarios("player")
        self.assertIsInstance(scenarios, list)

        # 対話生成
        dialogue = self.engine.generate_dialogue("npc1", "player", "greeting")
        self.assertIsNotNone(dialogue)

        # ステータスレポート
        report = self.engine.get_status_report()
        self.assertIn("relationship_manager", report)
        self.assertIn("romance", report)

    def test_status_report(self):
        """ステータスレポートのテスト"""
        report = self.engine.get_status_report()
        self.assertIn("graph_health", report)


class TestBranching(unittest.TestCase):
    """分岐シナリオ生成のテスト"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.temp_dir, "test_relations.yaml")
        with open(self.data_file, "w", encoding="utf-8") as f:
            f.write(
                """
relationship_templates:
  lovers:
    id: "lovers"
    name: "恋人"
    relationship_type: "romance"
    initial_level: 70
    decay_rate: 0.003
"""
            )
        self.manager = RelationshipManager(self.data_file)
        self.manager.initialize_character("player", "Player")
        self.manager.initialize_character("npc1", "NPC1")
        self.manager.establish_relationship("player", "npc1", "lovers")
        self.branching = BranchingScenarioGenerator(self.manager)

    def test_scenario_generation(self):
        """シナリオ生成のテスト"""
        scenarios = self.branching.check_for_scenarios("player")
        # ロマンスレベルが高いため、何らかのシナリオが生成されるはず
        self.assertIsInstance(scenarios, list)


def run_all_tests():
    """すべてのテストを実行"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestRelationshipModels,
        TestRelationshipGraph,
        TestRelationshipManager,
        TestDynamicSystem,
        TestFactionSystem,
        TestRomanceSystem,
        TestMentorshipSystem,
        TestBetrayalSystem,
        TestMemorySystem,
        TestPersonalitySystem,
        TestDialogueSystem,
        TestVisualization,
        TestSaveLoad,
        TestIntegrationEngine,
        TestBranching,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
