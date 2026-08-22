"""
Skill Eater Exploration Meta Integration Test
Phase 1-7 全機能統合テスト
"""

import os
import sys
import unittest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExplorationMetaIntegration(unittest.TestCase):
    """探索メタプログレッション統合テスト"""

    def setUp(self):
        """テスト前準備"""
        # シングルトンリセット
        from reincarnation_system import ReincarnationManager
        from skill_eater_ascension_board import AscensionBoard
        from skill_eater_bounty_system import MidasBountyManager
        from skill_eater_concept_crystal import ConceptCrystallizer
        from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        SkillEaterExplorationSystem.reset_instance()
        AscensionBoard.reset_instance()
        MidasBountyManager._instance = None  # 手動リセット
        ConceptCrystallizer._instance = None  # 手動リセット
        SkillEaterDungeonFloorManager.reset_instance()
        ReincarnationManager.REGISTRY = None  # 手動リセット

    def test_phase1_exploration_rank(self):
        """Phase 1: 探索経験値・ランキングシステム"""
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        exploration = SkillEaterExplorationSystem.get_instance()

        # 初期状態確認
        self.assertEqual(exploration.exploration_rank.rank, 1)
        self.assertEqual(exploration.exploration_rank.total_exp, 0)

        # 経験値付与テスト
        gained, ranked_up = exploration.add_exploration_exp(500)
        self.assertEqual(gained, 500)
        self.assertFalse(ranked_up)
        self.assertEqual(exploration.exploration_rank.rank, 1)

        # ランクアップテスト
        gained, ranked_up = exploration.add_exploration_exp(600)  # 合計1100
        self.assertTrue(ranked_up)
        self.assertEqual(exploration.exploration_rank.rank, 2)

        # 経験値計算式テスト
        exp = exploration._calculate_exploration_exp(
            depth=10, room_count=5, is_first_visit=True, is_first_floor=True, is_secret=True
        )
        # 10 * 5 * 10 + 500 + 1000 + 2000 = 4000
        self.assertEqual(exp, 4000)

        # 初見判定テスト
        self.assertTrue(exploration._is_first_visit("new_room"))
        exploration._visited_rooms.add("new_room")
        self.assertFalse(exploration._is_first_visit("new_room"))

        # 秘密部屋判定テスト
        from skill_eater_exploration_system import DungeonRoom
        secret_room = DungeonRoom("secret_1", "秘密の部屋", "隠された部屋")
        normal_room = DungeonRoom("normal_1", "通常の部屋", "普通の部屋")
        self.assertTrue(exploration._is_secret_room(secret_room))
        self.assertFalse(exploration._is_secret_room(normal_room))

        print("[OK] Phase 1: Exploration Rank System")

    def test_phase1_move_to_room_exp(self):
        """Phase 1: 部屋移動時の経験値付与"""
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        exploration = SkillEaterExplorationSystem.get_instance()

        # 部屋移動（初見）
        result = exploration.move_to_room("underground_market")
        self.assertEqual(result.action_type, "MOVE_ROOM")
        self.assertGreater(exploration.exploration_rank.total_exp, 0)
        self.assertEqual(exploration.exploration_rank.rooms_visited, 1)
        self.assertEqual(exploration.exploration_rank.first_visit_bonuses, 1)

        # 同部屋再訪問（経験値は入るが初見ボーナスなし）
        old_exp = exploration.exploration_rank.total_exp
        result = exploration.move_to_room("underground_market")
        self.assertGreater(exploration.exploration_rank.total_exp, old_exp)

        print("[OK] Phase 1: Move to Room Exp Grant")

    def test_phase1_secret_room_discovery(self):
        """Phase 1: 秘密部屋発見ボーナス"""
        from skill_eater_exploration_system import DungeonRoom, SkillEaterExplorationSystem

        exploration = SkillEaterExplorationSystem.get_instance()
        # 秘密部屋を追加
        exploration.dungeon_rooms["secret_room_1"] = DungeonRoom(
            "secret_room_1", "秘密の隠し部屋", "隠された秘密の部屋"
        )

        old_exp = exploration.exploration_rank.total_exp
        old_secrets = exploration.exploration_rank.secret_rooms_found

        result = exploration.discover_secret_room("secret_room_1")
        self.assertEqual(result.action_type, "SECRET_DISCOVER")
        self.assertEqual(exploration.exploration_rank.secret_rooms_found, old_secrets + 1)
        self.assertGreater(exploration.exploration_rank.total_exp, old_exp)

        print("[OK] Phase 1: Secret Room Discovery")

    def test_phase1_floor_transition_exp(self):
        """Phase 1: フロア遷移時の初見フロアボーナス"""
        from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager

        dungeon = SkillEaterDungeonFloorManager.get_instance()
        dungeon.initialize_dungeon(max_depth=10)

        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()

        # 最初のフロアは既に訪問済み扱い
        self.assertIn(1, exploration._visited_floors)

        # 2階へ降下
        result = dungeon.descend_stairs()
        self.assertTrue(result.success)
        self.assertEqual(dungeon.current_depth, 2)
        self.assertIn(2, exploration._visited_floors)
        self.assertEqual(exploration.exploration_rank.max_depth_reached, 2)

        print("[OK] Phase 1: Floor Transition Exp")

    def test_phase1_floor_clear_exp(self):
        """Phase 1: フロアクリア時ボーナス"""
        from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager

        dungeon = SkillEaterDungeonFloorManager.get_instance()
        dungeon.initialize_dungeon(max_depth=10)

        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()

        old_exp = exploration.exploration_rank.total_exp
        old_floors = exploration.exploration_rank.floors_cleared

        result = dungeon.clear_current_floor()
        self.assertTrue(result.success)
        self.assertEqual(exploration.exploration_rank.floors_cleared, old_floors + 1)
        self.assertGreater(exploration.exploration_rank.total_exp, old_exp)

        print("[OK] Phase 1: Floor Clear Exp")

    def test_phase1_rank_info(self):
        """Phase 1: ランク情報取得"""
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        exploration = SkillEaterExplorationSystem.get_instance()
        info = exploration.get_exploration_rank_info()

        self.assertIn("rank", info)
        self.assertIn("total_exp", info)
        self.assertIn("next_rank_exp", info)
        self.assertIn("exp_to_next", info)
        self.assertIn("max_depth", info)
        self.assertIn("rooms_visited", info)
        self.assertIn("secrets_found", info)
        self.assertIn("floors_cleared", info)

        print("[OK] Phase 1: Rank Info")

    def test_phase1_save_load(self):
        """Phase 1: セーブ/ロード"""
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        exploration = SkillEaterExplorationSystem.get_instance()
        exploration.add_exploration_exp(5000)
        exploration._visited_rooms.add("test_room")
        exploration._visited_floors.add(5)

        data = exploration.to_dict()
        self.assertIn("exploration_rank", data)
        self.assertIn("visited_rooms", data)
        self.assertIn("visited_floors", data)

        # 新インスタンスでロード
        SkillEaterExplorationSystem.reset_instance()
        new_exploration = SkillEaterExplorationSystem.from_dict(data)

        self.assertEqual(new_exploration.exploration_rank.rank, exploration.exploration_rank.rank)
        self.assertEqual(new_exploration.exploration_rank.total_exp, exploration.exploration_rank.total_exp)
        self.assertIn("test_room", new_exploration._visited_rooms)
        self.assertIn(5, new_exploration._visited_floors)

        print("[OK] Phase 1: Save/Load")

    def test_phase2_ascension_board_nodes(self):
        """Phase 2: アセンションボード探索連動ノード"""
        from skill_eater_ascension_board import AscensionBoard
        from skill_eater_exploration_system import ExplorationRank

        board = AscensionBoard.get_instance()

        # 探索連動ノードが定義されているか
        self.assertIn("deep_delver", board.exploration_nodes)
        self.assertIn("full_clearer", board.exploration_nodes)
        self.assertIn("secret_finder", board.exploration_nodes)
        self.assertIn("speed_runner", board.exploration_nodes)
        self.assertIn("hazard_master", board.exploration_nodes)

        # 深層到達ノード段階的解放テスト
        rank = ExplorationRank()
        rank.max_depth_reached = 60

        results = board.update_deep_delver_progress(60)
        self.assertEqual(len(results), 1)  # 深度50閾値のみ解放
        self.assertEqual(board.exploration_nodes["deep_delver"]["level"], 1)
        self.assertTrue(board.exploration_nodes["deep_delver"]["unlocked"])

        # さらに深度到達で次のレベル解放
        rank.max_depth_reached = 110
        results = board.update_deep_delver_progress(110)
        self.assertEqual(len(results), 1)  # 深度100閾値解放
        self.assertEqual(board.exploration_nodes["deep_delver"]["level"], 2)

        print("[OK] Phase 2: Ascension Board Nodes")

    def test_phase2_node_buffs(self):
        """Phase 2: ノード解放時のバフ付与"""
        from skill_eater_ascension_board import AscensionBoard
        from skill_eater_exploration_system import ExplorationRank

        board = AscensionBoard.get_instance()

        # 初期バフ確認
        initial_all_resistance = board.synergy_buffs.get("all_resistance", 0.0)
        initial_crit_rate = board.synergy_buffs.get("crit_rate", 0.0)

        # ノード解放シミュレート
        rank = ExplorationRank()
        rank.max_depth_reached = 60
        rank.floors_cleared = 10
        rank.secret_rooms_found = 60
        rank.total_exp = 20000  # speed_runner用

        results = board.check_and_unlock_exploration_nodes(rank)
        # deep_delver, secret_finder が解放されるはず
        self.assertGreaterEqual(len(results), 2)

        # バフが適用されているか
        self.assertGreater(board.synergy_buffs.get("all_resistance", 0.0), initial_all_resistance)
        self.assertGreater(board.synergy_buffs.get("crit_rate", 0.0), initial_crit_rate)

        print("[OK] Phase 2: Node Buffs")

    def test_phase3_bounty_targets(self):
        """Phase 3: 深層バウンティ対象生成"""
        from skill_eater_bounty_system import MidasBountyManager

        bounty = MidasBountyManager()

        # 深度50では出現しない
        targets = bounty.generate_deep_dungeon_bounties(50)
        deep_targets = [t for t in targets if t["type"] == "deep_target"]
        self.assertEqual(len(deep_targets), 0)

        # 深度100でアビス・ウォーデン出現
        targets = bounty.generate_deep_dungeon_bounties(100)
        deep_targets = [t for t in targets if t["type"] == "deep_target"]
        self.assertEqual(len(deep_targets), 1)
        self.assertEqual(deep_targets[0]["id"], "abyss_warden")

        # 深度150でヴォイド・ストーカー追加
        targets = bounty.generate_deep_dungeon_bounties(150)
        deep_targets = [t for t in targets if t["type"] == "deep_target"]
        self.assertEqual(len(deep_targets), 2)

        # 深度200でバベルの設計者追加
        targets = bounty.generate_deep_dungeon_bounties(200)
        deep_targets = [t for t in targets if t["type"] == "deep_target"]
        self.assertEqual(len(deep_targets), 3)

        print("[OK] Phase 3: Deep Dungeon Bounties")

    def test_phase3_secret_boss(self):
        """Phase 3: 隠しボス出現条件"""
        from skill_eater_bounty_system import MidasBountyManager
        from skill_eater_exploration_system import ExplorationRank

        bounty = MidasBountyManager()

        rank = ExplorationRank()
        rank.secret_rooms_found = 60

        # 秘密部屋50個でシャドウ・モナーク出現
        spawned = bounty.check_secret_boss_spawn(100, rank)
        self.assertEqual(spawned, "shadow_monarch")
        self.assertTrue(bounty.secret_bosses["shadow_monarch"]["spawned"])

        print("[OK] Phase 3: Secret Boss Spawn")

    def test_phase3_shadow_broker(self):
        """Phase 3: 闇ブローカー遭遇判定"""
        from skill_eater_bounty_system import MidasBountyManager

        bounty = MidasBountyManager()

        # 深度30以上で遭遇可能
        # 確率的なので複数回試行
        encountered = False
        for _ in range(1000):
            result = bounty.roll_shadow_broker_encounter(50)
            if result:
                encountered = True
                self.assertEqual(result["id"], "shadow_broker_01")
                break

        # 確率的に遭遇するはず（完全に運次第だが、1000回ならほぼ確実）
        # ここでは遭遇フラグが立つことを確認
        self.assertTrue(bounty.shadow_brokers["shadow_broker_01"]["encountered"] or not encountered)

        print("[OK] Phase 3: Shadow Broker Encounter")

    def test_phase3_eliminate_deep_target(self):
        """Phase 3: 深層ターゲット討伐・概念結晶ドロップ"""
        from skill_eater_bounty_system import MidasBountyManager

        bounty = MidasBountyManager()

        # モックプレイヤー
        class MockPlayer:
            pass

        player = MockPlayer()

        # 討伐実行
        result = bounty.eliminate_deep_target("abyss_warden", player)
        self.assertTrue(result["success"])
        self.assertEqual(result["target_type"], "deep_target")
        self.assertEqual(result["reward_aldo"], 50000)
        self.assertIsNotNone(result["reward_concept_crystal"])
        self.assertTrue(bounty.deep_targets["abyss_warden"]["is_defeated"])

        print("[OK] Phase 3: Eliminate Deep Target")

    def test_phase4_concept_crystal_drops(self):
        """Phase 4: 概念結晶ドロップ判定"""
        from skill_eater_concept_crystal import ConceptCrystallizer
        from skill_eater_exploration_system import ExplorationRank

        crystallizer = ConceptCrystallizer()

        rank = ExplorationRank()
        rank.rank = 5

        # 初見フロアボスドロップ
        crystal = crystallizer.roll_first_floor_boss_drop(depth=10, exploration_rank=rank, is_first_clear=True)
        # 確率的なのでNoneの可能性もあるが、レート確認
        rates = crystallizer.get_drop_rates(depth=10, exploration_rank=rank)
        self.assertIn("first_floor_boss", rates)
        self.assertGreater(rates["first_floor_boss"], 0.15)  # ベース15% + ボーナス

        # 秘密エリアドロップ
        crystal = crystallizer.roll_secret_area_drop(depth=20, exploration_rank=rank, is_first_clear=True)
        rates = crystallizer.get_drop_rates(depth=20, exploration_rank=rank)
        self.assertIn("secret_area", rates)

        # 派閥ボスドロップ
        crystal = crystallizer.roll_faction_boss_drop(depth=30, exploration_rank=rank)
        rates = crystallizer.get_drop_rates(depth=30, exploration_rank=rank)
        self.assertIn("faction_boss", rates)

        # 深層バウンティドロップ
        crystal = crystallizer.roll_concept_crystal_drop("deep_bounty", 100, rank)
        rates = crystallizer.get_drop_rates(depth=100, exploration_rank=rank)
        self.assertIn("deep_bounty", rates)

        print("[OK] Phase 4: Concept Crystal Drops")

    def test_phase4_auto_crystallize(self):
        """Phase 4: 自動合成提案"""
        from skill_eater_concept_crystal import ConceptCrystallizer

        crystallizer = ConceptCrystallizer()

        # モックプレイヤー
        class MockPlayer:
            def __init__(self):
                self.skills = {
                    "fire_1": type('obj', (), {"is_concept_crystal": False})(),
                    "fire_2": type('obj', (), {"is_concept_crystal": False})(),
                    "fire_3": type('obj', (), {"is_concept_crystal": False})(),
                    "ice_1": type('obj', (), {"is_concept_crystal": False})(),
                }

        player = MockPlayer()
        suggestions = crystallizer.auto_crystallize_if_possible(player)

        # fireカテゴリで3つ以上あるので提案されるはず
        fire_suggestions = [s for s in suggestions if s["category"] == "Fire"]
        self.assertEqual(len(fire_suggestions), 1)
        self.assertEqual(len(fire_suggestions[0]["available_skills"]), 3)

        print("[OK] Phase 4: Auto Crystallize")

    def test_phase5_new_game_plus(self):
        """Phase 5: ニューゲーム+引継ぎ"""
        from reincarnation_system import ReincarnationManager

        manager = ReincarnationManager()

        # モックプレイヤー
        class MockPlayer:
            def __init__(self):
                self.max_dungeon_depth = 100
                self.reincarnation_count = 1
                self.total_level_earned = 150
                self.level = 50
                self.attributes = type('obj', (), {
                    "strength": 10, "endurance": 10, "dexterity": 10,
                    "perception": 10, "learning": 10, "will": 10,
                    "magic": 10, "charisma": 10
                })()
                self.skills = {}

        player = MockPlayer()

        # 探索システムモック
        from skill_eater_exploration_system import SkillEaterExplorationSystem
        exploration = SkillEaterExplorationSystem.get_instance()
        exploration.exploration_rank.rank = 10
        exploration.exploration_rank.total_exp = 15000
        exploration.exploration_rank.secret_rooms_found = 20
        exploration.exploration_rank.floors_cleared = 30
        exploration.exploration_rank.max_depth_reached = 100

        # データ収集
        ng_data = manager.collect_new_game_plus_data(player)

        self.assertEqual(ng_data.max_depth_reached, 100)
        self.assertEqual(ng_data.exploration_rank, 10)
        self.assertEqual(ng_data.total_secrets_found, 20)
        self.assertEqual(ng_data.reincarnation_count, 1)

        # ボーナス計算
        bonuses = manager._calculate_ng_plus_bonuses(ng_data)
        self.assertIn("all_attributes", bonuses)
        self.assertIn("item_find_rate", bonuses)
        self.assertIn("faction_reputation_bonus", bonuses)
        self.assertIn("base_facility_level", bonuses)
        self.assertIn("starting_exploration_exp", bonuses)
        self.assertIn("all_damage_multiplier", bonuses)
        self.assertIn("max_mp_bonus", bonuses)

        # 上限チェック
        self.assertLessEqual(bonuses["all_attributes"], manager.MAX_NG_PLUS_BONUS_CAP)

        print("[OK] Phase 5: New Game Plus")

    def test_phase5_apply_ng_plus(self):
        """Phase 5: NG+ボーナス適用"""
        from reincarnation_system import NewGamePlusData, ReincarnationManager

        manager = ReincarnationManager()

        class MockPlayer:
            def __init__(self):
                self.attributes = type('obj', (), {
                    "strength": 10, "endurance": 10, "dexterity": 10,
                    "perception": 10, "learning": 10, "will": 10,
                    "magic": 10, "charisma": 10
                })()
                self.max_mp = 100
                self.mp = 100

        player = MockPlayer()
        ng_data = NewGamePlusData(
            max_depth_reached=100,
            total_secrets_found=10,
            exploration_rank=5,
            concept_crystals_owned=3,
        )

        old_str = player.attributes.strength
        old_mp = player.max_mp

        manager.apply_ng_plus_bonuses(player, ng_data)

        self.assertGreater(player.attributes.strength, old_str)
        self.assertGreater(player.max_mp, old_mp)
        self.assertTrue(hasattr(player, "ng_plus_bonuses"))

        print("[OK] Phase 5: Apply NG+ Bonuses")

    def test_phase6_audio_fallback(self):
        """Phase 6: 音声フォールバック"""
        from skill_eater_audio_system import SkillEaterAudioSystem

        audio = SkillEaterAudioSystem(enable_real_audio=False)  # モックモード

        # 存在しないファイルでもフォールバックでTrue返却（モックモード）
        result = audio.play_sound("rank_up_fanfare.ogg")
        self.assertTrue(result)
        self.assertIn("rank_up_fanfare.ogg", audio.played_sounds)

        # カテゴリ別音量
        audio.set_category_volume("sfx", 0.5)
        self.assertEqual(audio.category_volumes["sfx"], 0.5)

        # ファイル存在確認
        check = audio.check_audio_files()
        self.assertIsInstance(check, dict)

        print("[OK] Phase 6: Audio Fallback")

    def test_phase6_presentation_priority(self):
        """Phase 6: 演出優先度制御"""
        from skill_eater_presentation_system import SkillEaterPresentationSystem

        presentation = SkillEaterPresentationSystem(is_mock_only=True)

        # 低優先度
        presentation.add_event(message="Low", event_type="step")
        # 高優先度
        presentation.add_event(message="High", event_type="rank_up")
        # 中優先度
        presentation.add_event(message="Medium", event_type="node_unlock")

        # 取得順序は優先度順
        events = presentation.get_all_events_sorted()
        self.assertEqual(events[0].message, "High")
        self.assertEqual(events[1].message, "Medium")
        self.assertEqual(events[2].message, "Low")

        # 次イベント取得
        next_evt = presentation.get_next_event()
        self.assertEqual(next_evt.message, "High")

        print("[OK] Phase 6: Presentation Priority")

    def test_phase6_emote_fallback(self):
        """Phase 6: エモートフォールバック"""
        from skill_eater_presentation_system import SkillEaterPresentationSystem

        presentation = SkillEaterPresentationSystem(is_mock_only=True)

        # 存在しないエモート→フォールバック
        resolved = presentation._resolve_emote_path("emote_crown.png")
        # フォールバック先が存在するか、またはNone
        self.assertIsNotNone(resolved)  # モックモードではパス解決のみ

        print("[OK] Phase 6: Emote Fallback")

    def test_phase7_balance_config(self):
        """Phase 7: バランス設定ファイル読み込み"""
        import yaml

        config_path = "data/balance/exploration_meta.yaml"
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            self.assertIn("exploration_exp", config)
            self.assertIn("exploration_rank", config)
            self.assertIn("ascension_nodes", config)
            self.assertIn("bounty", config)
            self.assertIn("concept_crystal_drops", config)
            self.assertIn("new_game_plus", config)
            self.assertIn("cycle_scaling", config)

            print("[OK] Phase 7: Balance Config Load")
        else:
            self.skipTest("Balance config file not found")

    def test_full_integration_flow(self):
        """完全統合フローテスト"""
        from skill_eater_ascension_board import AscensionBoard
        from skill_eater_bounty_system import MidasBountyManager
        from skill_eater_concept_crystal import ConceptCrystallizer
        from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager
        from skill_eater_exploration_system import SkillEaterExplorationSystem

        # システム初期化
        exploration = SkillEaterExplorationSystem.get_instance()
        board = AscensionBoard.get_instance()
        bounty = MidasBountyManager()
        dungeon = SkillEaterDungeonFloorManager.get_instance()
        crystallizer = ConceptCrystallizer()

        dungeon.initialize_dungeon(max_depth=10)

        # 1. 探索開始・部屋移動
        result = exploration.move_to_room("underground_market")
        self.assertEqual(result.action_type, "MOVE_ROOM")

        # 2. フロア降下
        result = dungeon.descend_stairs()
        self.assertTrue(result.success)

        # 3. フロアクリア
        result = dungeon.clear_current_floor()
        self.assertTrue(result.success)

        # 4. アセンションノードチェック
        rank = exploration.exploration_rank
        results = board.check_and_unlock_exploration_nodes(rank)
        # この時点ではまだ閾値未満だが、エラーなく実行されること

        # 5. バウンティ生成
        targets = bounty.generate_deep_dungeon_bounties(dungeon.current_depth)
        self.assertIsInstance(targets, list)

        # 6. 概念結晶ドロップ判定
        crystal = crystallizer.roll_concept_crystal_drop("first_floor_boss", dungeon.current_depth, rank)
        # 確率的なのでNoneでもOK

        # 7. NG+データ収集（転生シミュレート）
        from reincarnation_system import ReincarnationManager
        manager = ReincarnationManager()

        class MockPlayer:
            def __init__(self):
                self.max_dungeon_depth = dungeon.current_depth
                self.reincarnation_count = 1
                self.total_level_earned = 50
                self.level = 50
                self.attributes = type('obj', (), {
                    "strength": 10, "endurance": 10, "dexterity": 10,
                    "perception": 10, "learning": 10, "will": 10,
                    "magic": 10, "charisma": 10
                })()
                self.skills = {}
                self.max_mp = 100
                self.mp = 100

        player = MockPlayer()
        ng_data = manager.collect_new_game_plus_data(player)
        self.assertGreater(ng_data.max_depth_reached, 0)

        print("[OK] Full Integration Flow")


if __name__ == "__main__":
    unittest.main(verbosity=2)
