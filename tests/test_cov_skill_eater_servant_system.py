"""Coverage tests for skill_eater_servant_system (SkillEaterServantSystem)."""

from __future__ import annotations

import pytest

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_servant_system import (
    ServantActionResult,
    ServantCharacter,
    SkillEaterServantSystem,
)
from skill_eater_system import CharacterState, SkillEaterRegistry


class FakeAudio:
    """play_sound を記録するだけの軽量スタブ (pygame不要)"""

    def __init__(self) -> None:
        self.played: list[str] = []

    def play_sound(self, name: str, category: str | None = None) -> bool:
        self.played.append(name)
        return True


def make_char(
    char_id: str,
    name: str,
    hp: int = 100,
    max_hp: int = 100,
    atk: int = 30,
    defense: int = 10,
    intelligence: int = 10,
) -> CharacterState:
    return CharacterState(
        id=char_id,
        name=name,
        hp=hp,
        max_hp=max_hp,
        mp=20,
        max_mp=20,
        atk=atk,
        defense=defense,
        intelligence=intelligence,
        speed=10,
    )


@pytest.fixture
def registry() -> SkillEaterRegistry:
    SkillEaterRegistry.reset_instance()
    reg = SkillEaterRegistry()
    yield reg
    SkillEaterRegistry.reset_instance()


@pytest.fixture
def audio() -> FakeAudio:
    return FakeAudio()


@pytest.fixture
def presentation(audio: FakeAudio) -> SkillEaterPresentationSystem:
    return SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)


@pytest.fixture
def system(registry, audio, presentation) -> SkillEaterServantSystem:
    return SkillEaterServantSystem(
        registry=registry, audio=audio, presentation=presentation
    )


def make_husk(husk_id: str = "husk_1", name: str = "空殻A") -> CharacterState:
    char = make_char(husk_id, name)
    char.is_husk = True
    return char


class TestServantCharacter:
    def test_defaults_and_skill_count(self) -> None:
        state = make_char("s1", "x")
        state.add_skill("sk1")
        servant = ServantCharacter(
            id="servant_s1", original_name="orig", custom_name="cust", state=state
        )
        assert servant.duration_turns == 3
        assert servant.assigned_role == "Turret"
        assert servant.get_skill_count() == 1


class TestCaptureHusk:
    def test_capture_husk_success(self, system: SkillEaterServantSystem) -> None:
        husk = make_husk()
        servant = system.capture_husk(husk, custom_name="タレット壱号")
        assert servant is not None
        assert servant.id == "servant_husk_1"
        assert servant.custom_name == "タレット壱号"
        assert servant.original_name == "空殻A"
        assert system.servant_party["servant_husk_1"] is servant

    def test_capture_auto_names(self, system: SkillEaterServantSystem) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        assert servant.custom_name == "従属素体_空殻A"

    def test_capture_non_husk_rejected(self, system: SkillEaterServantSystem) -> None:
        alive = make_char("alive_1", "元気な敵")
        assert system.capture_husk(alive) is None
        assert system.servant_party == {}


class TestTransplantSkill:
    def test_transplant_moves_skill_to_servant(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        husk = make_husk()
        servant = system.capture_husk(husk)
        assert servant is not None
        player = make_char("player_1", "喰らい手")
        player.add_skill("com_combat_001")

        ok, msg = system.transplant_skill(player, servant, "com_combat_001")
        assert ok is True
        assert player.has_skill("com_combat_001") is False
        assert servant.state.has_skill("com_combat_001") is True
        assert servant.state.is_husk is False
        assert servant.duration_turns == 3
        assert "注入" in msg
        assert audio.played == ["beltHandle1.ogg"]
        assert system.presentation.event_queue[-1].audio_file == "beltHandle1.ogg"

    def test_transplant_unknown_skill_fails(
        self, system: SkillEaterServantSystem
    ) -> None:
        husk = make_husk()
        servant = system.capture_husk(husk)
        assert servant is not None
        player = make_char("player_1", "p")
        ok, msg = system.transplant_skill(player, servant, "nonexistent_skill")
        assert ok is False
        assert "所持していません" in msg
        assert servant.state.get_skill_ids() == []


class TestCrumble:
    def test_crumble_removes_from_party(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        result = system.crumble_servant(servant.id)
        assert result is servant
        assert servant.id not in system.servant_party
        # 演出 (cloth3) + 自壊音 (creak3) の順で再生される
        assert audio.played == ["cloth3.ogg", "creak3.ogg"]

    def test_crumble_unknown_id_returns_none(
        self, system: SkillEaterServantSystem
    ) -> None:
        assert system.crumble_servant("ghost") is None


class TestExecuteTurn:
    def test_attack_lowest_hp_enemy(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        e1 = make_char("e1", "敵1", hp=80)
        e2 = make_char("e2", "敵2", hp=40)
        result = system.execute_servant_turn(servant, [e1, e2], [])

        assert isinstance(result, ServantActionResult)
        assert result.action_type == "ATTACK"
        assert result.target_id == "e2"
        # atk 30 - defense 10 // 2 = 25
        assert result.damage == 25
        assert e2.hp == 15
        assert servant.duration_turns == 2
        assert result.is_crumbled is False
        assert "一斉射撃" in result.log_message
        # 演出イベントが発行されている
        assert len(result.presentation_events) == 1

    def test_damage_minimum_one(
        self, system: SkillEaterServantSystem
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        tank = make_char("tank", "鉄壁", hp=100, defense=100)
        result = system.execute_servant_turn(servant, [tank], [])
        assert result.damage == 1
        assert tank.hp == 99

    def test_crumble_after_last_turn(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        enemy = make_char("e1", "敵", hp=100)
        servant.duration_turns = 1
        result = system.execute_servant_turn(servant, [enemy], [])
        assert result.is_crumbled is True
        assert "崩壊" in result.log_message or "自壊" in result.log_message
        assert servant.id not in system.servant_party
        assert result.played_sounds == ["cloth3.ogg", "creak3.ogg"]
        assert audio.played == ["cloth3.ogg", "creak3.ogg"]

    def test_heal_skill_targets_wounded_ally(
        self, system: SkillEaterServantSystem
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        servant.state.add_skill("com_combat_002")
        ally_wounded = make_char("ally1", "負傷者", hp=30)
        ally_full = make_char("ally2", "健常者", hp=100)
        result = system.execute_servant_turn(servant, [], [ally_full, ally_wounded])

        assert result.action_type == "SKILL"
        assert result.skill_used_id == "com_combat_002"
        assert result.target_id == "ally1"
        # int(10 * 1.2 + 20) = 32
        assert result.heal == 32
        assert ally_wounded.hp == 62
        assert ally_full.hp == 100

    def test_heal_caps_at_max_hp(self, system: SkillEaterServantSystem) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        servant.state.add_skill("com_combat_002")
        servant.state.intelligence = 100
        ally = make_char("ally1", "a", hp=99)
        result = system.execute_servant_turn(servant, [], [ally])
        assert ally.hp == ally.max_hp

    def test_heal_without_wounded_targets_first_ally(
        self, system: SkillEaterServantSystem
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        servant.state.add_skill("com_combat_002")
        ally = make_char("ally1", "a", hp=100)
        result = system.execute_servant_turn(servant, [], [ally])
        assert result.target_id == "ally1"

    def test_pass_when_no_targets(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        result = system.execute_servant_turn(servant, [], [])
        assert result.action_type == "PASS"
        assert result.target_id == ""
        assert result.damage == 0
        assert servant.duration_turns == 2

    def test_pass_crumble(
        self, system: SkillEaterServantSystem, audio: FakeAudio
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        servant.duration_turns = 1
        result = system.execute_servant_turn(servant, [], [])
        assert result.action_type == "PASS"
        assert result.is_crumbled is True
        assert servant.id not in system.servant_party

    def test_heal_falls_back_to_self_when_no_allies(
        self, system: SkillEaterServantSystem
    ) -> None:
        servant = system.capture_husk(make_husk())
        assert servant is not None
        servant.state.add_skill("com_combat_002")
        servant.state.hp = 50
        result = system.execute_servant_turn(servant, [], [])
        assert result.target_id == servant.state.id
        assert result.heal == 32
        assert servant.state.hp == 82
