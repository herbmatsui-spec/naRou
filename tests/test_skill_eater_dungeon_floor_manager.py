"""
test_skill_eater_dungeon_floor_manager.py
SkillEaterDungeonFloorManager のテストスイート (Steps 67-72)
"""
from __future__ import annotations

import os
import tempfile

import pytest

# テスト用にモックモードで初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_dungeon_floor_manager import (
    DepthScalingConfig,
    DungeonFloor,
    DungeonTheme,
    FloorTransitionRecord,
    FloorTransitionType,
    SkillEaterDungeonFloorManager,
)
from skill_eater_presentation_system import SkillEaterPresentationSystem


class TestDataStructures:
    """Step 67: データ構造・基本機能テスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)

    def test_dungeon_theme_from_depth(self):
        """DungeonTheme.from_depth 境界値テスト"""
        assert DungeonTheme.from_depth(1) == DungeonTheme.INDUSTRIAL_RUINS
        assert DungeonTheme.from_depth(15) == DungeonTheme.INDUSTRIAL_RUINS
        assert DungeonTheme.from_depth(16) == DungeonTheme.NEON_SEWERS
        assert DungeonTheme.from_depth(30) == DungeonTheme.NEON_SEWERS
        assert DungeonTheme.from_depth(31) == DungeonTheme.MIDAS_LABS
        assert DungeonTheme.from_depth(50) == DungeonTheme.MIDAS_LABS
        assert DungeonTheme.from_depth(51) == DungeonTheme.BABEL_CORE
        assert DungeonTheme.from_depth(99) == DungeonTheme.BABEL_CORE

    def test_depth_scaling_config_defaults(self):
        """DepthScalingConfig デフォルト値テスト"""
        config = DepthScalingConfig()
        assert config.base_enemy_tier == 1
        assert config.enemy_tier_per_depth == 0.1
        assert config.base_trap_density == 0.1
        assert config.trap_density_per_depth == 0.02
        assert config.base_reward_multiplier == 1.0
        assert config.reward_multiplier_per_depth == 0.05
        assert config.boss_spawn_depth_interval == 10

    def test_dungeon_floor_to_dict_from_dict(self):
        """DungeonFloor シリアライズ/デシリアライズ テスト"""
        from skill_eater_exploration_system import DungeonRoom

        room1 = DungeonRoom("room_1", "Room 1", "Desc 1")
        room2 = DungeonRoom("room_2", "Room 2", "Desc 2")
        floor = DungeonFloor(
            floor_id="floor_1",
            depth=1,
            theme=DungeonTheme.INDUSTRIAL_RUINS,
            rooms=[room1, room2],
            boss_room=room2,
            exit_to_next={"type": "stairs", "target_floor": "floor_2"},
            hazard_level=10,
            cleared=True,
        )

        room_lookup = {"room_1": room1, "room_2": room2}
        data = floor.to_dict()
        restored = DungeonFloor.from_dict(data, room_lookup)

        assert restored.floor_id == "floor_1"
        assert restored.depth == 1
        assert restored.theme == DungeonTheme.INDUSTRIAL_RUINS
        assert len(restored.rooms) == 2
        assert restored.boss_room == room2
        assert restored.hazard_level == 10
        assert restored.cleared is True

    def test_floor_transition_record_serialization(self):
        """FloorTransitionRecord シリアライズテスト"""
        record = FloorTransitionRecord(
            timestamp=1234567890.0,
            from_floor="floor_1",
            to_floor="floor_2",
            transition_type=FloorTransitionType.STAIRS_DOWN,
            hazard_before=10,
            hazard_after=15,
        )
        data = record.to_dict()
        assert data["from_floor"] == "floor_1"
        assert data["to_floor"] == "floor_2"
        assert data["transition_type"] == FloorTransitionType.STAIRS_DOWN.value


class TestFloorGeneration:
    """Step 67 続き: フロア生成テスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)

    def test_initialize_dungeon_creates_all_floors(self):
        """initialize_dungeon が全フロア生成するか"""
        self.manager.initialize_dungeon(max_depth=10)
        assert len(self.manager.floors) == 10
        assert self.manager.current_floor_id == "floor_1"
        assert self.manager.current_depth == 1

    def test_floor_theme_assignment(self):
        """フロアごとのテーマ割り当てテスト"""
        self.manager.initialize_dungeon(max_depth=60)

        # 深度1-15: INDUSTRIAL_RUINS
        for d in range(1, 16):
            floor = self.manager.floors[f"floor_{d}"]
            assert floor.theme == DungeonTheme.INDUSTRIAL_RUINS, f"Depth {d}: expected INDUSTRIAL_RUINS, got {floor.theme}"

        # 深度16-30: NEON_SEWERS
        for d in range(16, 31):
            floor = self.manager.floors[f"floor_{d}"]
            assert floor.theme == DungeonTheme.NEON_SEWERS, f"Depth {d}: expected NEON_SEWERS, got {floor.theme}"

        # 深度31-50: MIDAS_LABS
        for d in range(31, 51):
            floor = self.manager.floors[f"floor_{d}"]
            assert floor.theme == DungeonTheme.MIDAS_LABS, f"Depth {d}: expected MIDAS_LABS, got {floor.theme}"

        # 深度51-60: BABEL_CORE
        for d in range(51, 61):
            floor = self.manager.floors[f"floor_{d}"]
            assert floor.theme == DungeonTheme.BABEL_CORE, f"Depth {d}: expected BABEL_CORE, got {floor.theme}"

    def test_room_count_scales_with_depth(self):
        """部屋数が深度に応じてスケールするか"""
        self.manager.initialize_dungeon(max_depth=20)

        floor_1 = self.manager.floors["floor_1"]
        floor_10 = self.manager.floors["floor_10"]
        floor_20 = self.manager.floors["floor_20"]

        # 最小3部屋
        assert len(floor_1.rooms) >= 3
        # 深度に応じて増加
        assert len(floor_10.rooms) >= len(floor_1.rooms)
        assert len(floor_20.rooms) >= len(floor_10.rooms)
        # 最大12部屋
        assert len(floor_20.rooms) <= 12

    def test_boss_room_spawn_interval(self):
        """ボス部屋が正しい間隔で生成されるか"""
        self.manager.initialize_dungeon(max_depth=30)

        for d in range(1, 31):
            floor = self.manager.floors[f"floor_{d}"]
            if d % 10 == 0:
                assert floor.boss_room is not None, f"Depth {d}: boss room should exist"
            else:
                # 10の倍数以外でもランダムで生成される可能性があるため、存在しないことを保証はしない
                pass


class TestDepthScaling:
    """Step 69: 深度スケーリングテスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)

    def test_calculate_enemy_tier(self):
        """敵ティア計算テスト"""
        assert self.manager.calculate_enemy_tier(1) == 1
        assert self.manager.calculate_enemy_tier(10) == 2
        assert self.manager.calculate_enemy_tier(25) == 3
        assert self.manager.calculate_enemy_tier(50) == 6
        assert self.manager.calculate_enemy_tier(99) == 10

    def test_calculate_trap_density(self):
        """トラップ密度計算テスト（上限0.8）"""
        import pytest
        assert self.manager.calculate_trap_density(1) == pytest.approx(0.12)
        assert self.manager.calculate_trap_density(10) == pytest.approx(0.3)
        assert self.manager.calculate_trap_density(35) == 0.8  # 上限でクランプ
        assert self.manager.calculate_trap_density(99) == 0.8

    def test_calculate_reward_multiplier(self):
        """報酬倍率計算テスト（上限3.0）"""
        assert self.manager.calculate_reward_multiplier(1) == 1.05
        assert self.manager.calculate_reward_multiplier(10) == 1.5
        assert self.manager.calculate_reward_multiplier(40) == 3.0  # 上限でクランプ
        assert self.manager.calculate_reward_multiplier(99) == 3.0

    def test_theme_transition_boundaries(self):
        """テーマ遷移境界テスト (15/16, 30/31, 50/51)"""
        self.manager.initialize_dungeon(max_depth=55)

        # 15->16: INDUSTRIAL_RUINS -> NEON_SEWERS
        assert self.manager.floors["floor_15"].theme == DungeonTheme.INDUSTRIAL_RUINS
        assert self.manager.floors["floor_16"].theme == DungeonTheme.NEON_SEWERS

        # 30->31: NEON_SEWERS -> MIDAS_LABS
        assert self.manager.floors["floor_30"].theme == DungeonTheme.NEON_SEWERS
        assert self.manager.floors["floor_31"].theme == DungeonTheme.MIDAS_LABS

        # 50->51: MIDAS_LABS -> BABEL_CORE
        assert self.manager.floors["floor_50"].theme == DungeonTheme.MIDAS_LABS
        assert self.manager.floors["floor_51"].theme == DungeonTheme.BABEL_CORE


class TestFloorTransitions:
    """Step 68: フロア移動テスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)
        self.manager.initialize_dungeon(max_depth=10)

    def test_can_descend_initial(self):
        """初期状態で降下可能か（ボスなしフロア）"""
        # floor_1 にはボスがいない（10の倍数ではない）
        assert self.manager.can_descend() is True

    def test_can_descend_blocked_by_boss(self):
        """ボス未クリアで降下ブロックされるか"""
        # floor_10 に移動（ボスあり）
        self.manager.current_floor_id = "floor_10"
        self.manager.current_depth = 10
        floor_10 = self.manager.floors["floor_10"]
        floor_10.cleared = False
        assert floor_10.boss_room is not None
        assert self.manager.can_descend() is False

    def test_can_descend_after_boss_clear(self):
        """ボスクリア後は降下可能か"""
        self.manager.current_floor_id = "floor_10"
        self.manager.current_depth = 10
        floor_10 = self.manager.floors["floor_10"]
        floor_10.cleared = True
        assert self.manager.can_descend() is True

    def test_can_ascend_from_floor_1(self):
        """フロア1からは上昇不可"""
        assert self.manager.can_ascend() is False

    def test_can_ascend_from_floor_2(self):
        """フロア2からは上昇可能"""
        self.manager.current_floor_id = "floor_2"
        self.manager.current_depth = 2
        assert self.manager.can_ascend() is True

    def test_can_use_elevator(self):
        """エレベーター判定テスト"""
        # floor_1 の exit_to_next タイプを確認
        floor_1 = self.manager.floors["floor_1"]
        floor_1.exit_to_next = {"type": "elevator", "target_floor": "floor_2"}
        assert self.manager.can_use_elevator() is True

        floor_1.exit_to_next = {"type": "stairs", "target_floor": "floor_2"}
        assert self.manager.can_use_elevator() is False

    def test_descend_stairs_success(self):
        """階段降下成功テスト"""
        result = self.manager.descend_stairs()
        assert result.success is True
        assert result.transition_type == FloorTransitionType.STAIRS_DOWN
        assert self.manager.current_depth == 2
        assert self.manager.current_floor_id == "floor_2"
        assert result.hazard_change == 5

    def test_descend_stairs_failure_blocked(self):
        """階段降下失敗（ボス未クリア）テスト"""
        self.manager.current_floor_id = "floor_10"
        self.manager.current_depth = 10
        floor_10 = self.manager.floors["floor_10"]
        floor_10.cleared = False

        result = self.manager.descend_stairs()
        assert result.success is False
        assert "ボスを倒すか、出口がありません" in result.message

    def test_ascend_stairs_success(self):
        """階段上昇成功テスト"""
        self.manager.current_floor_id = "floor_2"
        self.manager.current_depth = 2
        result = self.manager.ascend_stairs()
        assert result.success is True
        assert result.transition_type == FloorTransitionType.STAIRS_UP
        assert self.manager.current_depth == 1
        assert result.hazard_change == -10

    def test_use_elevator_success(self):
        """エレベーター移動成功テスト"""
        floor_1 = self.manager.floors["floor_1"]
        floor_1.exit_to_next = {"type": "elevator", "target_floor": "floor_5"}

        result = self.manager.use_elevator(target_depth=5)
        assert result.success is True
        assert result.transition_type == FloorTransitionType.ELEVATOR
        assert self.manager.current_depth == 5
        assert result.hazard_change == 0

    def test_emergency_escape(self):
        """緊急脱出テスト"""
        self.manager.initialize_dungeon(max_depth=50)
        self.manager.current_floor_id = "floor_50"
        self.manager.current_depth = 50
        floor_50 = self.manager.floors["floor_50"]
        floor_50.hazard_level = 80

        result = self.manager.emergency_escape()
        assert result.success is True
        assert result.transition_type == FloorTransitionType.EMERGENCY_SHAFT
        assert self.manager.current_depth == 1
        assert self.manager.current_floor_id == "floor_1"
        assert self.manager.floors["floor_1"].hazard_level == 0


class TestPresentationIntegration:
    """Step 70: 演出統合テスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)
        self.manager.initialize_dungeon(max_depth=5)

    def test_stairs_down_sounds_and_emotes(self):
        """階段降下時の音声・エモートテスト"""
        self.presentation.event_queue.clear()
        self.audio.played_sounds.clear()

        result = self.manager.descend_stairs()

        # stair_creak.ogg x3 + floor_transition_woosh.ogg
        assert self.audio.played_sounds.count("stair_creak.ogg") == 3
        assert "floor_transition_woosh.ogg" in self.audio.played_sounds

        # emote_arrow_down.png イベントが追加されている
        events = self.presentation.get_and_clear_events()
        assert len(events) >= 1
        assert events[0].emote_file == "emote_arrow_down.png"

    def test_stairs_up_sounds_and_emotes(self):
        """階段上昇時の音声・エモートテスト"""
        self.manager.current_floor_id = "floor_2"
        self.manager.current_depth = 2
        self.presentation.event_queue.clear()
        self.audio.played_sounds.clear()

        result = self.manager.ascend_stairs()

        assert self.audio.played_sounds.count("stair_creak.ogg") == 3
        assert "floor_transition_woosh.ogg" in self.audio.played_sounds

        events = self.presentation.get_and_clear_events()
        assert events[0].emote_file == "emote_arrow_up.png"

    def test_elevator_sounds_and_emotes(self):
        """エレベーター時の音声・エモートテスト"""
        floor_1 = self.manager.floors["floor_1"]
        floor_1.exit_to_next = {"type": "elevator", "target_floor": "floor_3"}

        self.presentation.event_queue.clear()
        self.audio.played_sounds.clear()

        result = self.manager.use_elevator(target_depth=3)

        assert "elevator_hum.ogg" in self.audio.played_sounds
        assert "floor_transition_woosh.ogg" in self.audio.played_sounds

        events = self.presentation.get_and_clear_events()
        assert events[0].emote_file in ("emote_arrow_down.png", "emote_arrow_up.png")
        assert events[0].vr_grid_effect is True

    def test_emergency_escape_sounds_and_emotes(self):
        """緊急脱出時の音声・エモートテスト"""
        self.manager.current_floor_id = "floor_10"
        self.manager.current_depth = 10
        self.presentation.event_queue.clear()
        self.audio.played_sounds.clear()

        result = self.manager.emergency_escape()

        assert "warp.ogg" in self.audio.played_sounds
        assert "floor_transition_woosh.ogg" in self.audio.played_sounds

        events = self.presentation.get_and_clear_events()
        assert events[0].emote_file == "emote_exclamation.png"
        assert events[0].vr_grid_effect is True


class TestHazardSystem:
    """ハザードシステムテスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)
        self.manager.initialize_dungeon(max_depth=10)

    def test_hazard_level_clamping(self):
        """ハザードレベル 0-100 クランプテスト"""
        floor = self.manager.get_current_floor()
        floor.hazard_level = 95
        self.manager.update_hazard_level(10)
        assert floor.hazard_level == 100

        floor.hazard_level = 5
        self.manager.update_hazard_level(-10)
        assert floor.hazard_level == 0

    def test_hazard_debuffs_thresholds(self):
        """ハザードデバフ閾値テスト"""
        floor = self.manager.get_current_floor()

        floor.hazard_level = 20
        assert self.manager.get_hazard_debuffs() == []

        floor.hazard_level = 30
        debuffs = self.manager.get_hazard_debuffs()
        assert "Concept Leaking: MP Cost +20%" in debuffs
        assert len(debuffs) == 1

        floor.hazard_level = 60
        debuffs = self.manager.get_hazard_debuffs()
        assert len(debuffs) == 2

        floor.hazard_level = 90
        debuffs = self.manager.get_hazard_debuffs()
        assert len(debuffs) == 3
        assert "Total Reality Breakdown: Continuous HP Erosion" in debuffs

    def test_check_map_mutation(self):
        """マップ構造変化トリガーテスト"""
        floor = self.manager.get_current_floor()
        floor.hazard_level = 40
        assert self.manager.check_map_mutation() is None

        floor.hazard_level = 50
        assert floor.exit_to_next is not None
        result = self.manager.check_map_mutation()
        assert "Spatial collapse" in result
        assert floor.exit_to_next is None


class TestSerialization:
    """Step 71-72: シリアライズ/デシリアライズ・E2Eテスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)

    def test_save_load_roundtrip(self):
        """セーブ/ロード ラウンドトリップテスト"""
        self.manager.initialize_dungeon(max_depth=5)
        self.manager.descend_stairs()
        self.manager.descend_stairs()
        self.manager.floors["floor_3"].hazard_level = 30
        self.manager.floors["floor_3"].cleared = True

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            self.manager.save_to_file(temp_path)

            # ロード
            loaded = SkillEaterDungeonFloorManager.load_from_file(temp_path)

            assert loaded.current_floor_id == self.manager.current_floor_id
            assert loaded.current_depth == self.manager.current_depth
            assert len(loaded.floors) == len(self.manager.floors)
            assert loaded.floors["floor_3"].hazard_level == 30
            assert loaded.floors["floor_3"].cleared is True
            assert len(loaded.transition_history) == len(self.manager.transition_history)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_e2e_scenario(self):
        """E2Eシナリオテスト: 初期化→探索→ボス撃破→降下→エレベーター→脱出→セーブ/ロード"""
        self.manager.initialize_dungeon(max_depth=20)

        # 1. 深度1探索
        assert self.manager.current_depth == 1
        assert self.manager.get_current_floor().theme == DungeonTheme.INDUSTRIAL_RUINS

        # 2. ボスフロア(10)まで降下
        for _ in range(9):
            result = self.manager.descend_stairs()
            assert result.success is True

        assert self.manager.current_depth == 10
        assert self.manager.get_current_floor().theme == DungeonTheme.INDUSTRIAL_RUINS

        # 3. ボス撃破・フロアクリア
        floor_10 = self.manager.get_current_floor()
        floor_10.cleared = True
        clear_result = self.manager.clear_current_floor()
        assert clear_result.success is True
        assert clear_result.concept_shards > 0

        # 4. 階段で深度16へ（テーマ遷移: INDUSTRIAL_RUINS -> NEON_SEWERS）
        for _ in range(6):  # 11->12->13->14->15->16
            result = self.manager.descend_stairs()
            assert result.success is True

        assert self.manager.current_depth == 16
        assert self.manager.get_current_floor().theme == DungeonTheme.NEON_SEWERS

        # 5. エレベーターで深度15へ
        floor_11 = self.manager.get_current_floor()
        floor_11.exit_to_next = {"type": "elevator", "target_floor": "floor_15"}
        result = self.manager.use_elevator(target_depth=15)
        assert result.success is True
        assert self.manager.current_depth == 15
        assert self.manager.get_current_floor().theme == DungeonTheme.INDUSTRIAL_RUINS  # 15はまだINDUSTRIAL

        # 6. エレベーターで深度20へ（テーマ遷移）
        floor_15 = self.manager.get_current_floor()
        floor_15.exit_to_next = {"type": "elevator", "target_floor": "floor_20"}
        result = self.manager.use_elevator(target_depth=20)
        assert result.success is True
        assert self.manager.current_depth == 20
        assert self.manager.get_current_floor().theme == DungeonTheme.NEON_SEWERS

        # 7. 緊急脱出
        result = self.manager.emergency_escape()
        assert result.success is True
        assert self.manager.current_depth == 1

        # 8. セーブ/ロード
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            self.manager.save_to_file(temp_path)
            loaded = SkillEaterDungeonFloorManager.load_from_file(temp_path)

            assert loaded.current_depth == 1
            assert loaded.current_floor_id == "floor_1"
            assert len(loaded.transition_history) > 0
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestExplorationIntegration:
    """Step 71: ExplorationSystem 統合テスト"""

    def setup_method(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        SkillEaterDungeonFloorManager.reset_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(is_mock_only=True)
        self.manager = SkillEaterDungeonFloorManager(audio=self.audio, presentation=self.presentation)
        self.manager.initialize_dungeon(max_depth=5)

    def test_try_descend_returns_exploration_result(self):
        """try_descend が ExplorationResult を返すか"""
        result = self.manager.try_descend()
        from skill_eater_exploration_system import ExplorationResult
        assert isinstance(result, ExplorationResult)
        assert result.action_type in ("MOVE_FLOOR", "MOVE_ROOM")
        assert result.current_room_id != ""

    def test_try_ascend_returns_exploration_result(self):
        """try_ascend が ExplorationResult を返すか"""
        self.manager.current_floor_id = "floor_2"
        self.manager.current_depth = 2
        result = self.manager.try_ascend()
        from skill_eater_exploration_system import ExplorationResult
        assert isinstance(result, ExplorationResult)

    def test_try_elevator_returns_exploration_result(self):
        """try_elevator が ExplorationResult を返すか"""
        floor_1 = self.manager.floors["floor_1"]
        floor_1.exit_to_next = {"type": "elevator", "target_floor": "floor_3"}
        result = self.manager.try_elevator(target_depth=3)
        from skill_eater_exploration_system import ExplorationResult
        assert isinstance(result, ExplorationResult)

    def test_get_floor_info(self):
        """get_floor_info が正しい情報を返すか"""
        info = self.manager.get_floor_info()
        assert info["floor_id"] == "floor_1"
        assert info["depth"] == 1
        assert info["theme"] == "industrial_ruins"
        assert "hazard_level" in info
        assert "hazard_debuffs" in info
        assert "exit_type" in info

    def test_get_available_transitions(self):
        """get_available_transitions が正しい遷移タイプを返すか"""
        transitions = self.manager.get_available_transitions()
        assert FloorTransitionType.EMERGENCY_SHAFT in transitions
        # floor_1 では descend が可能
        assert FloorTransitionType.STAIRS_DOWN in transitions
        # floor_1 では ascend 不可能
        assert FloorTransitionType.STAIRS_UP not in transitions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
