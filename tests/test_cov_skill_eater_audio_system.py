"""Coverage tests for skill_eater_audio_system (SkillEaterAudioSystem)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from skill_eater_audio_system import (
    REQUIRED_AUDIO_FILES,
    SOUND_CATEGORIES,
    VOLUME_CATEGORIES,
    SkillEaterAudioSystem,
)


@pytest.fixture
def audio_dir(tmp_path: Path) -> Path:
    d = tmp_path / "audio"
    d.mkdir()
    for name in ("victory.ogg", "fanfare.ogg", "magic_chime.ogg"):
        (d / name).write_bytes(b"OggS-fake")
    return d


@pytest.fixture
def audio(audio_dir: Path) -> SkillEaterAudioSystem:
    return SkillEaterAudioSystem(audio_dir=audio_dir, enable_real_audio=False)


@pytest.fixture(autouse=True)
def _reset_singleton():
    SkillEaterAudioSystem.reset_instance()
    yield
    SkillEaterAudioSystem.reset_instance()


class TestConstants:
    def test_required_files_have_fallbacks(self) -> None:
        assert REQUIRED_AUDIO_FILES["rank_up_fanfare.ogg"] == "victory.ogg"

    def test_volume_categories_defaults(self) -> None:
        assert VOLUME_CATEGORIES == {"sfx": 1.0, "bgm": 0.7, "ui": 0.8, "ambient": 0.5}

    def test_sound_categories_cover_steps(self) -> None:
        assert SOUND_CATEGORIES["footstep00.ogg"] == "sfx"
        assert SOUND_CATEGORIES["handleCoins.ogg"] == "ui"
        assert SOUND_CATEGORIES["heartbeat.ogg"] == "ambient"


class TestInit:
    def test_headless_init_no_pygame(self, audio_dir: Path) -> None:
        audio = SkillEaterAudioSystem(audio_dir=audio_dir, enable_real_audio=False)
        assert audio.has_pygame is False
        assert audio._pygame is None
        assert audio.category_volumes == VOLUME_CATEGORIES

    def test_default_audio_dir_is_repo_assets(self) -> None:
        audio = SkillEaterAudioSystem(audio_dir=None, enable_real_audio=False)
        assert audio.audio_dir.name == "audio"


class TestVolumeAndMute:
    def test_set_volume_clamps(self, audio: SkillEaterAudioSystem) -> None:
        audio.set_volume(1.5)
        assert audio.volume == 1.0
        audio.set_volume(-0.5)
        assert audio.volume == 0.0
        audio.set_volume(0.4)
        assert audio.volume == pytest.approx(0.4)

    def test_set_category_volume_known_and_unknown(self, audio: SkillEaterAudioSystem) -> None:
        audio.set_category_volume("bgm", 0.2)
        assert audio.category_volumes["bgm"] == pytest.approx(0.2)
        audio.set_category_volume("nonexistent", 0.9)
        assert "nonexistent" not in audio.category_volumes

    def test_mute_blocks_playback(self, audio: SkillEaterAudioSystem) -> None:
        audio.set_mute(True)
        assert audio.play_sound("rank_up_fanfare.ogg") is False
        assert audio.played_sounds == []
        audio.set_mute(False)
        assert audio.play_sound("rank_up_fanfare.ogg") is True
        assert audio.played_sounds == ["rank_up_fanfare.ogg"]


class TestPlaySound:
    def test_play_without_pygame_still_queues(self, audio: SkillEaterAudioSystem) -> None:
        assert audio.play_sound("crystal_resonance.ogg") is True
        assert audio.played_sounds == ["crystal_resonance.ogg"]

    def test_play_returns_true_even_if_file_missing_without_pygame(
        self, audio: SkillEaterAudioSystem
    ) -> None:
        # has_pygame=False の場合はキュー記録のみで True
        assert audio.play_sound("totally_unknown.ogg") is True

    def test_get_and_clear_played_sounds(self, audio: SkillEaterAudioSystem) -> None:
        audio.play_sound("a.ogg")
        audio.play_sound("b.ogg")
        sounds = audio.get_and_clear_played_sounds()
        assert sounds == ["a.ogg", "b.ogg"]
        assert audio.played_sounds == []
        assert audio.get_and_clear_played_sounds() == []


class TestResolveSoundPath:
    def test_direct_hit(self, audio: SkillEaterAudioSystem, audio_dir: Path) -> None:
        path = audio._resolve_sound_path("victory.ogg")
        assert path == audio_dir / "victory.ogg"

    def test_fallback_used(self, audio: SkillEaterAudioSystem, audio_dir: Path) -> None:
        path = audio._resolve_sound_path("rank_up_fanfare.ogg")
        assert path == audio_dir / "victory.ogg"

    def test_missing_without_fallback(self, audio: SkillEaterAudioSystem) -> None:
        assert audio._resolve_sound_path("nope.ogg") is None


class TestCheckAudioFiles:
    def test_all_present_via_fallback(self, audio: SkillEaterAudioSystem) -> None:
        res = audio.check_audio_files()
        assert res == {
            "rank_up_fanfare.ogg": True,
            "ascension_node_unlock.ogg": True,
            "crystal_resonance.ogg": True,
        }

    def test_all_missing_when_dir_empty(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        audio = SkillEaterAudioSystem(audio_dir=empty, enable_real_audio=False)
        res = audio.check_audio_files()
        assert all(v is False for v in res.values())


class TestSingleton:
    def test_get_instance_returns_same(self) -> None:
        a1 = SkillEaterAudioSystem.get_instance()
        a2 = SkillEaterAudioSystem.get_instance()
        assert a1 is a2

    def test_reset_instance_creates_new(self) -> None:
        a1 = SkillEaterAudioSystem.get_instance()
        SkillEaterAudioSystem.reset_instance()
        a2 = SkillEaterAudioSystem.get_instance()
        assert a1 is not a2


class _FakeSound:
    def __init__(self, path: str) -> None:
        self.path = path
        self.volume: float | None = None
        self.played = False

    def set_volume(self, v: float) -> None:
        self.volume = v

    def play(self) -> None:
        self.played = True


class _FakeMixer:
    def __init__(self, fail: bool = False) -> None:
        self.sounds: dict[str, _FakeSound] = {}
        self.fail = fail

    def init(self) -> None:
        if self.fail:
            raise RuntimeError("no audio device")

    def Sound(self, path: str) -> _FakeSound:
        if path not in self.sounds:
            self.sounds[path] = _FakeSound(path)
        return self.sounds[path]


class _FakePygame:
    def __init__(self, fail: bool = False) -> None:
        self.mixer = _FakeMixer(fail)


class TestPygamePaths:
    def test_play_with_fake_pygame_uses_cache_and_volume(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakePygame()
        monkeypatch.setitem(sys.modules, "pygame", fake)
        audio.has_pygame = True
        audio._pygame = fake
        audio.set_volume(0.5)
        audio.set_category_volume("ui", 0.8)

        assert audio.play_sound("rank_up_fanfare.ogg", category="ui") is True
        assert audio.played_sounds == ["rank_up_fanfare.ogg"]
        cached = fake.mixer.sounds
        assert len(cached) == 1
        snd = next(iter(cached.values()))
        assert snd.volume == pytest.approx(0.5 * 0.8)
        assert snd.played is True

    def test_play_caches_same_object(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakePygame()
        monkeypatch.setitem(sys.modules, "pygame", fake)
        audio.has_pygame = True
        audio._pygame = fake
        assert audio.play_sound("victory.ogg") is True
        assert audio.play_sound("victory.ogg") is True
        assert len(fake.mixer.sounds) == 1
        assert audio._sound_cache["victory.ogg"] is fake.mixer.sounds[str(audio.audio_dir / "victory.ogg")]

    def test_play_unknown_file_returns_false_with_pygame(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "pygame", _FakePygame())
        audio.has_pygame = True
        assert audio.play_sound("missing.ogg") is False

    def test_play_exception_returns_false(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "pygame", _FakePygame())
        audio.has_pygame = True

        class _Boom:
            def set_volume(self, v: float) -> None:
                raise RuntimeError("device error")

        # 実在ファイル名でキャッシュに例外を投げる偽サウンドを注入
        audio._sound_cache["victory.ogg"] = _Boom()
        assert audio.play_sound("victory.ogg") is False

    def test_init_pygame_failure_disables(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "pygame", _FakePygame(fail=True))
        audio._init_pygame()
        assert audio.has_pygame is False
        assert audio._pygame is None

    def test_get_pygame_headless_returns_none(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NAROU_HEADLESS", "1")
        assert audio._get_pygame() is None
        assert audio.has_pygame is False

    def test_get_pygame_lazy_init(
        self, audio: SkillEaterAudioSystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakePygame()
        monkeypatch.setitem(sys.modules, "pygame", fake)
        got = audio._get_pygame()
        assert got is fake
        assert audio.has_pygame is True

    def test_resolve_fallback_missing_returns_none(self, tmp_path: Path) -> None:
        # プライマリもフォールバックも存在しないケース
        empty = tmp_path / "empty"
        empty.mkdir()
        audio = SkillEaterAudioSystem(audio_dir=empty, enable_real_audio=False)
        assert audio._resolve_sound_path("rank_up_fanfare.ogg") is None
