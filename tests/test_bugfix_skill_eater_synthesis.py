"""Regression tests for 案9バッチ1 coverage-testing bugs (synthesis / registry).

Fixes covered here:
- bug1: 最後の2スキルを合成に消費すると is_husk=True が add_skill 後も残る
- bug2: 合成結果が registry._skills 私有 dict に直接書き込まれる (API 境界違反)
- bug3: CharacterState.add_skill / current_memory_usage が注入 registry を無視して
  SkillEaterRegistry.get_instance() を参照する
"""

from __future__ import annotations

import pytest

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_synthesis_system import SkillEaterSynthesisSystem
from skill_eater_system import (
    CharacterSkillSlot,
    CharacterState,
    SkillDef,
    SkillEaterRegistry,
    SkillTier,
    SkillType,
)


class FakeAudio:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play_sound(self, name: str, category: str | None = None) -> bool:
        self.played.append(name)
        return True


def make_skill(
    skill_id: str,
    name: str,
    tier: SkillTier = SkillTier.COMMON,
    skill_type: SkillType = SkillType.PASSIVE,
    tags: list[str] | None = None,
    memory_usage: int = 1,
) -> SkillDef:
    return SkillDef(
        id=skill_id,
        name=name,
        tier=tier,
        type=skill_type,
        tags=tags or [],
        memory_usage=memory_usage,
    )


def make_char(**kwargs) -> CharacterState:
    defaults = dict(
        id="p1",
        name="喰らい手",
        hp=100,
        max_hp=100,
        mp=50,
        max_mp=50,
        atk=30,
        defense=10,
        intelligence=10,
        speed=10,
    )
    defaults.update(kwargs)
    return CharacterState(**defaults)


@pytest.fixture
def audio() -> FakeAudio:
    return FakeAudio()


@pytest.fixture
def presentation(audio: FakeAudio) -> SkillEaterPresentationSystem:
    return SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)


@pytest.fixture
def reg() -> SkillEaterRegistry:
    """非シングルトンの独立 registry (バグ3の検証を兼ねる)"""
    return SkillEaterRegistry()


@pytest.fixture
def system(reg: SkillEaterRegistry, audio: FakeAudio, presentation) -> SkillEaterSynthesisSystem:
    return SkillEaterSynthesisSystem(registry=reg, audio=audio, presentation=presentation)


# ---------------------------------------------------------------------------
# bug1: 合成による最後の2スキル消費で husk 状態が残留する
# ---------------------------------------------------------------------------


class TestBug1HuskClearedAfterSynthesis:
    def test_last_two_skills_synthesis_clears_husk(self, reg, system) -> None:
        reg.register_skill(make_skill("m1", "素材A", tags=["Fire"]))
        reg.register_skill(make_skill("m2", "素材B", tags=["Ice"]))
        char = make_char(registry=reg)
        char.add_skill("m1")
        char.add_skill("m2")
        assert char.is_husk is False

        res = system.synthesize(char, "m1", "m2")

        assert res.success is True
        assert char.has_skill(res.result_skill.id) is True
        # 修正前: remove_skill が空になった瞬間に立てた is_husk=True が残留する
        assert char.is_husk is False

    def test_static_recipe_last_two_skills_clears_husk(self, reg, system) -> None:
        reg.register_skill(make_skill("com_magic_001", "火種", tags=["Fire"]))
        reg.register_skill(make_skill("com_labor_002", "夜目", tags=["Earth"]))
        reg.register_skill(
            make_skill("rar_infrared_vision", "赤外線視覚", tier=SkillTier.RARE)
        )
        char = make_char(registry=reg)
        char.add_skill("com_magic_001")
        char.add_skill("com_labor_002")

        res = system.synthesize(char, "com_magic_001", "com_labor_002")

        assert res.success is True
        assert char.has_skill("rar_infrared_vision") is True
        assert char.is_husk is False

    def test_capacity_failure_keeps_husk_state(self, reg, system) -> None:
        # 結果の装備に失敗して本当に空っぽになった場合は husk のままが正しい
        reg.register_skill(make_skill("m1", "素材A", memory_usage=1))
        reg.register_skill(make_skill("m2", "素材B", memory_usage=1))
        reg.register_skill(
            make_skill("heavy", "重い結果", tier=SkillTier.UNIQUE, memory_usage=5)
        )
        system.register_static_recipe("m1", "m2", "heavy")
        char = make_char(registry=reg)
        char.max_memory_capacity = 2
        char.add_skill("m1")
        char.add_skill("m2")

        res = system.synthesize(char, "m1", "m2")

        assert res.success is True
        assert char.has_skill("heavy") is False
        assert len(char.skills) == 0
        assert char.is_husk is True


# ---------------------------------------------------------------------------
# bug2: 合成結果の registry 登録が私有 dict への直接書き込みになっている
# ---------------------------------------------------------------------------


class TestBug2RegisterViaPublicApi:
    def _spy_register_skill(self, reg: SkillEaterRegistry) -> list[str]:
        calls: list[str] = []
        orig = reg.register_skill

        def spy(skill: SkillDef) -> None:
            calls.append(skill.id)
            orig(skill)

        reg.register_skill = spy  # type: ignore[method-assign]
        return calls

    def test_procedural_result_registered_via_public_api(self, reg, system) -> None:
        reg.register_skill(make_skill("s_fire", "炎撃", tags=["Fire"]))
        reg.register_skill(make_skill("s_ice", "氷撃", tags=["Ice"]))
        calls = self._spy_register_skill(reg)
        char = make_char(registry=reg)
        char.add_skill("s_fire")
        char.add_skill("s_ice")

        res = system.synthesize(char, "s_fire", "s_ice")

        assert res.success is True
        assert res.result_skill is not None
        assert res.result_skill.id in calls
        assert reg.get_skill(res.result_skill.id) is res.result_skill

    def test_static_recipe_fallback_registered_via_public_api(self, reg, system) -> None:
        reg.register_skill(make_skill("com_magic_001", "火種"))
        reg.register_skill(make_skill("com_labor_002", "夜目"))
        system.register_static_recipe("com_magic_001", "com_labor_002", "unknown_result")
        calls = self._spy_register_skill(reg)
        char = make_char(registry=reg)
        char.add_skill("com_magic_001")
        char.add_skill("com_labor_002")

        res = system.synthesize(char, "com_magic_001", "com_labor_002")

        assert res.success is True
        assert "unknown_result" in calls
        assert reg.get_skill("unknown_result") is not None


# ---------------------------------------------------------------------------
# bug3: CharacterState が注入 registry を無視してシングルトンを見る
# ---------------------------------------------------------------------------


class TestBug3InjectedRegistryRespected:
    def test_add_skill_capacity_check_uses_bound_registry(self, reg) -> None:
        reg.register_skill(make_skill("big", "巨大スキル", memory_usage=7))
        char = make_char(registry=reg, max_memory_capacity=3)

        # シングルトン (未登録 → default 1) を参照していると容量チェックを通過してしまう
        ok = char.add_skill("big")

        assert ok is False
        assert char.has_skill("big") is False

    def test_add_skill_success_uses_bound_registry(self, reg) -> None:
        reg.register_skill(make_skill("normal", "通常スキル", memory_usage=2))
        char = make_char(registry=reg, max_memory_capacity=10)

        ok = char.add_skill("normal")

        assert ok is True
        assert char.has_skill("normal") is True

    def test_current_memory_usage_uses_bound_registry(self, reg) -> None:
        reg.register_skill(make_skill("s1", "S1", memory_usage=3))
        reg.register_skill(make_skill("s2", "S2", memory_usage=4))
        char = make_char(registry=reg)
        char.add_skill("s1")
        char.add_skill("s2")

        # 修正前: シングルトン未登録 → default 1+1=2 が返る
        assert char.current_memory_usage == 7

    def test_calculate_memory_usage_mb_uses_bound_registry(self, reg) -> None:
        reg.register_skill(
            SkillDef(
                id="m1",
                name="M1",
                tier=SkillTier.COMMON,
                type=SkillType.PASSIVE,
                memory_cost_mb=55,
            )
        )
        char = make_char(registry=reg)
        char.add_skill("m1")

        assert char.calculate_memory_usage() == 55
        assert char.current_used_memory_mb == 55

    def test_retrieve_skill_capacity_check_uses_bound_registry(self, reg) -> None:
        reg.register_skill(make_skill("big", "巨大スキル", memory_usage=7))
        char = make_char(registry=reg, max_memory_capacity=3)
        char.archived_skills["big"] = CharacterSkillSlot(skill_id="big")

        # シングルトン (default 1) を見ていると容量不足でも復元できてしまう
        ok = char.retrieve_skill("big")

        assert ok is False
        assert char.has_skill("big") is False
        assert "big" in char.archived_skills

    def test_unbound_character_still_falls_back_to_singleton(self) -> None:
        SkillEaterRegistry.reset_instance()
        try:
            reg = SkillEaterRegistry.get_instance()
            reg.register_skill(make_skill("s1", "S1", memory_usage=4))
            char = make_char()  # registry 未バインド

            ok = char.add_skill("s1")

            assert ok is True
            # シングルトンに登録された memory_usage=4 が参照される
            assert char.current_memory_usage == 4
        finally:
            SkillEaterRegistry.reset_instance()
