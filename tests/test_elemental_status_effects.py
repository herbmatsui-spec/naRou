"""
Unit and integration tests for Elemental Weakness, Resistances, and ECS Status Effects (Phase 3, Steps 69-71).
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from naRou.constants import (
    Element,
    STATUS_BURN,
    STATUS_FREEZE,
    STATUS_PARALYZE,
    STATUS_POISON,
)
from naRou.ecs.components import StatusEffectsComponent
from naRou.ecs.entity import Attributes, Entity
from naRou.item_system import Item, use_item
from naRou.systems import CombatSystem


class TestElementalAndStatusEffects:
    """フェーズ3のテストスイート"""

    def test_status_effects_component_lifecycle(self):
        """ECSコンポーネントとしての状態異常付与・持続・解除 (Step 54, 70)"""
        entity = Entity(name="テスト勇者", is_player=True)
        assert entity.has_component(StatusEffectsComponent)
        assert not entity.has_status(STATUS_POISON)

        # 毒付与
        added = entity.add_status(STATUS_POISON, duration=3, power=5, source_name="毒蛇")
        assert added is True
        assert entity.has_status(STATUS_POISON)

        sec = entity.status_effects
        assert sec.get_effect(STATUS_POISON).power == 5
        assert sec.get_effect(STATUS_POISON).duration == 3

        # 状態異常の解除
        removed = entity.remove_status(STATUS_POISON)
        assert removed is True
        assert not entity.has_status(STATUS_POISON)

    def test_elemental_weakness_and_damage_bonus(self):
        """属性弱点によるダメージボーナス (Step 56, 69)"""
        attacker = Entity(name="アタッカー")
        attacker.attributes.dexterity = 80
        defender = Entity(name="氷の精霊")
        defender.attributes.dexterity = 5
        defender.weaknesses = ["fire"]
        defender.base_resistances = {"fire": 0}

        # 火炎攻撃 (弱点) - 命中するまで試行
        hit = False
        for _ in range(10):
            dmg_fire, is_crit, msg_fire = CombatSystem.calculate_melee_attack(attacker, defender, element=Element.FIRE)
            if dmg_fire > 0:
                assert "効果はばつぐんだ" in msg_fire
                hit = True
                break
        assert hit

    def test_status_effects_tick_processing(self):
        """ターン経過によるDoTダメージと行動不能判定、自動治癒 (Step 58-61, 70, 71)"""
        entity = Entity(name="被験者")
        entity.hp = 50
        entity.max_hp = 50
        entity.energy = 100

        # 毒と麻痺を付与
        entity.add_status(STATUS_POISON, duration=2, power=4)
        entity.add_status(STATUS_PARALYZE, duration=1, power=1)

        # 1ターン経過 (Tick 1)
        logs, _ = CombatSystem.process_status_effects(entity)
        assert entity.hp == 46  # 50 - 4
        assert entity.energy == 0  # 麻痺で行動不能 (Step 71)
        assert any("毒" in l for l in logs)
        assert any("麻痺" in l for l in logs)
        assert not entity.has_status(STATUS_PARALYZE)  # 麻痺は1ターンなので解除
        assert entity.has_status(STATUS_POISON)  # 毒は残り1ターン

        # 2ターン経過 (Tick 2)
        entity.energy = 100  # 麻痺が解けたのでエネルギー回復
        logs2, _ = CombatSystem.process_status_effects(entity)
        assert entity.hp == 42  # 46 - 4
        assert entity.energy == 100  # 麻痺していないのでエネルギー維持
        assert not entity.has_status(STATUS_POISON)  # 毒も終了
        assert any("治まった" in l for l in logs2)

    def test_cure_poison_potion(self):
        """毒消しポーションによる状態異常治療 (Step 64)"""
        entity = Entity(name="プレイヤー", is_player=True)
        entity.hp = 30
        entity.max_hp = 50
        entity.add_status(STATUS_POISON, duration=5, power=3)
        entity.add_status(STATUS_BURN, duration=3, power=5)

        assert entity.has_status(STATUS_POISON)
        assert entity.has_status(STATUS_BURN)

        potion = Item(name="毒消しのポーション", category="potion", char="🧪", color=(100, 255, 100))
        ok, msg = use_item(entity, potion)

        assert ok is True
        assert "治まった" in msg
        assert not entity.has_status(STATUS_POISON)
        assert not entity.has_status(STATUS_BURN)


if __name__ == "__main__":
    test = TestElementalAndStatusEffects()
    test.test_status_effects_component_lifecycle()
    test.test_elemental_weakness_and_damage_bonus()
    test.test_status_effects_tick_processing()
    test.test_cure_poison_potion()
    print("All Phase 3 unit & integration tests PASSED!")
