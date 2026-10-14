"""改善案6 機能3: ペット性格システムのゲームループ配線テスト。

配線対象:
- 新規ゲーム開始時にペットへ性格と好物タグが付与される
  (engine._initialize_player_and_pet から PetPersonalitySystem へ)。
- 絆 (pet.pet_ai.bond, 契約スケール) が get_bond_stat_modifiers に反映される。
- GameLoopHandler の turn 進行から apply_bond_gameplay_effects が呼ばれ、
  絆に応じた最大HPボーナスが冪等に適用される。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from constants import (
    FOOD_TAG_FISH,
    FOOD_TAG_MEAT,
    PERSONALITY_BRAVE,
    PERSONALITY_LABELS,
)
from ecs.components.components import PetAIComponent
from pet_personality_system import PetPersonalitySystem


class _PetStub:
    """必要属性だけを持つペット代替 (MagicMock 不使用: pickle/属性安全性確保)"""

    def __init__(self, max_hp: int = 50, hp: int | None = None, pet_ai: PetAIComponent | None = None):
        self.name = "テストペット"
        self.max_hp = max_hp
        self.hp = max_hp if hp is None else hp
        self.personality = ""
        self.favorite_food_tags: list[str] = []
        if pet_ai is not None:
            self.pet_ai = pet_ai


class _EngineStub:
    def __init__(self, pet):
        self.pet = pet


# --- 配線 1: 新規ゲーム時の性格付与 ---


def test_initialize_pet_personality_assigns_traits():
    pet = _PetStub()
    chosen = PetPersonalitySystem.initialize_pet_personality(pet)
    assert chosen in PERSONALITY_LABELS
    assert pet.personality == chosen
    assert pet.favorite_food_tags  # 好物タグが 1 つ以上付く


def test_initialize_pet_personality_respects_existing():
    pet = _PetStub()
    pet.personality = PERSONALITY_BRAVE
    pet.favorite_food_tags = [FOOD_TAG_FISH]
    PetPersonalitySystem.initialize_pet_personality(pet)
    assert pet.personality == PERSONALITY_BRAVE  # 上書きしない
    assert pet.favorite_food_tags == [FOOD_TAG_FISH]  # 保持される


# --- 配線 2: 契約スケールの絆が補正に反映される ---


def test_bond_modifiers_use_pet_ai_contract_scale():
    pet = _PetStub(pet_ai=PetAIComponent())
    pet.pet_ai.bond = 200  # 契約 max_bond=1000 の 20% (デフォルト fallback の 50% とは区別)
    pet.pet_ai.contract_id = "default"
    mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
    assert mods["hp_bonus"] == 8  # 20% × 0.4
    assert mods["hit_bonus"] == 2
    assert mods["damage_multiplier"] == 1.05  # 1.0 + 0.2*0.25 = 1.05
    assert mods["dv_bonus"] == 1


def test_bond_modifiers_keep_entity_attr_compatibility():
    """旧形式 (entity.bond 0-100) の既存契約を維持する。"""
    pet = _PetStub(pet_ai=PetAIComponent())
    pet.bond = 50  # entity 属性が優先される
    mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
    assert mods["hp_bonus"] == 20


# --- 配線 3: ゲームループからの絆効果適用 ---


def test_apply_bond_gameplay_effects_grows_max_hp():
    pet = _PetStub(max_hp=50, pet_ai=PetAIComponent())
    pet.pet_ai.bond = 500  # 50% → hp_bonus=20
    engine = _EngineStub(pet)

    PetPersonalitySystem.apply_bond_gameplay_effects(engine)
    assert pet.max_hp == 70
    assert pet.hp == 50  # 自動回復はしない (控えめな初期値)

    # 2 度呼んでも増幅しない (冪等)
    PetPersonalitySystem.apply_bond_gameplay_effects(engine)
    assert pet.max_hp == 70

    # 外部 (レベルアップ等) が max_hp を上げても打ち消さない
    pet.max_hp = 90
    PetPersonalitySystem.apply_bond_gameplay_effects(engine)
    assert pet.max_hp == 90


def test_apply_bond_gameplay_effects_shrinks_and_clamps():
    pet = _PetStub(max_hp=50, pet_ai=PetAIComponent())
    pet.pet_ai.bond = 500
    engine = _EngineStub(pet)
    PetPersonalitySystem.apply_bond_gameplay_effects(engine)
    assert pet.max_hp == 70

    pet.pet_ai.bond = 0  # 絆喪失 → ボーナス消失
    pet.hp = 65
    PetPersonalitySystem.apply_bond_gameplay_effects(engine)
    assert pet.max_hp == 50
    assert pet.hp == 50  # max_hp を超えないようクランプ


def test_apply_bond_gameplay_effects_noop_without_pet():
    engine = _EngineStub(None)
    PetPersonalitySystem.apply_bond_gameplay_effects(engine)  # 例外を出さない


def test_engine_init_wires_personality(monkeypatch):
    """engine._initialize_player_and_pet が initialize_pet_personality を呼ぶこと。"""
    import engine.engine as engine_mod

    calls: list = []
    monkeypatch.setattr(
        PetPersonalitySystem,
        "initialize_pet_personality",
        staticmethod(lambda pet: calls.append(pet) or PERSONALITY_BRAVE),
    )

    engine_obj = engine_mod.Engine.__new__(engine_mod.Engine)
    from types import SimpleNamespace

    pet = _PetStub()
    player = SimpleNamespace(
        god_id="",
        piety=0,
        hp=10,
        max_hp=10,
        mp=5,
        max_mp=5,
        status_effects=None,
        resistances=None,
        faction="",
        aggro=None,
    )
    engine_obj.game_state_data = SimpleNamespace(player=player, pet=pet)

    # meta_progression_manager は kernel 経由のプロパティのため、テスト用に差し替える
    monkeypatch.setattr(
        engine_mod.Engine,
        "meta_progression_manager",
        property(
            lambda self: SimpleNamespace(recalculate_and_apply_bonuses=lambda p: None)
        ),
    )
    engine_obj._initialize_player_and_pet()
    assert calls and calls[0] is pet
