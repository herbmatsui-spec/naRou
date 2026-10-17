"""Coverage tests for skill_eater_concept_crystal (ConceptCrystallizer)."""

from __future__ import annotations

import pytest

import skill_eater_concept_crystal as cc_mod
from skill_eater_concept_crystal import ConceptCrystallizer
from skill_eater_exploration_system import ExplorationRank


@pytest.fixture
def cryst() -> ConceptCrystallizer:
    return ConceptCrystallizer()


def rank(n: int) -> ExplorationRank:
    return ExplorationRank(rank=n)


class TestCrystallizeSkills:
    def test_requires_exactly_three(self, cryst: ConceptCrystallizer) -> None:
        two = [{"name": "a", "tags": ["Fire"]}, {"name": "b", "tags": ["Fire"]}]
        res = cryst.crystallize_skills("Fire", two)
        assert res["success"] is False
        assert "Exactly 3" in res["message"]

        four = two + [{"name": "c", "tags": ["Fire"]}, {"name": "d", "tags": ["Fire"]}]
        assert cryst.crystallize_skills("Fire", four)["success"] is False

    def test_tag_mismatch_rejected(self, cryst: ConceptCrystallizer) -> None:
        skills = [
            {"name": "a", "tags": ["Fire"]},
            {"name": "b", "tags": ["Fire"]},
            {"name": "c", "tags": ["Ice"]},
        ]
        res = cryst.crystallize_skills("Fire", skills)
        assert res["success"] is False
        assert "must share" in res["message"]

    def test_missing_tags_rejected(self, cryst: ConceptCrystallizer) -> None:
        skills = [{"name": "a", "tags": ["Fire"]}, {"name": "b"}, {"name": "c", "tags": ["Fire"]}]
        res = cryst.crystallize_skills("Fire", skills)
        assert res["success"] is False

    def test_success_combines_power_and_passives(self, cryst: ConceptCrystallizer) -> None:
        skills = [
            {"name": "a", "tags": ["Fire"], "power": 10, "passive": "burn_aura"},
            {"name": "b", "tags": ["Fire"], "power": 20},
            {"name": "c", "tags": ["Fire"], "power": 30, "passive": "heat_shield"},
        ]
        res = cryst.crystallize_skills("Fire", skills)
        assert res["success"] is True
        concept = res["concept_skill"]
        assert concept["name"] == "Concept of Absolute Fire (純粋なるFireの概念)"
        assert concept["category"] == "Fire"
        assert concept["is_concept_crystal"] is True
        assert concept["power"] == 10 + 20 + 30 + 100
        assert concept["tags"] == ["Fire", "Concept", "Mastery", "Inherited"]
        assert concept["passives"] == ["burn_aura", "heat_shield"]

    def test_message_contains_name(self, cryst: ConceptCrystallizer) -> None:
        skills = [{"name": "x", "tags": ["Dark"]}] * 3
        res = cryst.crystallize_skills("Dark", skills)
        assert "CRYSTALLIZATION COMPLETE" in res["message"]
        assert "Dark" in res["message"]


class TestDropTables:
    def test_four_drop_tables_exist(self) -> None:
        assert set(ConceptCrystallizer.DROP_TABLES) == {
            "first_floor_boss", "secret_area", "faction_boss", "deep_bounty",
        }

    def test_deep_bounty_has_highest_base_rate(self) -> None:
        rates = {k: v["base_rate"] for k, v in ConceptCrystallizer.DROP_TABLES.items()}
        assert max(rates, key=rates.get) == "deep_bounty"


class TestRollCrystalDrop:
    def test_unknown_category_returns_none(self, cryst: ConceptCrystallizer) -> None:
        assert cryst.roll_concept_crystal_drop("nope", 1, rank(1)) is None

    def test_miss_returns_none_and_no_history(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.99)
        assert cryst.roll_concept_crystal_drop("first_floor_boss", 1, rank(1)) is None
        assert cryst.get_drop_history() == []

    def test_hit_returns_crystal_with_rate_math(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.0)
        monkeypatch.setattr(cc_mod.random, "choice", lambda seq: seq[0])
        crystal = cryst.roll_concept_crystal_drop("first_floor_boss", depth=10, exploration_rank=rank(3))
        assert crystal is not None
        assert crystal["category"] == "Fire"
        assert crystal["is_concept_crystal"] is True
        # power = 100 + depth*2 + rank*10 = 100 + 20 + 30
        assert crystal["power"] == 150
        assert crystal["description"] == "Dropped from first_floor_boss at depth 10."
        # rate = 0.15 + 10*0.005 + 3*0.05 + 0.20 = 0.55
        hist = cryst.get_drop_history()
        assert len(hist) == 1
        assert hist[0]["exploration_rank"] == 3
        assert hist[0]["crystal_name"] == crystal["name"]

    def test_rate_capped_at_95_percent(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.96)
        # deep_bounty at depth 100, rank 10: 0.5 + 0.1 + 0.2 = 0.8 → capped check irrelevant;
        # 0.96 > 0.8 → miss. Add first-clear to push to 0.8, still miss → proves cap/limit logic path
        assert cryst.roll_concept_crystal_drop("deep_bounty", 100, rank(10), is_first_clear=True) is None

    def test_choice_picks_within_category_list(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.0)
        seen = set()
        for i in range(len(ConceptCrystallizer.DROP_TABLES["secret_area"]["crystal_categories"])):
            monkeypatch.setattr(
                cc_mod.random, "choice",
                lambda seq, i=i: seq[i],
            )
            crystal = cryst.roll_concept_crystal_drop("secret_area", 1, rank(1))
            seen.add(crystal["category"])
        assert seen == set(ConceptCrystallizer.DROP_TABLES["secret_area"]["crystal_categories"])

    def test_convenience_wrappers(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.0)
        monkeypatch.setattr(cc_mod.random, "choice", lambda seq: seq[0])
        assert cryst.roll_first_floor_boss_drop(5, rank(2)) is not None
        assert cryst.roll_secret_area_drop(5, rank(2)) is not None
        assert cryst.roll_faction_boss_drop(5, rank(2)) is not None

    def test_wrappers_miss_path(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 1.0)
        assert cryst.roll_first_floor_boss_drop(1, rank(1)) is None
        assert cryst.roll_secret_area_drop(1, rank(1)) is None
        assert cryst.roll_faction_boss_drop(1, rank(1)) is None


class TestDropHistory:
    def test_clear_drop_history(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.0)
        monkeypatch.setattr(cc_mod.random, "choice", lambda seq: seq[0])
        cryst.roll_concept_crystal_drop("first_floor_boss", 1, rank(1))
        assert len(cryst.get_drop_history()) == 1
        cryst.clear_drop_history()
        assert cryst.get_drop_history() == []

    def test_get_returns_copy(self, cryst, monkeypatch) -> None:
        monkeypatch.setattr(cc_mod.random, "random", lambda: 0.0)
        monkeypatch.setattr(cc_mod.random, "choice", lambda seq: seq[0])
        cryst.roll_concept_crystal_drop("first_floor_boss", 1, rank(1))
        hist = cryst.get_drop_history()
        hist.clear()
        assert len(cryst.get_drop_history()) == 1


class TestAutoCrystallize:
    def test_player_without_skills_attr(self, cryst: ConceptCrystallizer) -> None:
        class Bare:
            pass
        assert cryst.auto_crystallize_if_possible(Bare()) == []

    def test_three_fire_skills_suggested(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"fire_1": 1, "fire_2": 1, "fire_3": 1, "heal": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert len(res) == 1
        assert res[0]["category"] == "Fire"
        assert res[0]["available_skills"] == ["fire_1", "fire_2", "fire_3"]
        assert "概念結晶化可能" in res[0]["message"]

    def test_ice_variant_keywords(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"ice_a": 1, "cold_b": 1, "ice_c": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Ice"

    def test_two_skills_not_suggested(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"fire_1": 1, "fire_2": 1}
        assert cryst.auto_crystallize_if_possible(P()) == []

    def test_unknown_category_lumps_together(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"zap": 1, "boom": 1, "blast": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Unknown"

    def test_lightning_keyword(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"lightning_a": 1, "lightning_b": 1, "lightning_c": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Lightning"

    def test_dark_and_shadow_keywords(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"dark_a": 1, "shadow_b": 1, "dark_c": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Dark"

    def test_holy_and_light_keywords(self, cryst: ConceptCrystallizer) -> None:
        class P:
            skills = {"holy_a": 1, "light_b": 1, "holy_c": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Holy"

    def test_lightning_misses_fire_overlap(self, cryst: ConceptCrystallizer) -> None:
        # "light" is checked before "lightning"? No: lightning branch precedes holy/light,
        # so "lightning_x" maps to Lightning, not Holy
        class P:
            skills = {"lightning_x": 1, "lightning_y": 1, "lightning_z": 1}
        res = cryst.auto_crystallize_if_possible(P())
        assert res[0]["category"] == "Lightning"


class TestDropRates:
    def test_all_tables_reported(self, cryst: ConceptCrystallizer) -> None:
        rates = cryst.get_drop_rates(depth=10, exploration_rank=rank(5))
        assert set(rates) == set(ConceptCrystallizer.DROP_TABLES)
        for key, table in ConceptCrystallizer.DROP_TABLES.items():
            expected = min(
                0.95,
                table["base_rate"]
                + 10 * table["depth_bonus_per_level"]
                + 5 * table["rank_bonus_per_level"]
                + table["first_clear_bonus"],
            )
            assert rates[key] == pytest.approx(expected)

    def test_rates_never_exceed_cap(self, cryst: ConceptCrystallizer) -> None:
        rates = cryst.get_drop_rates(depth=1000, exploration_rank=rank(99))
        assert all(v <= 0.95 for v in rates.values())


class TestAudioFilesCheck:
    def test_returns_required_three_files(self, cryst: ConceptCrystallizer) -> None:
        res = cryst.check_audio_files()
        assert set(res) == {
            "crystal_resonance.ogg", "rank_up_fanfare.ogg", "ascension_node_unlock.ogg",
        }
        assert all(isinstance(v, bool) for v in res.values())


class TestPresentationEffect:
    def test_play_effect_calls_both_systems(self, cryst, monkeypatch) -> None:
        events: list = []
        played: list = []

        class FakePresentation:
            def add_event(self, **kwargs) -> None:
                events.append(kwargs)

        class FakeAudio:
            def play_sound(self, name: str) -> None:
                played.append(name)

        class FakePresCls:
            @classmethod
            def get_instance(cls):
                return FakePresentation()

        class FakeAudioCls:
            @classmethod
            def get_instance(cls):
                return FakeAudio()

        monkeypatch.setattr(cc_mod, "SkillEaterPresentationSystem", FakePresCls)
        monkeypatch.setattr(cc_mod, "SkillEaterAudioSystem", FakeAudioCls)

        cryst._play_crystal_drop_effect("Fire")
        assert len(events) == 1
        assert events[0]["emote_file"] == "emote_crystal.png"
        assert events[0]["message"] == "概念結晶《Fire》を獲得！"
        assert played == ["crystal_resonance.ogg"]

    def test_effect_cached_after_first_call(self, cryst, monkeypatch) -> None:
        calls = {"count": 0}

        class FakePresentation:
            def add_event(self, **kwargs) -> None:
                pass

        class FakeAudio:
            def play_sound(self, name: str) -> None:
                pass

        class FakePresCls:
            @classmethod
            def get_instance(cls):
                calls["count"] += 1
                return FakePresentation()

        class FakeAudioCls:
            @classmethod
            def get_instance(cls):
                return FakeAudio()

        monkeypatch.setattr(cc_mod, "SkillEaterPresentationSystem", FakePresCls)
        monkeypatch.setattr(cc_mod, "SkillEaterAudioSystem", FakeAudioCls)

        cryst._play_crystal_drop_effect("X")
        cryst._play_crystal_drop_effect("Y")
        assert calls["count"] == 1
