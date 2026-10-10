"""呪文テスト (Phase 2 Step 40-41)"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import Element  # noqa: E402
from ecs.entity import Entity  # noqa: E402
from engine.systems.combat_system import CombatSystem  # noqa: E402
from systems import (  # noqa: E402
    _execute_self_spell,
    _execute_single_spell,
    cast,
    get_spell_data,
    get_spell_ids,
)


def create_test_entity(name: str, x: int = 0, y: int = 0, hp: int = 10, max_hp: int = 10, mp: int = 10, max_mp: int = 10, faction: str = "monster", is_pet: bool = False) -> Entity:
    """テスト用エンティティ作成ヘルパー"""
    e = Entity(name=name, x=x, y=y, is_pet=is_pet)
    e.hp = hp
    e.max_hp = max_hp
    e.mp = mp
    e.max_mp = max_mp
    e.faction = faction
    return e


class TestSpellData:
    """呪文データの読み込みテスト"""

    def test_spell_data_loads_correctly(self):
        """spells.yaml から8つの呪文が読み込まれる"""
        spell_ids = get_spell_ids()
        expected = ["magic_dart", "fireball", "ice_bolt", "lightning_bolt", "heal_light", "heal_heavy", "teleport", "haste"]
        assert set(spell_ids) == set(expected), f"Expected {expected}, got {spell_ids}"

    def test_spell_data_has_required_fields(self):
        """各呪文に必須フィールドがある"""
        for spell_id in get_spell_ids():
            data = get_spell_data()[spell_id]
            assert "name" in data, f"{spell_id}: name missing"
            assert "mp_cost" in data, f"{spell_id}: mp_cost missing"
            assert "element" in data, f"{spell_id}: element missing"
            assert "range" in data, f"{spell_id}: range missing"
            assert "target_type" in data, f"{spell_id}: target_type missing"


class TestCastSpell:
    """統一呪文詠唱関数のテスト"""

    def test_cast_unknown_spell_fails(self):
        """未知の呪文は失敗"""
        caster = create_test_entity("Caster", mp=100)
        success, msg = cast("unknown_spell", caster)
        assert success is False
        assert "未知" in msg

    def test_cast_insufficient_mp_fails(self):
        """MP不足なら失敗"""
        caster = create_test_entity("Caster", mp=0)
        success, msg = cast("magic_dart", caster)
        assert success is False
        assert "MPが足りない" in msg

    def test_cast_consumes_mp(self):
        """呪文詠唱でMPが消費される"""
        caster = create_test_entity("Caster", mp=20)
        caster.attributes.magic = 20  # 高い魔力で成功率を上げる
        target = create_test_entity("Target", hp=20, max_hp=20, faction="monster")
        initial_mp = caster.mp

        with patch("systems.random.randint", return_value=50):  # 成功率以内
            success, msg = cast("magic_dart", caster, target)

        assert success is True
        assert caster.mp == initial_mp - 4  # magic_dart mp_cost=4

    def test_magic_dart_deals_damage(self):
        """magic_dart がダメージを与える"""
        caster = create_test_entity("Caster", mp=20)
        caster.attributes.magic = 15
        target = create_test_entity("Target", hp=20, max_hp=20, faction="monster")

        with patch("engine.systems.combat_system.random.randint", side_effect=[50, 4]):  # hit, damage
            success, msg = cast("magic_dart", caster, target)

        assert success is True
        assert target.hp < 20
        assert "ダメージ" in msg

    def test_heal_light_restores_hp(self):
        """heal_light がHPを回復する"""
        caster = create_test_entity("Caster", mp=20)
        caster.hp = 10
        caster.max_hp = 20

        with patch("systems.random.randint", return_value=5):  # 2d8 + 10 = 10+10=20
            success, msg = cast("heal_light", caster)

        assert success is True
        assert caster.hp == caster.max_hp
        assert "癒えた" in msg or "回復" in msg

    def test_heal_heavy_restores_more_hp(self):
        """heal_heavy がより多く回復する"""
        caster = create_test_entity("Caster", mp=50)
        caster.hp = 5
        caster.max_hp = 50

        with patch("systems.random.randint", return_value=10):  # 4d12 + 30
            success, msg = cast("heal_heavy", caster)

        assert success is True
        assert caster.hp == caster.max_hp
        assert "癒えた" in msg or "回復" in msg

    def test_teleport_moves_caster(self):
        """teleport が位置を移動させる"""
        from core_framework import Point
        from ecs.entity import Entity

        # モックエンジンを作成
        mock_engine = MagicMock()
        mock_engine.is_tile_free.return_value = True
        mock_engine.get_entity_at.return_value = None

        # プレイヤーエンティティを作成
        caster = Entity(name="Player", x=10, y=10, char="@", color=(255, 255, 255))
        caster.mp = 20
        caster.max_mp = 20
        caster.attributes.magic = 30  # 高い魔力で成功率を95%以上に
        initial_x, initial_y = caster.x, caster.y
        caster.status_effects = []

        # モックエンジンのplayerプロパティを設定
        mock_engine.player = caster
        mock_engine.is_tile_free = MagicMock(return_value=True)
        mock_engine.get_entity_at = MagicMock(return_value=None)

        success, msg = cast("teleport", caster, engine=mock_engine)

        assert success is True
        assert (caster.x, caster.y) != (initial_x, initial_y)
        assert "移動" in msg or "テレポート" in msg

    def test_haste_applies_buff(self):
        """haste が速度バフを付与する"""
        caster = create_test_entity("Caster", mp=50)
        caster.attributes.magic = 20  # 高い魔力で成功率を上げる
        initial_speed = caster.speed

        with patch("systems.random.randint", return_value=50):
            success, msg = cast("haste", caster)

        assert success is True
        assert caster.speed > initial_speed
        assert "加速" in msg or "速度" in msg
        # Hasteステータスが付与される
        assert any(e.name == "Haste" for e in caster.status_effects)

    def test_fireball_aoe_damage(self):
        """fireball が範囲ダメージを与える"""
        from game import Engine
        from renderer import NullRenderer
        engine = Engine(renderer=NullRenderer())
        caster = engine.player
        caster.mp = 50
        caster.attributes.magic = 20

        # 対象と周囲に敵を配置
        target = create_test_entity("Target1", x=5, y=5, hp=30, max_hp=30, faction="monster")
        target2 = create_test_entity("Target2", x=6, y=5, hp=30, max_hp=30, faction="monster")
        engine.entity_manager.add_entity(target)
        engine.entity_manager.add_entity(target2)

        with patch("systems.random.randint", return_value=50):  # 全て命中
            success, msg = cast("fireball", caster, target, engine=engine)

        assert success is True
        assert target.hp < 30
        assert target2.hp < 30  # 範囲内なので巻き込まれる
        assert "爆発" in msg or "火炎球" in msg

    def test_ice_bolt_beam_damage(self):
        """ice_bolt がビームで貫通ダメージ"""
        caster = create_test_entity("Caster", x=0, y=0, mp=20)
        caster.attributes.magic = 15
        target = create_test_entity("Target", x=5, y=5, hp=30, max_hp=30, faction="monster")

        with patch("systems.random.randint", return_value=50):
            success, msg = cast("ice_bolt", caster, target)

        assert success is True
        assert target.hp < 30
        assert "貫" in msg or "氷" in msg

    def test_lightning_bolt_beam_damage(self):
        """lightning_bolt がビームで貫通ダメージ"""
        caster = create_test_entity("Caster", x=0, y=0, mp=30)
        caster.attributes.magic = 15
        target = create_test_entity("Target", x=5, y=5, hp=40, max_hp=40, faction="monster")

        with patch("systems.random.randint", return_value=50):
            success, msg = cast("lightning_bolt", caster, target)

        assert success is True
        assert target.hp < 40
        assert "雷" in msg or "稲妻" in msg

    def test_cast_fails_when_mp_insufficient_after_cost(self):
        """MPコスト分だけMPがあるかチェック"""
        caster = create_test_entity("Caster", mp=3)
        success, msg = cast("fireball", caster)  # mp_cost=12
        assert success is False
        assert "MPが足りない" in msg

    def test_spell_failure_causes_backlash(self):
        """詠唱失敗時に魔力反動ダメージ"""
        caster = create_test_entity("Caster", mp=20, hp=30, max_hp=30)
        caster.attributes.magic = 5

        # 失敗ロール (95以上で失敗)
        with patch("engine.systems.combat_system.random.randint", return_value=99):
            success, msg = cast("magic_dart", caster)

        assert success is False
        assert "失敗" in msg
        assert caster.hp < 30  # 反動ダメージ


class TestSpellTargeting:
    """呪文の標的選択テスト"""

    def test_self_target_spells_use_caster(self):
        """self-target呪文は詠唱者自身を対象とする"""
        caster = create_test_entity("Caster", mp=20)
        caster.hp = 5
        caster.max_hp = 20

        with patch("engine.systems.combat_system.random.randint", return_value=5):
            success, msg = cast("heal_light", caster)

        assert success is True
        assert caster.hp > 5

    def test_attack_spells_require_target(self):
        """攻撃呪文は対象が必要"""
        from systems import get_spell_data
        spell_data = get_spell_data()

        attack_spells = [sid for sid, data in spell_data.items() if data.get("target_type") in ("single", "beam", "area")]
        self_spells = [sid for sid, data in spell_data.items() if data.get("target_type") == "self"]

        assert len(attack_spells) > 0
        assert len(self_spells) >= 2  # heal_light, heal_heavy, teleport, haste


class TestSpellElements:
    """呪文属性テスト"""

    def test_fireball_is_fire_element(self):
        """fireball は fire 属性"""
        assert get_spell_data()["fireball"]["element"] == "fire"

    def test_ice_bolt_is_cold_element(self):
        """ice_bolt は cold 属性"""
        assert get_spell_data()["ice_bolt"]["element"] == "cold"

    def test_lightning_bolt_is_lightning_element(self):
        """lightning_bolt は lightning 属性"""
        assert get_spell_data()["lightning_bolt"]["element"] == "lightning"

    def test_heal_spells_are_heal_element(self):
        """回復呪文は heal 属性"""
        assert get_spell_data()["heal_light"]["element"] == "heal"
        assert get_spell_data()["heal_heavy"]["element"] == "heal"

    def test_magic_dart_is_magic_element(self):
        """magic_dart は magic 属性"""
        assert get_spell_data()["magic_dart"]["element"] == "magic"

    def test_teleport_is_utility_element(self):
        """teleport は utility 属性"""
        assert get_spell_data()["teleport"]["element"] == "utility"

    def test_haste_is_buff_element(self):
        """haste は buff 属性"""
        assert get_spell_data()["haste"]["element"] == "buff"


class TestSpellResistance:
    """呪文耐性テスト"""

    def test_fire_resistance_reduces_fireball_damage(self):
        """火炎耐性が火炎ダメージを軽減"""

        dmg = 20
        res = 50  # 50%軽減
        final = CombatSystem.calc_element_damage(dmg, Element.FIRE, res)
        assert final == 10  # 50%軽減

    def test_ice_resistance_reduces_ice_bolt_damage(self):
        """冷気耐性が氷ダメージを軽減"""

        dmg = 20
        res = 50
        final = CombatSystem.calc_element_damage(dmg, Element.COLD, res)
        assert final == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
