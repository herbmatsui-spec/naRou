"""Coverage tests for skill_eater_synthesis_system (SkillEaterSynthesisSystem)."""

from __future__ import annotations

import pytest

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_synthesis_system import (
    StaticSynthesisRecipe,
    SynthesisResult,
    SkillEaterSynthesisSystem,
    TreeNode,
)
from skill_eater_system import (
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
    mp_cost: int = 5,
    cooldown: int = 2,
    market_value: int = 100,
) -> SkillDef:
    return SkillDef(
        id=skill_id,
        name=name,
        tier=tier,
        type=skill_type,
        mp_cost=mp_cost,
        cooldown=cooldown,
        market_value=market_value,
        tags=tags or [],
    )


def make_char(char_id: str = "p1", name: str = "喰らい手") -> CharacterState:
    return CharacterState(
        id=char_id,
        name=name,
        hp=100,
        max_hp=100,
        mp=50,
        max_mp=50,
        atk=30,
        defense=10,
        intelligence=10,
        speed=10,
    )


@pytest.fixture
def registry() -> SkillEaterRegistry:
    SkillEaterRegistry.reset_instance()
    reg = SkillEaterRegistry.get_instance()
    # バグ2修正 (register_skill 公開 API 追加) に伴い、_skills 直接書き込みから移行
    reg.register_skill(make_skill("com_magic_001", "ファイアボルト", tags=["Fire"]))
    reg.register_skill(make_skill("com_labor_002", "掘削", tags=["Earth"]))
    reg.register_skill(
        make_skill("rar_infrared_vision", "赤外線視覚", tier=SkillTier.RARE, tags=["Fire", "Earth"])
    )
    reg.register_skill(make_skill("rar_combat_012", "黄金の一撃", tier=SkillTier.RARE))
    reg.register_skill(make_skill("uni_midas_001", "ミダスの手", tier=SkillTier.UNIQUE))
    yield reg
    SkillEaterRegistry.reset_instance()


@pytest.fixture
def audio() -> FakeAudio:
    return FakeAudio()


@pytest.fixture
def presentation(audio: FakeAudio) -> SkillEaterPresentationSystem:
    return SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)


@pytest.fixture
def system(registry, audio, presentation) -> SkillEaterSynthesisSystem:
    return SkillEaterSynthesisSystem(
        registry=registry, audio=audio, presentation=presentation
    )


class TestDataclasses:
    def test_static_recipe_fields(self) -> None:
        r = StaticSynthesisRecipe(
            ingredient_ids=("a", "b"), result_skill_id="c", description="d"
        )
        assert r.ingredient_ids == ("a", "b")
        assert r.result_skill_id == "c"

    def test_synthesis_result_defaults(self) -> None:
        res = SynthesisResult(success=False)
        assert res.result_skill is None
        assert res.consumed_skill_ids == []
        assert res.is_procedural is False
        assert res.played_sounds == []
        assert res.presentation_events == []

    def test_tree_node_defaults(self) -> None:
        node = TreeNode(skill_id="s", name="n", tier="Common")
        assert node.parent_ids == []
        assert node.is_synthesized is False


class TestStaticRecipes:
    def test_default_recipes_registered_both_orders(self, system) -> None:
        assert system._static_recipes[("com_magic_001", "com_labor_002")] == "rar_infrared_vision"
        assert system._static_recipes[("com_labor_002", "com_magic_001")] == "rar_infrared_vision"
        assert system._static_recipes[("rar_combat_012", "uni_midas_001")] == "rar_gold_body"
        assert system._static_recipes[("uni_midas_001", "rar_combat_012")] == "rar_gold_body"

    def test_register_custom_recipe_symmetric(self, system) -> None:
        system.register_static_recipe("x", "y", "z")
        assert system._static_recipes[("x", "y")] == "z"
        assert system._static_recipes[("y", "x")] == "z"


class TestSynthesizeErrors:
    def test_missing_ingredient_skill(self, system) -> None:
        char = make_char()
        char.add_skill("com_magic_001")
        res = system.synthesize(char, "com_magic_001", "not_owned")
        assert res.success is False
        assert "所持していない" in res.message
        assert res.played_sounds == ["metalClick.ogg"]
        assert res.presentation_events[0].audio_file == "metalClick.ogg"

    def test_same_skill_pair_rejected(self, system) -> None:
        char = make_char()
        char.add_skill("com_magic_001")
        res = system.synthesize(char, "com_magic_001", "com_magic_001")
        assert res.success is False
        assert "同じスキル同士" in res.message

    def test_skill_not_in_registry_rejected(self, system, registry) -> None:
        char = make_char()
        char.add_skill("com_magic_001")
        char.add_skill("com_labor_002")
        del registry._skills["com_magic_001"]
        res = system.synthesize(char, "com_magic_001", "com_labor_002")
        assert res.success is False
        assert "無効なスキルデータ" in res.message
        # 素材は消費されない
        assert char.has_skill("com_magic_001") is True


class TestStaticSynthesis:
    def test_known_recipe_success(self, system) -> None:
        char = make_char()
        char.add_skill("com_magic_001")
        char.add_skill("com_labor_002")
        res = system.synthesize(char, "com_magic_001", "com_labor_002")

        assert res.success is True
        assert res.is_procedural is False
        assert res.consumed_skill_ids == ["com_magic_001", "com_labor_002"]
        assert res.result_skill is not None
        assert res.result_skill.id == "rar_infrared_vision"
        # 素材が消費され結果が装備される
        assert char.has_skill("com_magic_001") is False
        assert char.has_skill("com_labor_002") is False
        assert char.has_skill("rar_infrared_vision") is True
        # バグ1修正: 最後の2スキルを消費しても合成結果の装備に成功した時点で husk は解除される
        assert char.is_husk is False
        # 演出: 調合 → 秘伝 → 完成 の順
        messages = [e.message for e in res.presentation_events]
        assert "合成炉に投入" in messages[0]
        assert "秘伝の合成式" in messages[1]
        assert "完成" in messages[2]
        assert res.played_sounds == [
            "metalPot2.ogg",
            "bookOpen.ogg",
            "bookFlip1.ogg",
            "metalPot3.ogg",
        ]

    def test_reverse_order_recipe_also_resolves(self, system) -> None:
        char = make_char()
        char.add_skill("com_labor_002")
        char.add_skill("com_magic_001")
        res = system.synthesize(char, "com_labor_002", "com_magic_001")
        assert res.success is True
        assert res.result_skill is not None
        assert res.result_skill.id == "rar_infrared_vision"

    def test_recipe_with_unregistered_result_creates_fallback(
        self, system, registry
    ) -> None:
        system.register_static_recipe("com_magic_001", "rar_combat_012", "unknown_result_id")
        char = make_char()
        char.add_skill("com_magic_001")
        char.add_skill("rar_combat_012")
        res = system.synthesize(char, "com_magic_001", "rar_combat_012")
        assert res.success is True
        assert res.result_skill is not None
        assert res.result_skill.id == "unknown_result_id"
        assert res.result_skill.name.startswith("合成秘奥")
        assert res.result_skill.tier == SkillTier.RARE
        # registry に自動登録される
        assert registry.get_skill("unknown_result_id") is not None


class TestProceduralSynthesis:
    def test_unknown_pair_creates_chimera(self, system) -> None:
        registry = system.registry
        registry.register_skill(
            make_skill(
                "s_fire", "炎撃", tier=SkillTier.RARE, skill_type=SkillType.ACTIVE,
                tags=["Fire"], mp_cost=10, cooldown=3, market_value=200,
            )
        )
        registry.register_skill(
            make_skill(
                "s_ice", "氷撃", tier=SkillTier.UNIQUE, skill_type=SkillType.PASSIVE,
                tags=["Ice"], mp_cost=7, cooldown=5, market_value=300,
            )
        )
        char = make_char()
        char.add_skill("s_fire")
        char.add_skill("s_ice")
        res = system.synthesize(char, "s_fire", "s_ice")

        assert res.success is True
        assert res.is_procedural is True
        assert res.consumed_skill_ids == ["s_fire", "s_ice"]
        chimera = res.result_skill
        assert chimera is not None
        assert chimera.id.startswith("proc_syn_")
        assert "炎撃" in chimera.name and "氷撃" in chimera.name
        # タグ統合 & set() による重複排除
        assert set(chimera.tags) == {"Fire", "Ice"}
        # ティアは高い方 (UNIQUE)
        assert chimera.tier == SkillTier.UNIQUE
        # ACTIVE が片方でもあれば ACTIVE
        assert chimera.type == SkillType.ACTIVE
        assert chimera.mp_cost == 17
        assert chimera.cooldown == 5
        assert chimera.market_value == 500
        assert chimera.is_illegal is True
        assert char.has_skill("s_fire") is False
        assert char.has_skill("s_ice") is False
        assert char.has_skill(chimera.id) is True
        # registry に登録される
        assert system.registry.get_skill(chimera.id) is chimera
        # 違法警告イベントが含まれる
        messages = [e.message for e in res.presentation_events]
        assert any("違法" in m for m in messages)

    def test_both_passive_yield_passive_chimera(self, system) -> None:
        registry = system.registry
        registry.register_skill(make_skill("ps1", "耐性1", skill_type=SkillType.PASSIVE))
        registry.register_skill(make_skill("ps2", "耐性2", skill_type=SkillType.PASSIVE))
        char = make_char()
        char.add_skill("ps1")
        char.add_skill("ps2")
        res = system.synthesize(char, "ps1", "ps2")
        assert res.result_skill is not None
        assert res.result_skill.type == SkillType.PASSIVE

    def test_duplicate_tags_deduplicated(self, system) -> None:
        registry = system.registry
        registry.register_skill(make_skill("t1", "a", tags=["Fire", "Wind"]))
        registry.register_skill(make_skill("t2", "b", tags=["Fire"]))
        char = make_char()
        char.add_skill("t1")
        char.add_skill("t2")
        res = system.synthesize(char, "t1", "t2")
        assert res.result_skill is not None
        assert sorted(res.result_skill.tags) == ["Fire", "Wind"]


class TestDynamicTree:
    def test_empty_character_yields_root_only(self, system) -> None:
        nodes = system.generate_dynamic_tree(make_char())
        assert len(nodes) == 1
        assert nodes[0].skill_id == "root_analysis"
        assert nodes[0].parent_ids == []

    def test_nodes_per_skill_with_synthesis_flag(self, system) -> None:
        char = make_char()
        char.add_skill("com_magic_001")
        char.add_skill("rar_infrared_vision")
        # proc 接頭辞の疑似的な合成スキル
        system.registry.register_skill(
            make_skill("proc_syn_abc", "キメラ", tier=SkillTier.UNIQUE)
        )
        char.add_skill("proc_syn_abc")

        nodes = system.generate_dynamic_tree(char)
        assert nodes[0].skill_id == "root_analysis"
        by_id = {n.skill_id: n for n in nodes[1:]}
        assert set(by_id) == {"com_magic_001", "rar_infrared_vision", "proc_syn_abc"}
        assert all(n.parent_ids == ["root_analysis"] for n in nodes[1:])
        assert by_id["com_magic_001"].is_synthesized is False
        assert by_id["proc_syn_abc"].is_synthesized is True
        assert by_id["proc_syn_abc"].tier == "Unique"

    def test_unknown_skill_id_skipped(self, system) -> None:
        char = make_char()
        char.skills["ghost_skill"] = None  # type: ignore[assignment]
        nodes = system.generate_dynamic_tree(char)
        assert [n.skill_id for n in nodes] == ["root_analysis"]
