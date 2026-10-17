"""
Unit tests for SkillEaterSecretAccess - Detection System (Step 24)
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from secret_area_system import (
    KeyItem,
    SecretArea,
    SecretAreaRegistry,
    _check_access_condition,
    _check_key_requirement,
    _grant_rewards,
    check_secret_detection,
    perception_check,
    try_unlock_secret,
)
from skill_eater_system import CharacterState, SkillDef, SkillEaterRegistry, SkillTier, SkillType


class MockGameMap:
    """テスト用モックゲームマップ"""
    def __init__(self):
        self.tiles = [["TILE_WALL" for _ in range(80)] for _ in range(120)]
        self.hidden_tiles = {}
        self.width = 120
        self.height = 80

    def is_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


class TestPerceptionCheck(unittest.TestCase):
    """知覚判定テスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player",
            name="TestPlayer",
            hp=100, max_hp=100,
            mp=50, max_mp=50,
            atk=10, defense=5,
            intelligence=10, speed=100,
            perception=15,
            analysis_level=3,
        )

    def test_perception_check_success_high_stats(self):
        """高ステータスで成功"""
        with patch('secret_area_system.random.randint', return_value=50):
            success, margin = perception_check(self.player, 20, 0)
            self.assertTrue(success)
            self.assertGreater(margin, 0)

    def test_perception_check_failure_low_stats(self):
        """低ステータスで失敗"""
        weak_player = CharacterState(
            id="weak", name="Weak", hp=50, max_hp=50, mp=20, max_mp=20,
            atk=5, defense=2, intelligence=5, speed=80,
            perception=5, analysis_level=1,
        )
        with patch('secret_area_system.random.randint', return_value=10):
            success, margin = perception_check(weak_player, 30, 0)
            self.assertFalse(success)
            self.assertEqual(margin, 0)

    def test_perception_check_with_skill_bonus(self):
        """スキルボーナス込みで判定"""
        with patch('secret_area_system.random.randint', return_value=30):
            success, margin = perception_check(self.player, 25, 10)  # スキルボーナス+10
            self.assertTrue(success)

    def test_perception_check_failure_penalty(self):
        """連続失敗ペナルティ適用"""
        self.player.failed_search_count = 3  # ペナルティ+6
        with patch('secret_area_system.random.randint', return_value=30):
            success, margin = perception_check(self.player, 20, 0)
            # ペナルティ込みで target = 20 + 6 = 26
            # effective = 15*2 + 3*3 = 39
            # roll + effective = 30 + 39 = 69 >= 26 -> success
            self.assertTrue(success)


class TestSecretAreaRegistry(unittest.TestCase):
    """SecretAreaRegistryテスト"""

    def setUp(self):
        self.registry = SecretAreaRegistry()
        # テスト用データを直接追加
        self.test_area = SecretArea(
            id="test_secret_01",
            name="テスト隠し部屋",
            layer_key="underground:ruins:15:material",
            secret_type="hidden_door",
            position=(50, 30),
            detection_difficulty=20,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={},
            emotes={},
        )
        self.registry._secret_areas["test_secret_01"] = self.test_area
        self.registry._areas_by_layer["underground:ruins:15:material"] = [self.test_area]

    def test_get_secret_area(self):
        area = self.registry.get_secret_area("test_secret_01")
        self.assertIsNotNone(area)
        self.assertEqual(area.name, "テスト隠し部屋")

    def test_get_areas_in_layer(self):
        areas = self.registry.get_areas_in_layer("underground:ruins:15:material")
        self.assertEqual(len(areas), 1)
        self.assertEqual(areas[0].id, "test_secret_01")

    def test_get_key_item(self):
        test_key = KeyItem(
            id="test_keycard",
            name="テストキーカード",
            key_type="keycard",
            level=2,
            consumable=False,
        )
        self.registry._key_items["test_keycard"] = test_key
        key = self.registry.get_key_item("test_keycard")
        self.assertIsNotNone(key)
        self.assertEqual(key.level, 2)


class TestCheckSecretDetection(unittest.TestCase):
    """秘密検知テスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player",
            name="TestPlayer",
            hp=100, max_hp=100,
            mp=50, max_mp=50,
            atk=10, defense=5,
            intelligence=15, speed=100,
            perception=20,
            analysis_level=3,
        )
        self.game_map = MockGameMap()
        self.layer_key = "underground:ruins:15:material"

        # レジストリにテストエリア追加
        self.registry = SecretAreaRegistry()
        self.test_area = SecretArea(
            id="test_detect_01",
            name="検知テストエリア",
            layer_key=self.layer_key,
            secret_type="hidden_door",
            position=(10, 10),
            detection_difficulty=15,
            access_conditions=[],
            key_required=None,
            rewards=[],
            audio={"detect": "perception_success"},
            emotes={"detect": "emote_eye.png"},
        )
        self.registry._secret_areas["test_detect_01"] = self.test_area
        self.registry._areas_by_layer[self.layer_key] = [self.test_area]

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_check_secret_detection_success(self, mock_registry):
        """検知成功"""
        # モックレジストリにエリア設定
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._areas_by_layer = self.registry._areas_by_layer

        # プレイヤーをエリアの近くに配置
        self.player.x, self.player.y = 11, 11

        with patch('secret_area_system.random.randint', return_value=50):
            discovered = check_secret_detection(self.player, self.game_map, self.layer_key)
            self.assertEqual(len(discovered), 1)
            self.assertEqual(discovered[0].id, "test_detect_01")
            self.assertTrue(self.test_area.is_discovered)
            self.assertIn("test_detect_01", self.player.discovered_secrets)

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_check_secret_detection_too_far(self, mock_registry):
        """距離が遠くて検知されない"""
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._areas_by_layer = self.registry._areas_by_layer

        # プレイヤーを遠くに配置
        self.player.x, self.player.y = 50, 50

        discovered = check_secret_detection(self.player, self.game_map, self.layer_key)
        self.assertEqual(len(discovered), 0)
        self.assertFalse(self.test_area.is_discovered)

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_check_secret_detection_already_discovered(self, mock_registry):
        """既に発見済みならスキップ"""
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._areas_by_layer = self.registry._areas_by_layer

        self.player.x, self.player.y = 11, 11
        self.player.discovered_secrets.add("test_detect_01")

        discovered = check_secret_detection(self.player, self.game_map, self.layer_key)
        self.assertEqual(len(discovered), 0)


class TestAccessConditions(unittest.TestCase):
    """アクセス条件チェックテスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player", name="TestPlayer",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=5, intelligence=10, speed=100,
        )
        self.player.faction_reputation = {"resistance": 40, "broker": 10}
        self.player.story_variables = {"unlocked_archive_access": True}
        self.player.add_skill("rar_utility_003")

    def test_faction_rep_success(self):
        """派閥評判条件成功"""
        cond = {"type": "faction_rep", "faction": "resistance", "min_rep": 30}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertTrue(ok)

    def test_faction_rep_failure(self):
        """派閥評判条件失敗"""
        cond = {"type": "faction_rep", "faction": "resistance", "min_rep": 50}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertFalse(ok)
        self.assertIn("評判が足りません", msg)

    def test_skill_required_success(self):
        """スキル保有条件成功"""
        cond = {"type": "skill_required", "skill_id": "rar_utility_003"}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertTrue(ok)

    def test_skill_required_failure(self):
        """スキル保有条件失敗"""
        cond = {"type": "skill_required", "skill_id": "rar_utility_999"}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertFalse(ok)
        self.assertIn("習得していません", msg)

    def test_quest_flag_success(self):
        """クエストフラグ条件成功"""
        cond = {"type": "quest_flag", "quest_flag": "unlocked_archive_access"}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertTrue(ok)

    def test_quest_flag_failure(self):
        """クエストフラグ条件失敗"""
        cond = {"type": "quest_flag", "quest_flag": "not_unlocked"}
        ok, msg = _check_access_condition(self.player, cond)
        self.assertFalse(ok)
        self.assertIn("立っていません", msg)


class TestKeyRequirements(unittest.TestCase):
    """鍵要件チェックテスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player", name="TestPlayer",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=5, intelligence=10, speed=100,
        )

        # レジストリに鍵追加
        self.registry = SecretAreaRegistry()
        self.registry._key_items["keycard_lv2"] = KeyItem(
            id="keycard_lv2", name="キーカードLv2", key_type="keycard", level=2, consumable=False
        )
        self.registry._key_items["biometric_fingerprint"] = KeyItem(
            id="biometric_fingerprint", name="指紋キー", key_type="biometric", subtype="fingerprint", consumable=True
        )
        self.registry._key_items["decryption_module_basic"] = KeyItem(
            id="decryption_module_basic", name="暗号解除基礎", key_type="decryption", level=1, consumable=True
        )
        self.registry._key_items["physical_key_ancient"] = KeyItem(
            id="physical_key_ancient", name="古代の鍵", key_type="physical", consumable=False
        )

    def test_keycard_success(self):
        """キーカード条件成功"""
        self.player.owned_keys["keycard_lv2"] = 1
        key_req = {"type": "keycard", "level": 2, "consumable": False}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertTrue(ok)
        self.assertEqual(key_id, "keycard_lv2")

    def test_keycard_failure_insufficient_level(self):
        """キーカードレベル不足"""
        self.player.owned_keys["keycard_lv1"] = 1
        key_req = {"type": "keycard", "level": 2, "consumable": False}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertFalse(ok)
        self.assertIn("Lv.2 以上", msg)

    def test_biometric_success(self):
        """生体認証成功"""
        self.player.owned_keys["biometric_fingerprint"] = 1
        key_req = {"type": "biometric", "subtype": "fingerprint", "consumable": True}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertTrue(ok)
        self.assertEqual(key_id, "biometric_fingerprint")

    def test_biometric_failure(self):
        """生体認証失敗"""
        key_req = {"type": "biometric", "subtype": "retina", "consumable": True}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertFalse(ok)
        self.assertIn("生体認証キー", msg)

    def test_decryption_success(self):
        """暗号解除成功"""
        self.player.owned_keys["decryption_module_basic"] = 1
        key_req = {"type": "decryption", "level": 1, "consumable": True}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertTrue(ok)

    def test_physical_key_success(self):
        """物理鍵成功"""
        self.player.owned_keys["physical_key_ancient"] = 1
        key_req = {"type": "physical", "key_id": "physical_key_ancient", "consumable": False}
        ok, msg, key_id = _check_key_requirement(self.player, key_req)
        self.assertTrue(ok)
        self.assertEqual(key_id, "physical_key_ancient")


class TestTryUnlockSecret(unittest.TestCase):
    """秘密解除テスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player", name="TestPlayer",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=5, intelligence=15, speed=100,
            perception=20, analysis_level=3,
        )
        self.player.faction_reputation = {"resistance": 40}
        self.player.add_skill("rar_utility_003")
        self.player.owned_keys["keycard_lv2"] = 1

        self.game_map = MockGameMap()

        self.registry = SecretAreaRegistry()
        self.test_area = SecretArea(
            id="test_unlock_01",
            name="解除テストエリア",
            layer_key="underground:ruins:15:material",
            secret_type="hidden_door",
            position=(20, 20),
            detection_difficulty=15,
            access_conditions=[
                {"type": "faction_rep", "faction": "resistance", "min_rep": 30},
                {"type": "skill_required", "skill_id": "rar_utility_003"},
            ],
            key_required={"type": "keycard", "level": 2, "consumable": False},
            rewards=[
                {"type": "forbidden_skill", "skill_id": "eat_forbidden_001"},
                {"type": "lore", "text": "テストロア"},
            ],
            audio={"unlock": "secret_wall_slide"},
            emotes={"unlock": "emote_key.png"},
        )
        self.registry._secret_areas["test_unlock_01"] = self.test_area

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_try_unlock_secret_success(self, mock_registry):
        """解除成功"""
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._key_items = self.registry._key_items

        self.test_area.is_discovered = True
        self.player.discovered_secrets.add("test_unlock_01")

        success, msg = try_unlock_secret(self.player, self.test_area, self.game_map)
        self.assertTrue(success)
        self.assertTrue(self.test_area.is_unlocked)
        self.assertIn("test_unlock_01", self.player.unlocked_secrets)
        self.assertIn("解放されました", msg)

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_try_unlock_secret_not_discovered(self, mock_registry):
        """未発見で失敗"""
        mock_registry._secret_areas = self.registry._secret_areas

        success, msg = try_unlock_secret(self.player, self.test_area, self.game_map)
        self.assertFalse(success)
        self.assertIn("発見されていません", msg)

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_try_unlock_secret_missing_faction(self, mock_registry):
        """派閥評判不足で失敗"""
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._key_items = self.registry._key_items

        self.test_area.is_discovered = True
        self.player.discovered_secrets.add("test_unlock_01")
        self.player.faction_reputation = {"resistance": 10}  # 不足

        success, msg = try_unlock_secret(self.player, self.test_area, self.game_map)
        self.assertFalse(success)
        self.assertIn("評判が足りません", msg)

    @patch('secret_area_system.SECRET_REGISTRY', new_callable=lambda: SecretAreaRegistry())
    def test_try_unlock_secret_consumable_key(self, mock_registry):
        """消費型キーが消費される"""
        mock_registry._secret_areas = self.registry._secret_areas
        mock_registry._key_items = self.registry._key_items

        self.test_area.key_required = {"type": "biometric", "subtype": "fingerprint", "consumable": True}
        self.player.owned_keys["biometric_fingerprint"] = 1
        self.test_area.is_discovered = True
        self.player.discovered_secrets.add("test_unlock_01")

        success, msg = try_unlock_secret(self.player, self.test_area, self.game_map)
        self.assertTrue(success)
        self.assertEqual(self.player.owned_keys.get("biometric_fingerprint", 0), 0)


class TestRewards(unittest.TestCase):
    """報酬付与テスト"""

    def setUp(self):
        self.player = CharacterState(
            id="test_player", name="TestPlayer",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=5, intelligence=10, speed=100,
        )

        # スキルレジストリに禁忌スキル追加
        self.skill_registry = SkillEaterRegistry.get_instance()
        self.skill_registry._skills["eat_forbidden_001"] = SkillDef(
            id="eat_forbidden_001", name="禁忌スキルテスト", tier=SkillTier.UNIQUE,
            type=SkillType.ACTIVE, is_illegal=True, memory_usage=2,
        )

    def test_grant_forbidden_skill(self):
        """禁忌スキル付与"""
        area = SecretArea(
            id="reward_test", name="報酬テスト",
            layer_key="test", secret_type="hidden_door", position=(0,0),
            detection_difficulty=10, access_conditions=[], key_required=None,
            rewards=[{"type": "forbidden_skill", "skill_id": "eat_forbidden_001"}],
            audio={}, emotes={},
        )
        msgs = _grant_rewards(self.player, area)
        self.assertTrue(self.player.has_skill("eat_forbidden_001"))
        self.assertIn("禁忌スキル", msgs[0])

    def test_grant_lore(self):
        """ロア付与"""
        area = SecretArea(
            id="reward_test", name="報酬テスト",
            layer_key="test", secret_type="hidden_door", position=(0,0),
            detection_difficulty=10, access_conditions=[], key_required=None,
            rewards=[{"type": "lore", "text": "古代の記録"}],
            audio={}, emotes={},
        )
        msgs = _grant_rewards(self.player, area)
        self.assertEqual(len(self.player.discovered_lore), 1)
        self.assertEqual(self.player.discovered_lore[0]["text"], "古代の記録")
        self.assertIn("ロアを発見", msgs[0])


class TestSecretAreaHint(unittest.TestCase):
    """ヒントテキスト生成テスト"""

    def test_get_hint_text_faction(self):
        area = SecretArea(
            id="hint_test", name="ヒントテスト",
            layer_key="test", secret_type="hidden_door", position=(0,0),
            detection_difficulty=10,
            access_conditions=[
                {"type": "faction_rep", "faction": "resistance", "min_rep": 30},
            ],
            key_required={"type": "keycard", "level": 2, "consumable": False},
            rewards=[], audio={}, emotes={},
        )
        hint = area.get_hint_text()
        self.assertIn("resistance", hint)
        self.assertIn("30", hint)
        self.assertIn("キーカード Lv.2", hint)


if __name__ == "__main__":
    unittest.main()
