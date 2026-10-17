"""Tests for UI / FX / audio modules with low coverage.

Covers:
- sound_manager.py    : SoundManager / BGMManager / AmbientLayer / audio helpers
- fx_manager.py       : FXManager particle/effect spawning and lifecycle
- visual_fx_system.py : lighting, camera shake, sprite deformation, env FX, time-of-day
- ui_fx_systems.py    : FloatingText / Particle / ScreenShake / GaugeBar / notifications
- ui_event_panel.py   : event panel data providers
- ui_skill_tree.py    : SkillTreeRenderer view models and ASCII rendering
- ui_title_display.py : title data providers
- ui_ranking_panel.py : ranking data providers
- journal_ui.py       : JournalUI rendering / navigation

External backends (pygame mixer, winsound, external audio players, tcod
consoles) are mocked so the whole suite runs headless.
"""

from __future__ import annotations

import io
import logging
import sys
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fx_manager  # noqa: E402
import journal_ui  # noqa: E402
import sound_manager  # noqa: E402
import ui_event_panel  # noqa: E402
import ui_fx_systems  # noqa: E402
import ui_ranking_panel  # noqa: E402
import ui_skill_tree  # noqa: E402
import ui_title_display  # noqa: E402
import visual_fx_system  # noqa: E402
from main_quest_system import QuestStatus  # noqa: E402
from time_system import TimePhase  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AUDIO_CONFIG = str(ROOT / "data" / "audio_config.yaml")


# ===========================================================================
# sound_manager.py
# ===========================================================================


@pytest.fixture(autouse=True)
def _reset_sound_manager_state():
    """Class-level SoundManager state and module globals leak between tests."""
    yield
    sound_manager.SoundManager.set_enabled(True)
    sound_manager.SoundManager._audio_initialized = False
    sound_manager.SoundManager._se_cache.clear()
    sound_manager.SoundManager._se_files.clear()
    sound_manager.SoundManager._terrain_footstep_map.clear()
    sound_manager.SoundManager._terrain_footstep_files.clear()
    sound_manager._player_failures.clear()
    sound_manager._player_errors_reported.clear()
    sound_manager._missing_backend_reported = False


def _run_play_se_worker(se_type: str) -> None:
    """Run SoundManager.play_se and execute its worker thread synchronously."""
    with patch.object(sound_manager.threading, "Thread") as thread_mock:
        sound_manager.SoundManager.play_se(se_type)
        assert thread_mock.called, "play_se should spawn a worker thread"
        thread_mock.call_args.kwargs["target"]()


class TestSoundManagerToggles:
    def test_default_enabled(self):
        assert sound_manager.SoundManager.is_enabled() is True

    def test_set_enabled_mute_toggling(self):
        sound_manager.SoundManager.set_enabled(False)
        assert sound_manager.SoundManager.is_enabled() is False
        with patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager.SoundManager.play_se("hit")
            assert thread_mock.call_count == 0
        sound_manager.SoundManager.set_enabled(True)
        with patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager.SoundManager.play_se("hit")
            assert thread_mock.call_count == 1

    def test_play_bgm_ogg_respects_mute(self):
        with patch.object(sound_manager.SoundManager, "bgm_manager") as bgm, \
             patch.object(sound_manager.SoundManager, "_enabled", False):
            sound_manager.SoundManager.play_bgm_ogg("dungeon")
            bgm.play_bgm.assert_not_called()

    def test_update_ambient_ogg_respects_mute(self):
        with patch.object(sound_manager.SoundManager, "ambient_layer") as amb, \
             patch.object(sound_manager.SoundManager, "_enabled", False):
            sound_manager.SoundManager.update_ambient_ogg("town")
            amb.update_ambient.assert_not_called()


class TestSoundManagerPlayback:
    def test_play_se_hit_dispatches_single_tone(self):
        with patch.object(sound_manager.SoundManager, "_play_tone") as tone:
            _run_play_se_worker("hit")
        tone.assert_called_once_with(220, 40)

    def test_play_se_kill_dispatches_two_tones(self):
        with patch.object(sound_manager.SoundManager, "_play_tone") as tone:
            _run_play_se_worker("kill")
        assert [c.args for c in tone.call_args_list] == [(180, 50), (130, 80)]

    def test_play_se_level_up_arpeggio(self):
        with patch.object(sound_manager.SoundManager, "_play_tone") as tone:
            _run_play_se_worker("level_up")
        assert [c.args[0] for c in tone.call_args_list] == [523, 659, 784, 1046]

    def test_play_se_fanfare_arpeggio(self):
        with patch.object(sound_manager.SoundManager, "_play_tone") as tone:
            _run_play_se_worker("fanfare")
        assert [c.args[0] for c in tone.call_args_list] == [523, 659, 784, 1046, 1318]

    def test_play_se_silent_types_spawn_no_tone(self):
        with patch.object(sound_manager.SoundManager, "_play_tone") as tone:
            _run_play_se_worker("step")
            _run_play_se_worker("totally_unknown")
        assert tone.call_count == 0

    def test_play_tone_without_winsound_streams_wav_to_player(self):
        # HAS_WINSOUND is False on this platform: the tone is synthesized as a
        # WAV file and handed to the resolved external player.
        with patch.object(sound_manager, "resolve_audio_player", return_value="/usr/bin/pw-play"), \
             patch.object(sound_manager, "_spawn_player") as spawn:
            sound_manager.SoundManager._play_tone(440, 50)
        assert spawn.call_count == 1
        command = spawn.call_args.args[0]
        assert command[0] == "/usr/bin/pw-play"
        assert command[1] == "--volume=1.0"
        cleanup_path = spawn.call_args.kwargs["cleanup"]
        assert cleanup_path.endswith(".wav")

    def test_play_wav_bytes_without_any_player_reports_once(self, caplog):
        with caplog.at_level(logging.ERROR, logger="sound_manager"), \
             patch.object(sound_manager, "resolve_audio_player", return_value=None):
            sound_manager.SoundManager._play_wav_bytes(b"RIFF-fake")
            sound_manager.SoundManager._play_wav_bytes(b"RIFF-fake")
        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(errors) == 1

    def test_play_bgm_and_update_ambient_delegate(self):
        with patch.object(sound_manager.SoundManager, "bgm_manager") as bgm, \
             patch.object(sound_manager.SoundManager, "ambient_layer") as amb:
            bgm.play_bgm.return_value = "bgm-ok"
            amb.update_ambient.return_value = "amb-ok"
            assert sound_manager.SoundManager.play_bgm("dungeon") == "bgm-ok"
            bgm.play_bgm.assert_called_once_with("dungeon", fade_in=True)
            assert sound_manager.SoundManager.update_ambient("town") == "amb-ok"
            amb.update_ambient.assert_called_once_with("town")

    def test_play_ui_sound_maps_to_se_ids(self):
        with patch.object(sound_manager.SoundManager, "play_se_ogg") as se:
            sound_manager.SoundManager.play_ui_sound("notify")
            se.assert_called_with("ui_notify", 0.7)
            sound_manager.SoundManager.play_ui_sound("hover", volume=0.2)
            se.assert_called_with("ui_hover", 0.2)
            sound_manager.SoundManager.play_ui_sound("unknown_kind")
            se.assert_called_with("ui_click", 0.7)

    def test_stop_bgm_clears_current_track_without_backend(self):
        sound_manager.SoundManager.bgm_manager.current_track = "bgm_dungeon_dark"
        with patch.object(sound_manager, "HAS_AUDIO_BACKEND", False):
            sound_manager.SoundManager.stop_bgm()
        assert sound_manager.SoundManager.bgm_manager.current_track is None

    def test_stop_bgm_fades_backend_when_available(self):
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend):
            sound_manager.SoundManager.stop_bgm(fade_out=2.5)
        backend.stop_bgm.assert_called_once_with(2.5)


class TestSoundManagerOggPack:
    def test_init_audio_pack_disabled_flag_does_nothing(self):
        sound_manager.SoundManager._audio_initialized = False
        with patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "is_enabled", return_value=False), \
             patch.object(sound_manager, "preload_all_audio") as preload:
            sound_manager.SoundManager._init_audio_pack()
        assert sound_manager.SoundManager._audio_initialized is False
        preload.assert_not_called()

    def test_init_audio_pack_success_preloads_manifest(self):
        sound_manager.SoundManager._audio_initialized = False
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager, "preload_all_audio", return_value=7) as preload:
            sound_manager.SoundManager._init_audio_pack()
        preload.assert_called_once_with("assets/audio/manifest.csv")
        assert sound_manager.SoundManager._audio_initialized is True

    def test_load_se_mappings_reads_config(self):
        sound_manager.SoundManager._se_cache.clear()
        sound_manager.SoundManager._se_files.clear()
        sound_manager.SoundManager._load_se_mappings()
        assert sound_manager.SoundManager._se_files["ui_click"] == "metalClick.ogg"
        assert sound_manager.SoundManager._se_cache["ui_click"] == "se_metalclick"
        assert sound_manager.SoundManager._se_cache["ui_notify"] == "se_handlecoins"

    def test_play_se_ogg_falls_back_when_pack_disabled(self):
        with patch.object(sound_manager, "is_enabled", return_value=False), \
             patch.object(sound_manager.SoundManager, "play_se") as play_se:
            sound_manager.SoundManager.play_se_ogg("ui_click")
        play_se.assert_called_once_with("ui_click")

    def test_play_se_ogg_plays_via_backend(self):
        backend = MagicMock()
        backend.is_available = True
        sound_manager.SoundManager._se_cache["ui_click"] = "se_metalclick"
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager.SoundManager.play_se_ogg("ui_click", volume=0.4)
            thread_mock.call_args.kwargs["target"]()
        backend.play_sound.assert_called_once_with("se_metalclick", volume=0.4)

    def test_play_se_ogg_unknown_se_type_falls_back(self):
        backend = MagicMock()
        backend.is_available = True
        sound_manager.SoundManager._se_cache.clear()
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.SoundManager, "play_se") as play_se:
            sound_manager.SoundManager.play_se_ogg("mystery_sound")
        play_se.assert_called_once_with("mystery_sound")

    def test_play_se_ogg_backend_unavailable_uses_mapped_asset(self):
        backend = MagicMock()
        backend.is_available = False
        sound_manager.SoundManager._se_files["hit"] = "hit.ogg"
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.SoundManager, "_play_mapped_asset", return_value=True) as mapped:
            sound_manager.SoundManager.play_se_ogg("hit")
        mapped.assert_called_once_with("hit", 1.0)

    def test_play_se_ogg_backend_unavailable_asset_missing_falls_back(self):
        backend = MagicMock()
        backend.is_available = False
        sound_manager.SoundManager._se_files["hit"] = "hit.ogg"
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.SoundManager, "_play_mapped_asset", return_value=False), \
             patch.object(sound_manager.SoundManager, "play_se") as play_se:
            sound_manager.SoundManager.play_se_ogg("hit")
        play_se.assert_called_once_with("hit")

    def test_play_mapped_asset_resolves_and_plays(self):
        sound_manager.SoundManager._se_files["hit"] = "hit.ogg"
        with patch.object(sound_manager, "resolve_audio_asset", return_value="assets/audio/hit.ogg") as resolve, \
             patch.object(sound_manager, "play_audio_file", return_value=True) as play:
            assert sound_manager.SoundManager._play_mapped_asset("hit", 0.7) is True
        resolve.assert_called_once_with("hit.ogg")
        play.assert_called_once_with("assets/audio/hit.ogg", 0.7)

    def test_play_footstep_disabled_falls_back_to_step(self):
        with patch.object(sound_manager, "is_enabled", return_value=False), \
             patch.object(sound_manager.SoundManager, "play_se") as play_se:
            sound_manager.SoundManager.play_footstep("grass")
        play_se.assert_called_once_with("step")

    def test_play_footstep_backend_unavailable_without_asset(self):
        backend = MagicMock()
        backend.is_available = False
        sound_manager.SoundManager._terrain_footstep_files.clear()
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.SoundManager, "play_se") as play_se:
            sound_manager.SoundManager.play_footstep("grass")
        play_se.assert_called_once_with("step")

    def test_play_footstep_plays_terrain_asset(self):
        backend = MagicMock()
        backend.is_available = False
        sound_manager.SoundManager._terrain_footstep_files["snow"] = "snowStep.ogg"
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager, "resolve_audio_asset", return_value="assets/audio/snowStep.ogg"), \
             patch.object(sound_manager, "play_audio_file", return_value=True) as play:
            sound_manager.SoundManager.play_footstep("snow", volume=0.6)
        play.assert_called_once_with("assets/audio/snowStep.ogg", 0.6)

    def test_play_footstep_via_backend(self):
        backend = MagicMock()
        backend.is_available = True
        sound_manager.SoundManager._terrain_footstep_map["snow"] = "footstep_snow"
        sound_manager.SoundManager._se_cache["footstep_snow"] = "se_snowstep"
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager.SoundManager.play_footstep("snow", volume=0.5)
            thread_mock.call_args.kwargs["target"]()
        backend.play_sound.assert_called_once_with("se_snowstep", volume=0.5)

    def test_play_bgm_ogg_with_existing_file(self):
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.os.path, "exists", side_effect=[False, True]):
            sound_manager.SoundManager.play_bgm_ogg("dungeon", fade_in=2.0, loop=False)
        # First exists() probe (raw name) failed, ".ogg" was appended, second
        # probe succeeded -> backend received the .ogg path.
        backend.play_bgm.assert_called_once_with(
            "assets/audio/bgm_dungeon_dark.ogg", volume=0.7, loop=False, fade_in=2.0
        )

    def test_play_bgm_ogg_missing_file_falls_back_to_tone_bgm(self):
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.os.path, "exists", return_value=False):
            sound_manager.SoundManager.play_bgm_ogg("dungeon")
        backend.play_bgm.assert_not_called()
        assert sound_manager.SoundManager.bgm_manager.current_track == "bgm_dungeon_dark"

    def test_update_ambient_ogg_selects_depth_variant(self):
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.os.path, "exists", return_value=True):
            sound_manager.SoundManager.update_ambient_ogg("dungeon", depth=12)
            assert sound_manager.SoundManager.ambient_layer.current_ambient == "dungeon_deep"
            backend.play_bgm.assert_called_once()
            assert backend.play_bgm.call_args.kwargs["volume"] == 0.3
            assert backend.play_bgm.call_args.kwargs["loop"] is True

            backend.play_bgm.reset_mock()
            sound_manager.SoundManager.update_ambient_ogg("dungeon", depth=6)
            assert sound_manager.SoundManager.ambient_layer.current_ambient == "dungeon_shallow"

            backend.play_bgm.reset_mock()
            sound_manager.SoundManager.update_ambient_ogg("town", depth=0)
            assert sound_manager.SoundManager.ambient_layer.current_ambient == "town_day"

    def test_update_ambient_ogg_missing_file_falls_back(self):
        backend = MagicMock()
        backend.is_available = True
        with patch.object(sound_manager, "is_enabled", return_value=True), \
             patch.object(sound_manager, "HAS_AUDIO_BACKEND", True), \
             patch.object(sound_manager, "get_audio_backend", return_value=backend), \
             patch.object(sound_manager.SoundManager, "_init_audio_pack"), \
             patch.object(sound_manager.os.path, "exists", return_value=False), \
             patch.object(sound_manager.SoundManager, "ambient_layer") as amb:
            sound_manager.SoundManager.update_ambient_ogg("town")
        backend.play_bgm.assert_not_called()
        amb.update_ambient.assert_called_once_with("town")


class TestBGMAndAmbientManagers:
    def test_bgm_play_and_crisis_cycle(self):
        bgm = sound_manager.BGMManager(AUDIO_CONFIG)
        msg = bgm.play_bgm("dungeon")
        assert msg == "Playing BGM [bgm_dungeon_dark] (Theme: dungeon, Volume: 0.7)"
        assert bgm.current_track == "bgm_dungeon_dark"
        assert bgm.current_theme == "dungeon"

        crisis = bgm.check_crisis_trigger(20, 100)
        assert crisis == "Playing BGM [bgm_combat_crisis] (Theme: crisis, Volume: 0.9)"
        assert bgm.is_crisis is True
        # Staying in crisis does not re-trigger.
        assert bgm.check_crisis_trigger(20, 100) is None
        # Recovering restores the previous theme.
        restore = bgm.check_crisis_trigger(95, 100)
        assert restore.startswith("Playing BGM [bgm_dungeon_dark]")
        assert bgm.is_crisis is False
        assert bgm.check_crisis_trigger(100, 100) is None
        # Division-by-zero guard for max_hp <= 0.
        assert bgm.check_crisis_trigger(50, 0) is None

    def test_bgm_without_config_file_uses_defaults(self):
        bgm = sound_manager.BGMManager(str(ROOT / "no_such_config.yaml"))
        msg = bgm.play_bgm("town")
        assert msg == "Playing BGM [bgm_town] (Theme: town, Volume: 0.8)"
        assert bgm.current_track == "bgm_town"

    def test_ambient_layer_switches_sound_by_location(self):
        amb = sound_manager.AmbientLayer(AUDIO_CONFIG)
        assert amb.update_ambient("dungeon") == "Active Ambient: [amb_water_drop] (Location: dungeon)"
        assert amb.current_ambient == "amb_water_drop"
        assert amb.volume == 0.5
        # Unknown location falls back to a derived sound id and default volume.
        assert amb.update_ambient("volcano") == "Active Ambient: [amb_volcano] (Location: volcano)"
        assert amb.volume == 0.5

    def test_sound_manager_with_mocked_pygame_mixer(self):
        # The audio stack must keep working when pygame is a headless mock.
        pygame_mock = MagicMock()
        with patch.dict(sys.modules, {"pygame": pygame_mock}):
            import pygame  # noqa: F401

            sound_manager.SoundManager.set_enabled(True)
            msg = sound_manager.SoundManager.play_bgm("town")
            assert msg.startswith("Playing BGM [")
            assert sound_manager.SoundManager.is_enabled() is True


class TestAudioHelpers:
    def test_resolve_audio_asset(self, tmp_path, monkeypatch):
        (tmp_path / "se_hit.ogg").write_bytes(b"OggS")
        (tmp_path / "explicit.wav").write_bytes(b"RIFF")
        monkeypatch.setattr(sound_manager, "AUDIO_ASSET_DIR", str(tmp_path))
        assert sound_manager.resolve_audio_asset("se_hit") == str(tmp_path / "se_hit.ogg")
        assert sound_manager.resolve_audio_asset("explicit.wav") == str(tmp_path / "explicit.wav")
        # Missing file and empty name yield None (file existence handling).
        assert sound_manager.resolve_audio_asset("missing_effect") is None
        assert sound_manager.resolve_audio_asset("") is None

    def test_resolve_audio_player_respects_extension_support(self, monkeypatch):
        monkeypatch.setattr(
            sound_manager.shutil, "which", lambda n: "/usr/bin/aplay" if n == "aplay" else None
        )
        # aplay cannot play OGG -> no candidate.
        assert sound_manager.resolve_audio_player(".ogg") is None
        assert sound_manager.resolve_audio_player(".wav") == "/usr/bin/aplay"
        # Players that failed before are skipped.
        sound_manager._player_failures.add("aplay")
        assert sound_manager.resolve_audio_player(".wav") is None

    def test_resolve_audio_player_prefers_first_available(self, monkeypatch):
        monkeypatch.setattr(sound_manager.shutil, "which", lambda n: f"/usr/bin/{n}")
        assert sound_manager.resolve_audio_player(".ogg") == "/usr/bin/ffplay"

    def test_build_player_command_variants(self):
        assert sound_manager.build_player_command("/usr/bin/pw-play", "s.ogg", 0.5) == [
            "/usr/bin/pw-play", "--volume=0.5", "s.ogg",
        ]
        assert sound_manager.build_player_command("/usr/bin/paplay", "s.ogg", 0.5) == [
            "/usr/bin/paplay", "--volume=32768", "s.ogg",
        ]
        assert sound_manager.build_player_command("/usr/bin/ffplay", "s.ogg", 0.5) == [
            "/usr/bin/ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", "50", "s.ogg",
        ]
        assert sound_manager.build_player_command("/usr/bin/afplay", "s.ogg", 0.5) == [
            "/usr/bin/afplay", "-v", "0.50", "s.ogg",
        ]
        assert sound_manager.build_player_command("/usr/bin/aplay", "s.wav") == [
            "/usr/bin/aplay", "-q", "s.wav",
        ]
        assert sound_manager.build_player_command("/usr/bin/custom", "s.ogg") == [
            "/usr/bin/custom", "s.ogg",
        ]

    def test_build_player_command_clamps_volume(self):
        assert "--volume=1.0" in sound_manager.build_player_command("/usr/bin/pw-play", "s.ogg", 5.0)
        assert "--volume=0.0" in sound_manager.build_player_command("/usr/bin/pw-play", "s.ogg", -1.0)

    def test_render_tone_wav_produces_valid_wav(self):
        payload = sound_manager.render_tone_wav(440, 100, sample_rate=8000)
        assert payload[:4] == b"RIFF"
        with wave.open(io.BytesIO(payload)) as wav:
            assert wav.getframerate() == 8000
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getnframes() == 800

    def test_play_audio_file_dispatches_to_player(self):
        with patch.object(sound_manager, "resolve_audio_player", return_value="/usr/bin/aplay"), \
             patch.object(sound_manager, "_spawn_player") as spawn:
            assert sound_manager.play_audio_file("hit.wav", 0.5) is True
        assert spawn.call_args.args[0] == ["/usr/bin/aplay", "-q", "hit.wav"]

    def test_play_audio_file_empty_path(self):
        assert sound_manager.play_audio_file(None) is False
        assert sound_manager.play_audio_file("") is False

    def test_play_audio_file_without_player(self):
        with patch.object(sound_manager, "resolve_audio_player", return_value=None):
            assert sound_manager.play_audio_file("hit.wav") is False

    def test_spawn_player_failure_invokes_callback(self):
        with patch.object(sound_manager.subprocess, "Popen", side_effect=OSError("boom")):
            called = []
            sound_manager._spawn_player(["nope"], on_failure=lambda: called.append(1))
        assert called == [1]

    def test_spawn_player_cleans_up_temp_file(self, tmp_path):
        target = tmp_path / "tone.wav"
        target.write_bytes(b"x")
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = (None, b"")
        with patch.object(sound_manager.subprocess, "Popen", return_value=proc), \
             patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager._spawn_player(["player"], cleanup=str(target))
            thread_mock.call_args.kwargs["target"]()
        assert not target.exists()

    def test_spawn_player_reports_nonzero_return_code(self, tmp_path, caplog):
        target = tmp_path / "tone.wav"
        target.write_bytes(b"x")
        proc = MagicMock()
        proc.returncode = 3
        proc.communicate.return_value = (None, b"device busy")
        with caplog.at_level(logging.ERROR, logger="sound_manager"), \
             patch.object(sound_manager.subprocess, "Popen", return_value=proc), \
             patch.object(sound_manager.threading, "Thread") as thread_mock:
            sound_manager._spawn_player(["/usr/bin/aplay"], cleanup=str(target))
            thread_mock.call_args.kwargs["target"]()
        assert any("aplay" in r.getMessage() for r in caplog.records)
        assert not target.exists()

    def test_report_player_error_only_once_per_player(self, caplog):
        with caplog.at_level(logging.ERROR, logger="sound_manager"):
            sound_manager._report_player_error("aplay", 3, "x")
            sound_manager._report_player_error("aplay", 3, "x")
            sound_manager._report_player_error("other", 2, "y")
        assert len(caplog.records) == 2

    def test_report_missing_backend_only_once(self, caplog):
        with caplog.at_level(logging.ERROR, logger="sound_manager"):
            sound_manager.report_missing_audio_backend()
            sound_manager.report_missing_audio_backend()
        assert len(caplog.records) == 1


# ===========================================================================
# fx_manager.py
# ===========================================================================


class TestFXManagerCore:
    def test_initial_state(self):
        fx = fx_manager.FXManager()
        assert fx.floating_texts == []
        assert fx.particles == []
        assert fx.hit_stop_frames == 0
        assert fx.glitch_duration == 0
        assert fx.event_bus is None
        assert fx.screen_shake.is_active is False

    def test_event_bus_registration(self):
        bus = MagicMock()
        fx = fx_manager.FXManager(bus)
        subscribed = {c.args[0]: c.args[1] for c in bus.subscribe.call_args_list}
        assert set(subscribed) == {"damage_dealt", "entity_killed", "trap_triggered"}
        assert subscribed["damage_dealt"] == fx._on_damage_dealt
        assert subscribed["entity_killed"] == fx._on_entity_killed
        assert subscribed["trap_triggered"] == fx._on_trap_triggered

    def test_add_floating_text(self):
        fx = fx_manager.FXManager()
        fx.add_floating_text("-12", 3.0, 4.0, (255, 100, 100))
        (ft,) = fx.floating_texts
        assert ft.text == "-12"
        assert (ft.x, ft.y) == (3.0, 4.0)
        assert ft.color == (255, 100, 100)

    def test_spawn_explosion(self):
        fx = fx_manager.FXManager()
        fx.spawn_explosion(1.5, 2.5, count=3)
        assert len(fx.particles) == 3
        for p in fx.particles:
            assert p.char == "💥"
            assert p.color == (255, 180, 50)
            assert p.life == 3

    def test_spawn_shockwave_ring(self):
        fx = fx_manager.FXManager()
        fx.spawn_shockwave(0, 0, color=(10, 20, 30))
        assert len(fx.particles) == 8
        for p in fx.particles:
            assert p.char == "*"
            assert p.color == (10, 20, 30)
            assert p.life == 5

    def test_trigger_shake_and_hit_stop_and_glitch(self):
        fx = fx_manager.FXManager()
        fx.trigger_shake(intensity=2.0, duration=5, direction=(1, -1))
        assert fx.screen_shake.is_active
        assert fx.screen_shake.duration == 5
        assert fx.screen_shake.intensity == 2.0
        assert fx.screen_shake.direction == (1, -1)
        fx.trigger_hit_stop(duration=9)
        assert fx.hit_stop_frames == 9
        fx.trigger_glitch(duration=7)
        assert fx.glitch_duration == 7

    def test_update_removes_expired_effects(self):
        fx = fx_manager.FXManager()
        fx.add_floating_text("hi", 0, 0, (255, 255, 255))
        fx.floating_texts[0].life = 1
        fx.spawn_explosion(0, 0, count=1)
        fx.particles[0].life = 1
        fx.trigger_shake(duration=1)
        fx.update()
        assert fx.floating_texts == []
        assert fx.particles == []
        assert fx.screen_shake.is_active is False

    def test_update_hit_stop_freezes_other_effects(self):
        fx = fx_manager.FXManager()
        fx.spawn_explosion(1, 1, count=2)
        fx.trigger_hit_stop(duration=2)
        fx.update()
        assert fx.hit_stop_frames == 1
        fx.update()
        assert fx.hit_stop_frames == 0
        # During hit stop the particles were never ticked.
        fx.update()
        assert len(fx.particles) == 2
        assert all(p.life == 2 for p in fx.particles)

    def test_update_glitch_countdown(self):
        fx = fx_manager.FXManager()
        fx.trigger_glitch(duration=2)
        fx.update()
        assert fx.glitch_duration == 1
        fx.update()
        assert fx.glitch_duration == 0
        fx.update()
        assert fx.glitch_duration == 0

    def test_event_handlers_ignore_non_dict_payloads(self):
        fx = fx_manager.FXManager()
        fx._on_damage_dealt("bad")
        fx._on_entity_killed(None)
        fx._on_trap_triggered(42)
        assert fx.floating_texts == []
        assert fx.particles == []
        assert fx.screen_shake.is_active is False

    def test_on_damage_dealt_popup_and_blood(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx._on_damage_dealt({"damage": 12, "x": 3, "y": 4})
        (ft,) = fx.floating_texts
        assert ft.text == "-12"
        assert (ft.x, ft.y) == (3, pytest.approx(3.8))
        assert ft.color == (255, 100, 100)
        # Non-crit: one blood tile splatter only.
        assert len(fx.particles) == 1
        assert fx.particles[0].tile_id == fx_manager.get_effect_tile_id("blood")

    def test_on_damage_dealt_crit_bundle(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx._on_damage_dealt({"damage": 30, "x": 5, "y": 5, "is_crit": True})
        assert fx.floating_texts[0].color == (255, 230, 80)
        assert fx.hit_stop_frames == 6
        assert fx.screen_shake.is_active
        # blood(1) + 4 directional splatter + shockwave(8) + sparkle(8) + magic cast(4)
        assert len(fx.particles) == 25

    def test_on_entity_killed_effects(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx._on_entity_killed({"x": 2, "y": 2, "monster_type": "dragon"})
        assert fx.screen_shake.is_active
        # explosion(3) + blood pool(1+6) + death frame(1) + smoke fade(3)
        assert len(fx.particles) == 14

    def test_on_trap_triggered_effects(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=False):
            fx._on_trap_triggered({"damage": 7, "x": 1, "y": 2})
        (ft,) = fx.floating_texts
        assert ft.text == "-7"
        assert ft.color == (255, 80, 80)
        assert fx.screen_shake.is_active


class TestFXManagerSpawners:
    def test_spawn_tile_effect_with_tile_ids(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_tile_effect(1, 1, "fire", count=3, life=9, vx=0.5, vy=-0.5)
        assert len(fx.particles) == 3
        p = fx.particles[0]
        assert p.char == ""
        assert p.tile_id == fx_manager.get_effect_tile_id("fire")
        assert p.life == 9
        assert (p.vx, p.vy) == (0.5, -0.5)

    def test_spawn_tile_effect_fallbacks_when_gfx_disabled(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=False):
            fx.spawn_tile_effect(1, 1, "explosion", count=2)
            assert len(fx.particles) == 2
            fx.spawn_tile_effect(1, 1, "fire", count=2)
            assert len(fx.particles) == 4
            fx.spawn_tile_effect(1, 1, "magic_cast", count=2)
            assert len(fx.particles) > 4
            # Unknown effect types degrade to a no-op.
            before = len(fx.particles)
            fx.spawn_tile_effect(1, 1, "not_a_real_effect", count=2)
            assert len(fx.particles) == before

    @pytest.mark.parametrize(
        "method,count", [
            ("spawn_magic_cast", 3),
            ("spawn_fire_effect", 5),
            ("spawn_ice_effect", 4),
            ("spawn_lightning_effect", 3),
            ("spawn_poison_effect", 6),
            ("spawn_heal_effect", 8),
            ("spawn_teleport_effect", 10),
            ("spawn_explosion_effect", 12),
            ("spawn_sparkle_effect", 5),
            ("spawn_smoke_effect", 6),
        ],
    )
    def test_named_tile_effects_spawn_expected_counts(self, method, count):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            getattr(fx, method)(1, 1)
        assert len(fx.particles) == count
        assert all(p.tile_id for p in fx.particles)

    def test_spawn_slash_effect_follows_direction(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_slash_effect(0, 0, direction=(2, 0), count=3)
        assert len(fx.particles) == 3
        xs = [p.x for p in fx.particles]
        assert xs == [pytest.approx(v) for v in (0.0, 1.0, 2.0)]

    def test_spawn_shockwave_effect_ring(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_shockwave_effect(3, 3, count=16)
        assert len(fx.particles) == 16
        assert all((p.vx, p.vy) == (0, 0) for p in fx.particles)

    def test_spawn_emotion_particles(self):
        fx = fx_manager.FXManager()
        fx.spawn_emotion_particles(0, 0, "angry")
        assert len(fx.particles) == 5
        assert all(p.char in ("💢", "🔥") for p in fx.particles)
        # Unknown emotion degrades to the "confused" set.
        fx.spawn_emotion_particles(0, 0, "meh")
        assert len(fx.particles) == 9

    def test_spawn_material_particles(self):
        fx = fx_manager.FXManager()
        fx.spawn_material_particles(0, 0, "crystal", count=4)
        assert len(fx.particles) == 4
        assert all(p.char in ("✦", "✧", "✨") for p in fx.particles)
        # Unknown material degrades to the default set.
        fx.spawn_material_particles(0, 0, "unobtanium", count=2)
        assert len(fx.particles) == 6

    def test_spawn_loot_sparkle_gated(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=False):
            fx.spawn_loot_sparkle(0, 0)
        assert fx.particles == []
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_loot_sparkle(0, 0, rarity="legendary")
        # main sparkle(6) + 4 rising particles
        assert len(fx.particles) == 10

    def test_water_splash_and_lava_bubble_gated(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=False):
            fx.spawn_water_splash(0, 0, count=3)
            fx.spawn_lava_bubble(0, 0, count=3)
        assert fx.particles == []
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_water_splash(0, 0, count=3)
            fx.spawn_lava_bubble(0, 0, count=2)
        assert len(fx.particles) == 5

    def test_spawn_footstep_particles_gated(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=False):
            fx.spawn_footstep_particles(0, 0, "stone")
        assert fx.particles == []
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_footstep_particles(0, 0, "stone")
            assert len(fx.particles) == 2
            fx.spawn_footstep_particles(0, 0, "water", direction=(1, 0))
            assert len(fx.particles) == 3
            fx.spawn_footstep_particles(0, 0, "grass")
            assert len(fx.particles) == 4
            fx.spawn_footstep_particles(0, 0, "whatever")
            assert len(fx.particles) == 5

    def test_spawn_blood_splatter_directional_on_kill(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_blood_splatter(5, 5, is_kill=True)
        # center + 4 directional
        assert len(fx.particles) == 5

    def test_spawn_blood_pool_layout(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_blood_pool(2, 2)
        # pool + 6 surrounding splatter, all long-lived
        assert len(fx.particles) == 7
        assert all(p.life >= 60 for p in fx.particles)

    def test_spawn_death_animation_maps_monster_types(self):
        fx = fx_manager.FXManager()
        with patch.object(fx_manager, "is_enabled", return_value=True):
            fx.spawn_death_animation(0, 0, "slime")
        # death frame(1) + smoke fade(3)
        assert len(fx.particles) == 4
        assert fx.particles[0].tile_id == fx_manager.get_effect_tile_id("smoke")


# ===========================================================================
# visual_fx_system.py
# ===========================================================================


class TestVisualFxLighting:
    def test_light_source_radius_without_flicker(self):
        ls = visual_fx_system.LightSource(x=1, y=2, base_radius=42.0, flicker=False)
        assert ls.get_current_radius(123) == 42.0

    def test_light_source_radius_flicker_range(self):
        ls = visual_fx_system.LightSource(x=1, y=2, base_radius=60.0, flicker=True)
        for ticks in range(40):
            radius = ls.get_current_radius(ticks)
            assert 5.0 <= radius <= 60.0 + 4.5

    def test_draw_light_parameters(self):
        lm = visual_fx_system.LightingManager()
        mask = lm.draw_light(4.0, 6.0, radius=30.0, intensity=0.8)
        assert mask == {
            "center": (4.0, 6.0),
            "radius": 30.0,
            "intensity": 0.8,
            "blend_mode": "cutout_additive",
        }

    def test_generate_frame_lighting(self):
        lm = visual_fx_system.LightingManager(ambient_darkness=220)
        lm.add_light(visual_fx_system.LightSource(x=10, y=12, base_radius=40.0, flicker=False))
        frame = lm.generate_frame_lighting(player_x=5, player_y=5, ticks=0)
        assert frame["ambient_alpha"] == 220
        assert len(frame["light_cutouts"]) == 2
        player_mask = frame["light_cutouts"][0]
        assert player_mask["center"] == (5, 5)
        assert player_mask["radius"] == pytest.approx(75.0)  # sin(0) term vanishes
        assert frame["light_cutouts"][1]["radius"] == 40.0


class TestVisualFxCameraAndSprites:
    def test_camera_shake_lifecycle(self):
        cam = visual_fx_system.CameraShakeManager()
        assert cam.update() == (0.0, 0.0)
        cam.trigger_shake(duration=3, magnitude=2.0)
        for _ in range(3):
            ox, oy = cam.update()
            assert -2.0 <= ox <= 2.0
            assert -2.0 <= oy <= 2.0
        assert cam.shake_duration == 0
        assert cam.update() == (0.0, 0.0)

    def test_sprite_deformation_cycle(self):
        sprite = visual_fx_system.SpriteDeformation()
        sprite.on_windup()
        assert (sprite.scale_x, sprite.scale_y) == (0.85, 1.25)
        sprite.on_impact()
        assert (sprite.scale_x, sprite.scale_y) == (1.30, 0.75)
        for _ in range(200):
            sprite.update(recovery_rate=0.5)
        assert sprite.scale_x == pytest.approx(1.0, abs=1e-6)
        assert sprite.scale_y == pytest.approx(1.0, abs=1e-6)


class TestVisualFxParticles:
    def test_particle_update_and_alpha(self):
        p = visual_fx_system.Particle(
            x=0, y=0, vel_x=1.5, vel_y=-0.5, color=(1, 2, 3, 4), size=1.0,
            lifetime=2, max_lifetime=4,
        )
        assert p.update() is True
        assert (p.x, p.y) == (1.5, -0.5)
        assert p.lifetime == 1
        assert p.alpha == pytest.approx(0.25)
        assert p.update() is False
        assert p.alpha == 0.0

    def test_footprint_decal_update_and_alpha(self):
        d = visual_fx_system.FootprintDecal(x=3, y=4, angle=0.5, lifetime=2)
        assert d.alpha == pytest.approx(1.0)
        assert d.update() is True
        assert d.update() is False

    def test_spawn_ambient_dust_gated_by_random(self):
        mgr = visual_fx_system.EnvironmentFXManager()
        with patch.object(visual_fx_system.random, "random", return_value=0.0):
            mgr.spawn_ambient_dust(100, 100)
        assert len(mgr.particles) == 1
        with patch.object(visual_fx_system.random, "random", return_value=0.99):
            mgr.spawn_ambient_dust(100, 100)
        assert len(mgr.particles) == 1

    def test_on_character_step_soft_terrains(self):
        mgr = visual_fx_system.EnvironmentFXManager()
        for terrain in ("snow", "mud", "sand", "dirt", "SAND"):
            mgr.on_character_step(1.0, 2.0, terrain, angle=0.25)
        assert len(mgr.footprints) == 5
        assert mgr.footprints[-1].angle == 0.25
        mgr.on_character_step(0, 0, "stone")
        assert len(mgr.footprints) == 5

    def test_environment_update_filters_expired(self):
        mgr = visual_fx_system.EnvironmentFXManager()
        mgr.particles.append(
            visual_fx_system.Particle(
                x=0, y=0, vel_x=0, vel_y=0, color=(0, 0, 0, 0), size=1.0,
                lifetime=1, max_lifetime=2,
            )
        )
        mgr.footprints.append(visual_fx_system.FootprintDecal(x=1, y=1, lifetime=1))
        with patch.object(visual_fx_system.random, "random", return_value=1.0):
            mgr.update()
        assert mgr.particles == []
        assert mgr.footprints == []


class TestTimeOfDayFX:
    def test_set_phase_instant(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.set_phase(TimePhase.NIGHT, instant=True)
        assert mgr.current_phase == TimePhase.NIGHT
        assert mgr.transition_from is None
        assert mgr.transition_to is None
        mod = mgr.get_palette_modifier()
        assert mod["multiply"] == (0.5, 0.6, 0.8)
        assert mod["fog_density"] == pytest.approx(0.2)
        assert mod["description"] == "星空の夜"

    def test_set_phase_same_phase_is_instant(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.set_phase(TimePhase.DAY)
        assert mgr.transition_to is None

    def test_transition_lerp_and_completion(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.set_phase(TimePhase.DUSK)
        assert mgr.transition_from == TimePhase.DAY
        assert mgr.transition_to == TimePhase.DUSK
        mgr.update_transition(0.5)
        assert mgr.transition_progress == pytest.approx(0.5)
        mod = mgr.get_palette_modifier()
        day = mgr.PHASE_PALETTE_MODIFIERS[TimePhase.DAY]
        dusk = mgr.PHASE_PALETTE_MODIFIERS[TimePhase.DUSK]
        expected_r = day["multiply"][0] + (dusk["multiply"][0] - day["multiply"][0]) * 0.5
        assert mod["multiply"][0] == pytest.approx(expected_r)
        assert mod["fog_density"] == pytest.approx(0.05)
        assert mod["description"] == "夕焼けに染まる空"
        mgr.update_transition(0.5)
        assert mgr.current_phase == TimePhase.DUSK
        assert mgr.transition_to is None
        assert mgr.transition_progress == 0.0

    def test_update_transition_without_pending_transition_is_noop(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.update_transition(0.9)
        assert mgr.transition_progress == 0.0
        assert mgr.current_phase == TimePhase.DAY

    def test_apply_to_palette_multiplies_and_clamps(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.set_phase(TimePhase.NIGHT, instant=True)
        out = mgr.apply_to_palette({"white": (255, 255, 255), "black": (0, 0, 0)})
        assert out["white"] == (int(255 * 0.5 - 30), int(255 * 0.6 - 20), int(255 * 0.8))
        assert out["black"] == (0, 0, 0)  # clamped at zero

    def test_unknown_phase_falls_back_to_identity(self):
        mgr = visual_fx_system.TimeOfDayFXManager()
        mgr.current_phase = "BOGUS"
        mod = mgr.get_palette_modifier()
        assert mod["multiply"] == (1.0, 1.0, 1.0)
        assert mod["add"] == (0, 0, 0)
        assert mod["fog_density"] == 0.0


# ===========================================================================
# ui_fx_systems.py (shared primitives used by fx_manager)
# ===========================================================================


class TestUiFxPrimitives:
    def test_floating_text_rises_and_expires(self):
        ft = ui_fx_systems.FloatingText("-5", 1, 2, (255, 0, 0), life=2)
        assert ft.update() is True
        assert ft.y == pytest.approx(2 - 0.3)
        assert ft.update() is False

    def test_particle_moves_and_expires(self):
        p = ui_fx_systems.Particle("*", 0, 0, (1, 2, 3), life=1, vx=0.5, vy=-0.5)
        assert p.update() is False
        assert (p.x, p.y) == (0.5, -0.5)

    def test_particle_shockwave_flag_and_tile_id(self):
        p = ui_fx_systems.Particle("*", 0, 0, (1, 2, 3), is_shockwave=True, tile_id="TR_EFFECT_12")
        assert p.is_shockwave is True
        assert p.tile_id == "TR_EFFECT_12"

    def test_screen_shake_lifecycle(self):
        shake = ui_fx_systems.ScreenShake()
        assert shake.is_active is False
        shake.trigger(intensity=2.0, duration=2, direction=(1, -1))
        assert shake.is_active is True
        assert shake.intensity == 2.0
        assert shake.direction == (1, -1)
        assert shake.update() is True
        assert shake.update() is False
        assert shake.is_active is False
        assert shake.intensity == 0.0

    def test_gauge_bar_rendering(self):
        gauge = ui_fx_systems.GaugeBar
        assert gauge.render(10, 20, length=4) == "[■■□□] 10/20"
        assert gauge.render(0, 20, length=4) == "[□□□□] 0/20"
        assert gauge.render(25, 20, length=4) == "[■■■■] 25/20"
        assert gauge.render(5, 0) == "[□□□□□□□□□□] 5/0"
        assert gauge.render(5, 10, length=2, force_numeric=True) == "[■□] 5/10 (50%)"

    def test_look_cursor_clamps_to_map(self):
        cursor = ui_fx_systems.LookCursor()
        cursor.move(-10, -10)
        assert (cursor.x, cursor.y) == (0, 0)
        cursor.move(10**6, 10**6)
        assert cursor.x == ui_fx_systems.MAP_WIDTH - 1
        assert cursor.y == ui_fx_systems.VIEW_HEIGHT - 1

    def test_context_menu(self):
        menu = ui_fx_systems.ContextMenu()
        assert menu.is_empty() is True
        action = ui_fx_systems.ContextAction("拾う", "g", "do_pickup", payload={"item": 1})
        menu.set_actions([action])
        assert menu.is_empty() is False
        assert menu.selected_index == 0
        assert menu.actions[0].label == "拾う"
        assert menu.actions[0].handler_name == "do_pickup"
        assert menu.actions[0].payload == {"item": 1}

    def test_notification_manager_lifecycle(self):
        nm = ui_fx_systems.NotificationManager()
        assert nm.get_latest() is None
        nm.notify("Trophy", "最初の撃破", category="trophy", duration=2)
        nm.notify("Hint", "Spaceで待機", duration=1)
        latest = nm.get_latest()
        assert latest.title == "Trophy"
        assert latest.category == "trophy"
        nm.update()
        assert len(nm.active_notifications) == 1
        nm.update()
        assert nm.active_notifications == []
        assert nm.get_latest() is None

    def test_tutorial_manager_load_trigger_and_missing_file(self, tmp_path):
        guide_file = tmp_path / "guides.yaml"
        guide_file.write_text(
            "tutorial_guides:\n"
            "  first_step:\n"
            "    id: first_step\n"
            "    trigger_condition: game_start\n"
            "    title: ようこそ\n"
            "    message: 階段を探そう\n"
            "    action_required: move\n",
            encoding="utf-8",
        )
        tm = ui_fx_systems.TutorialManager(str(guide_file))
        guide = tm.check_triggers("game_start", set())
        assert guide is not None
        assert guide.title == "ようこそ"
        assert guide.to_dict() == {
            "id": "first_step",
            "trigger_condition": "game_start",
            "title": "ようこそ",
            "message": "階段を探そう",
            "action_required": "move",
        }
        assert tm.check_triggers("game_start", {"first_step"}) is None
        assert tm.check_triggers("unknown_condition", set()) is None
        tm.update()  # no-op must not raise

        missing = ui_fx_systems.TutorialManager(str(tmp_path / "nope.yaml"))
        assert missing.guides == {}

    def test_skill_tree_ui_formatting(self):
        st = ui_fx_systems.SkillTreeUI
        assert st.format_tree_summary("war", "戦士", 5, 2) == "【戦士】 習得済: 2/5 ティア"
        learned = st.format_tier_line("剣術", 3, True, True, frame_count=0)
        assert "⚡" in learned and "習得済" in learned and "剣術" in learned
        assert "✨" in st.format_tier_line("剣術", 3, True, True, frame_count=15)
        assert st.format_tier_line("槍術", 2, False, True).startswith("〇習得可")
        assert st.format_tier_line("槍術", 2, False, False).startswith("×未開放")

    def test_job_and_pet_ui_formatting(self):
        assert ui_fx_systems.JobUI.format_job_summary("戦士", 3, 100) == \
            "現在の職業: 【戦士】 (Job Lv.3  EXP: 100)"
        assert ui_fx_systems.PetUI.format_bond_summary("シエル", "友情的絆", 40, 100) == \
            "【シエル】 契約: 友情的絆  絆度: 40/100"

    def test_weather_particle_spawners(self):
        fx = MagicMock()
        with patch.object(ui_fx_systems, "is_enabled", return_value=False):
            ui_fx_systems.WeatherAtmosphereLayer.spawn_weather_particles(fx, "rain", 0, 0, 10, 10, 0)
        fx.spawn_tile_effect.assert_not_called()
        with patch.object(ui_fx_systems, "is_enabled", return_value=True):
            ui_fx_systems.WeatherAtmosphereLayer.spawn_weather_particles(fx, "rain", 0, 0, 10, 10, 0)
            assert fx.spawn_tile_effect.call_count == 3
            assert fx.spawn_tile_effect.call_args.args[2] == "fire"
            fx.reset_mock()
            ui_fx_systems.WeatherAtmosphereLayer.spawn_weather_particles(fx, "snow", 0, 0, 10, 10, 0)
            assert fx.spawn_tile_effect.call_count == 2
            assert fx.spawn_tile_effect.call_args.args[2] == "ice"
            fx.reset_mock()
            ui_fx_systems.WeatherAtmosphereLayer.spawn_weather_particles(fx, "ash", 0, 0, 10, 10, 0)
            assert fx.spawn_tile_effect.call_count == 2
            assert fx.spawn_tile_effect.call_args.args[2] == "smoke"

    def test_cinematic_log_rendering(self):
        console = MagicMock()
        log = MagicMock()
        log.get_recent.return_value = [
            SimpleNamespace(level="INFO", text="歩いた", color=(200, 200, 200)),
            SimpleNamespace(level="WARNING", text="敵が現れた！", color=(255, 100, 100)),
        ]
        ui_fx_systems.CinematicLogVisualizer.render_cinematic_logs(
            console, log, start_x=5, start_y=10, count=2, frame_count=0
        )
        assert console.print.call_count == 2
        first, second = console.print.call_args_list
        assert first.kwargs["string"] == " 歩いた"
        assert first.kwargs["fg"] == (200, 200, 200)
        # Latest warning shakes left (frame 0) and pulses brighter.
        assert second.kwargs["string"] == "[!] 敵が現れた！"
        assert second.kwargs["x"] == 5 - 1
        assert second.kwargs["fg"] == (255, 70, 70)

    def test_cinematic_log_success_flash_and_missing_api(self):
        console = MagicMock()
        log = MagicMock()
        log.get_recent.return_value = [
            SimpleNamespace(level="SUCCESS", text="宝を発見", color=(120, 220, 120)),
        ]
        ui_fx_systems.CinematicLogVisualizer.render_cinematic_logs(console, log, 0, 0, frame_count=0)
        (only,) = console.print.call_args_list
        assert only.kwargs["string"] == "★ 宝を発見"
        assert only.kwargs["fg"] == (220, 200, 50)
        # Message log without get_recent support renders nothing.
        bare_console = MagicMock()
        ui_fx_systems.CinematicLogVisualizer.render_cinematic_logs(bare_console, object(), 0, 0)
        bare_console.print.assert_not_called()

    def test_dynamic_lighting_distance_and_blend(self):
        dl = ui_fx_systems.DynamicLighting
        assert dl.calculate_distance_intensity(0, 0, 0, 0) == pytest.approx(1.0)
        assert dl.calculate_distance_intensity(100, 0, 0, 0) == 0.0
        assert dl.blend_color((100, 200, 255), 0.5) == (50, 100, 127)
        color, intensity = dl.calculate_tile_lighting(
            0, 0, (255, 255, 255),
            [ui_fx_systems.LightSource(x=0, y=0, radius=7.0, color=(255, 240, 200), intensity=1.0)],
        )
        assert color == (255, 255, 255)
        assert intensity == pytest.approx(1.0)

    def test_tile_lighting_properties(self):
        props = ui_fx_systems.DynamicLighting.get_tile_lighting_properties
        torch = props("TR_DECOR_01")
        assert torch["emissive"] is True
        assert torch["emissive_radius"] == 5.0
        assert torch["material"] == "fire"
        assert props("TR_FLOOR_01")["material"] == "stone"
        assert props("TR_MONSTER_01")["material"] == "flesh"
        assert props("TR_ITEM_04_01")["reflective"] is True
        plain = props("PLAIN")
        assert plain["emissive"] is False
        assert plain["material"] == "default"

    def test_get_light_sources_for_engine(self):
        context = MagicMock()
        context.player.x = 5
        context.player.y = 6
        context.pet.hp = 8
        context.pet.x = 7
        context.pet.y = 8
        context.altar_pos = (10, 10)
        context.game_map.stairs_down_pos = (20, 20)
        alive_node = SimpleNamespace(x=1, y=2, depleted=False)
        dead_node = SimpleNamespace(x=3, y=4, depleted=True)
        context.resource_nodes = [alive_node, dead_node]
        context.particles = [SimpleNamespace(x=1.5, y=2.5, color=(10, 20, 30))]
        sources = ui_fx_systems.DynamicLighting.get_light_sources_for_engine(context)
        assert [s.source_type for s in sources] == [
            "player", "pet", "altar", "portal", "resource", "magic",
        ]
        # No player -> no light sources at all.
        assert ui_fx_systems.DynamicLighting.get_light_sources_for_engine(MagicMock(player=None)) == []


# ===========================================================================
# ui_event_panel.py
# ===========================================================================


class TestUiEventPanel:
    def test_current_event_info_inactive(self):
        with patch.object(ui_event_panel, "EVENT_SCHEDULER") as sched:
            sched.get_current_seasonal_event.return_value = None
            assert ui_event_panel.get_current_event_info(100) == {"active": False}

    def test_current_event_info_with_end_turn(self):
        event = SimpleNamespace(
            id="harvest", name="収穫祭", description="畑の実りが溢れる",
            end_turn=150, effects=["buff"], quarter=3,
        )
        with patch.object(ui_event_panel, "EVENT_SCHEDULER") as sched:
            sched.get_current_seasonal_event.return_value = event
            info = ui_event_panel.get_current_event_info(100)
        assert info == {
            "active": True,
            "id": "harvest",
            "name": "収穫祭",
            "description": "畑の実りが溢れる",
            "remaining_turns": 50,
            "quarter": 3,
            "effects": ["buff"],
        }

    def test_current_event_info_duration_placeholder(self):
        event = SimpleNamespace(id="e", name="n", description="d", duration=7, effects=[])
        with patch.object(ui_event_panel, "EVENT_SCHEDULER") as sched:
            sched.get_current_seasonal_event.return_value = event
            info = ui_event_panel.get_current_event_info(100)
        assert info["remaining_turns"] == 7

    def test_get_event_ranking_slices_top_n(self):
        with patch.object(ui_event_panel, "RANKING_MANAGER") as rm:
            rm.get_ranking.return_value = [("p1", 10), ("p2", 8), ("p3", 3)]
            assert ui_event_panel.get_event_ranking("e", top_n=2) == [("p1", 10), ("p2", 8)]
            rm.get_ranking.assert_called_once_with("e")

    def test_get_player_event_score(self):
        with patch.object(ui_event_panel, "RANKING_MANAGER") as rm:
            rm.get_player_score.return_value = 42
            assert ui_event_panel.get_player_event_score("e", "p1") == 42
            rm.get_player_score.assert_called_once_with("e", "p1")

    def test_get_player_event_titles_delegates(self):
        player, event = MagicMock(), object()
        with patch.object(ui_event_panel, "TITLE_MANAGER") as tm:
            tm.get_player_titles.return_value = ["trophy"]
            assert ui_event_panel.get_player_event_titles(player, event) == ["trophy"]
            tm.get_player_titles.assert_called_once_with(player)

    def test_get_active_npc_names(self):
        clock = MagicMock()
        clock.get_active_npc_details.return_value = [
            {"name": "行商人", "location": "town"},
            {"name": "吟遊詩人", "location": "forest"},
        ]
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            assert ui_event_panel.get_active_npc_names() == ["行商人(town)", "吟遊詩人(forest)"]
            clock.get_active_npc_details.assert_called_once_with(None)

    def test_get_merchant_location(self):
        clock = MagicMock()
        clock.get_merchant_location.return_value = "market"
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            assert ui_event_panel.get_merchant_location("merchant_1") == "market"

    def test_get_current_phase_info(self):
        clock = MagicMock()
        clock.current_phase = TimePhase.DUSK
        clock.hour = 18
        clock.minute = 30
        clock.to_string.return_value = "18:30"
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            info = ui_event_panel.get_current_phase_info()
        assert info["phase"] == "DUSK"
        assert info["display_name"] == TimePhase.DUSK.display_name
        assert info["short_name"] == TimePhase.DUSK.short_name
        assert info["hour"] == 18
        assert info["minute"] == 30
        assert info["time_string"] == "18:30"
        assert info["hours_until_next"] == TimePhase.DUSK.hours_until_next(18)

    def test_get_facility_efficiency(self):
        clock = MagicMock()
        clock.get_facility_efficiency.return_value = 1.5
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            assert ui_event_panel.get_facility_efficiency("shop") == 1.5

    def test_get_facility_status_unknown_facility(self):
        clock = MagicMock()
        clock.get_facility_efficiency.return_value = 0.0
        clock.is_facility_active.return_value = False
        clock.facility_registry.get_facility.return_value = None
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            status = ui_event_panel.get_facility_status("nope")
        assert status == {"active": False, "efficiency": 0.0, "name": "nope"}

    def test_get_facility_status_full(self):
        facility = SimpleNamespace(
            name="武器屋", facility_type=SimpleNamespace(value="shop"), is_24h=False,
        )
        clock = MagicMock()
        clock.hour = 10
        clock.get_facility_efficiency.return_value = 0.8
        clock.is_facility_active.return_value = True
        clock.facility_registry.get_facility.return_value = facility
        clock.facility_registry.get_efficiency.return_value = 1.0
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            status = ui_event_panel.get_facility_status("shop_1")
        assert status["name"] == "武器屋"
        assert status["type"] == "shop"
        assert status["active"] is True
        assert status["efficiency"] == 0.8
        assert status["efficiency_percent"] == 80
        assert status["next_efficiency_percent"] == 100
        assert status["is_24h"] is False

    def test_get_all_facility_statuses(self):
        clock = MagicMock()
        clock.facility_registry.get_all_facilities.return_value = [
            SimpleNamespace(facility_id="a"),
            SimpleNamespace(facility_id="b"),
        ]
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock), \
             patch.object(ui_event_panel, "get_facility_status", side_effect=lambda fid: {"id": fid}):
            assert ui_event_panel.get_all_facility_statuses() == [{"id": "a"}, {"id": "b"}]

    def test_get_available_actions(self):
        from player_actions import ActionType

        clock = MagicMock()
        clock.can_perform_action.return_value = (True, "")
        cost = SimpleNamespace(base_hours=2.0, stamina_cost=5, mp_cost=0)
        clock.action_manager.get_cost.return_value = cost
        clock.get_facility_efficiency.return_value = 2.0
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            actions = ui_event_panel.get_available_actions(MagicMock())
        assert len(actions) == len(list(ActionType))
        by_type = {a["action_type"]: a for a in actions}
        assert by_type["explore"]["display_name"] == "探索"
        assert by_type["explore"]["can_perform"] is True
        assert by_type["explore"]["message"] == "実行可能"
        assert by_type["explore"]["actual_hours"] == 2.0
        assert by_type["explore"]["stamina_cost"] == 5
        # CRAFT hours are divided by the workshop efficiency (2.0 here).
        assert by_type["craft"]["actual_hours"] == 1.0

    def test_get_available_actions_without_cost_definitions(self):
        clock = MagicMock()
        clock.can_perform_action.return_value = (False, "疲労中")
        clock.action_manager.get_cost.return_value = None
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            assert ui_event_panel.get_available_actions(MagicMock()) == []

    def test_get_action_cost_preview_unknown_action(self):
        with patch.object(ui_event_panel, "get_world_clock", return_value=MagicMock()):
            assert ui_event_panel.get_action_cost_preview("meditate", MagicMock()) == \
                {"error": "不明な行動"}

    def test_get_action_cost_preview_missing_cost(self):
        clock = MagicMock()
        clock.action_manager.get_cost.return_value = None
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            assert ui_event_panel.get_action_cost_preview("sleep", MagicMock()) == \
                {"error": "コスト未定義"}

    def test_get_action_cost_preview_craft_with_efficiency(self):
        clock = MagicMock()
        clock.get_facility_efficiency.return_value = 4.0
        clock.can_perform_action.return_value = (True, "")
        clock.action_manager.get_cost.return_value = SimpleNamespace(
            base_hours=8.0, stamina_cost=10, mp_cost=5,
        )
        with patch.object(ui_event_panel, "get_world_clock", return_value=clock):
            preview = ui_event_panel.get_action_cost_preview("craft", MagicMock())
        assert preview["display_name"] == "クラフト"
        assert preview["base_hours"] == 8.0
        assert preview["actual_hours"] == 2.0
        assert preview["stamina_cost"] == 10
        assert preview["mp_cost"] == 5
        assert preview["can_perform"] is True

    def test_get_action_display_name_mapping(self):
        from player_actions import ActionType

        assert ui_event_panel._get_action_display_name(ActionType.EXPLORE) == "探索"
        assert ui_event_panel._get_action_display_name(SimpleNamespace(value="zzz")) == "zzz"


# ===========================================================================
# ui_skill_tree.py
# ===========================================================================


class FakeTier:
    def __init__(self, tier_id: str, name: str, cost: int, prerequisites=()):
        self.id = tier_id
        self.name = name
        self.cost = cost
        self.prerequisites = list(prerequisites)


class FakeTree:
    def __init__(self, name: str, tiers):
        self.name = name
        self.tiers = tiers


class FakeRegistry:
    def __init__(self, trees):
        self._trees = trees

    def all(self):
        return dict(self._trees)

    def get(self, tree_id):
        return self._trees.get(tree_id)


class FakeManager:
    def __init__(self, available=frozenset()):
        self._available = available
        self.calls = []

    def check_prerequisites(self, player, tier):
        self.calls.append(tier.id)
        return tier.id in self._available


def _make_player(earned=0, progress=None):
    return SimpleNamespace(total_skill_points_earned=earned, skill_tree_progress=progress or {})


class TestUiSkillTree:
    def test_build_nodes_marks_states(self):
        tree = FakeTree("戦士の道", [
            FakeTier("t1", "基礎体力", 5),
            FakeTier("t2", "剣術", 10, prerequisites=["t1"]),
        ])
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry({"war": tree}), FakeManager({"t2"}))
        nodes = renderer.build_nodes(_make_player(earned=5, progress={"war": ["t1"]}))
        n1, n2 = nodes["war"]
        assert n1.learned is True and n1.available is False and n1.progress_pct == 100
        assert n2.learned is False and n2.available is True and n2.progress_pct == 50
        assert n2.prerequisites == ["t1"]

    def test_build_nodes_multiple_trees(self):
        trees = {
            "war": FakeTree("戦", [FakeTier("w1", "A", 1)]),
            "mage": FakeTree("魔", [FakeTier("m1", "B", 1)]),
        }
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry(trees), FakeManager())
        nodes = renderer.build_nodes(_make_player())
        assert set(nodes) == {"war", "mage"}

    def test_progress_pct_clamps_and_zero_cost(self):
        tree = FakeTree("T", [FakeTier("a", "A", 10), FakeTier("b", "B", 0)])
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry({"t": tree}), FakeManager())
        nodes = renderer.build_nodes(_make_player(earned=9999))
        assert nodes["t"][0].progress_pct == 100
        assert nodes["t"][1].progress_pct == 0

    def test_check_prerequisites_not_called_for_learned_tiers(self):
        tree = FakeTree("T", [FakeTier("a", "A", 1)])
        manager = FakeManager()
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry({"t": tree}), manager)
        renderer.build_nodes(_make_player(progress={"t": ["a"]}))
        assert manager.calls == ["a"]  # learned tier short-circuits availability

    def test_render_text_available_node(self):
        tree = FakeTree("魔法の道", [FakeTier("m1", "火の玉", 4)])
        renderer = ui_skill_tree.SkillTreeRenderer(
            FakeRegistry({"mage": tree}), FakeManager({"m1"})
        )
        text = renderer.render_text(_make_player(earned=4), "mage")
        assert text.startswith("┌─ 魔法の道")
        assert text.rstrip().endswith("┘")
        assert "[○] 火の玉 (100%)" in text
        assert "習得可能" in text
        assert "前提: -" in text

    def test_render_text_learned_and_locked(self):
        tree = FakeTree("T", [FakeTier("a", "習得済み技", 4), FakeTier("b", "鍵技", 4, ["a"])])
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry({"t": tree}), FakeManager())
        text = renderer.render_text(_make_player(progress={"t": ["a"]}), "t")
        assert "[●] 習得済み技" in text
        assert "習得済み" in text
        assert "[✗] 鍵技" in text
        assert "🔒" in text
        assert "前提: a" in text

    def test_render_text_unknown_tree(self):
        renderer = ui_skill_tree.SkillTreeRenderer(FakeRegistry({}), FakeManager())
        assert renderer.render_text(_make_player(), "nope") == "(unknown tree: nope)"


# ===========================================================================
# ui_title_display.py
# ===========================================================================


class TestUiTitleDisplay:
    def test_get_player_titles(self):
        player = MagicMock()
        with patch.object(ui_title_display, "TITLE_MANAGER") as tm:
            tm.get_player_titles.return_value = ["slayer", "merchant"]
            titles = ui_title_display.get_player_titles(player)
        assert titles == [
            {"title": "slayer", "description": "", "event_id": ""},
            {"title": "merchant", "description": "", "event_id": ""},
        ]
        tm.get_player_titles.assert_called_once_with(player)

    def test_get_player_titles_empty(self):
        with patch.object(ui_title_display, "TITLE_MANAGER") as tm:
            tm.get_player_titles.return_value = []
            assert ui_title_display.get_player_titles(MagicMock()) == []

    def test_get_player_event_titles(self):
        player, event = MagicMock(), object()
        with patch.object(ui_title_display, "TITLE_MANAGER") as tm:
            tm.check_and_grant_titles.return_value = ["harvest_hero"]
            titles = ui_title_display.get_player_event_titles(player, event)
        assert titles == [{"title": "harvest_hero", "description": ""}]
        tm.check_and_grant_titles.assert_called_once_with(player, event, {})


# ===========================================================================
# ui_ranking_panel.py
# ===========================================================================


class TestUiRankingPanel:
    def test_get_all_event_rankings(self):
        with patch.object(ui_ranking_panel, "REGISTRY") as reg, \
             patch.object(ui_ranking_panel, "RANKING_MANAGER") as rm:
            reg.all_events.return_value = ["e1", "e2"]
            rm.get_ranking.side_effect = lambda eid: [("p", 1)] if eid == "e1" else []
            rankings = ui_ranking_panel.get_all_event_rankings()
        assert rankings == {"e1": [("p", 1)], "e2": []}

    def test_get_event_ranking_top_n(self):
        with patch.object(ui_ranking_panel, "RANKING_MANAGER") as rm:
            rm.get_ranking.return_value = [("p1", 9), ("p2", 5), ("p3", 1)]
            assert ui_ranking_panel.get_event_ranking("e", 2) == [("p1", 9), ("p2", 5)]
            rm.get_ranking.assert_called_once_with("e")

    def test_get_ranking_as_dict(self):
        with patch.object(ui_ranking_panel, "RANKING_MANAGER") as rm:
            rm.get_ranking.return_value = [("p1", 9), ("p2", 5)]
            assert ui_ranking_panel.get_ranking_as_dict("e", 5) == [
                {"player_id": "p1", "score": 9},
                {"player_id": "p2", "score": 5},
            ]

    def test_get_ranking_as_dict_empty(self):
        with patch.object(ui_ranking_panel, "RANKING_MANAGER") as rm:
            rm.get_ranking.return_value = []
            assert ui_ranking_panel.get_ranking_as_dict("e") == []


# ===========================================================================
# journal_ui.py
# ===========================================================================


def make_console():
    console = MagicMock()
    console.width = 80
    console.height = 50
    console.width_px = 640
    console.height_px = 400
    return console


def printed_strings(console) -> list[str]:
    out = []
    for call in console.print.call_args_list:
        args = call.args
        if len(args) >= 3 and isinstance(args[2], str):
            out.append(args[2])
    return out


def make_engine(**overrides):
    engine = MagicMock()
    engine.main_quest_system.active_quest_id = None
    engine.main_quest_system.quests = {}
    engine.procedural_quest_manager = None
    engine.archaeology_manager.registry.find_site_for_depth.return_value = None
    engine.dungeon_level = 1
    engine.arch_interpret_active = False
    comp = engine.player.archaeology
    comp.collected_fragments = []
    comp.decoded_fragments = []
    comp.reached_truths = []
    comp.leaned_endings = {}
    comp.decoder_hints_seen = []
    for key, value in overrides.items():
        setattr(engine, key, value)
    return engine


class TestJournalUINavigation:
    def test_initial_state(self):
        j = journal_ui.JournalUI()
        assert j.is_open is False
        assert j.visible is False
        assert j.selected_index == 0
        assert j.window_width == 60
        assert j.window_height == 20

    def test_toggle_resets_selection_on_open_only(self):
        j = journal_ui.JournalUI()
        j.selected_index = 7
        j.toggle()
        assert j.is_open is True
        assert j.visible is True
        assert j.selected_index == 0
        j.selected_index = 3
        j.toggle()
        assert j.is_open is False
        assert j.selected_index == 3  # reset happens only when opening

    def test_handle_input_when_closed_is_ignored(self):
        j = journal_ui.JournalUI()
        assert j.handle_input("DOWN") is False
        assert j.handle_input("ESC") is False

    def test_handle_input_navigation(self):
        j = journal_ui.JournalUI()
        j.toggle()
        assert j.handle_input("DOWN") is True
        assert j.selected_index == 1
        assert j.handle_input("UP") is True
        assert j.selected_index == 0
        assert j.handle_input("UP") is True  # clamped at zero
        assert j.selected_index == 0

    @pytest.mark.parametrize("key", ["ESC", "ENTER"])
    def test_handle_input_closes_journal(self, key):
        j = journal_ui.JournalUI()
        j.toggle()
        assert j.handle_input(key) is True
        assert j.is_open is False

    def test_handle_input_unhandled_key(self):
        j = journal_ui.JournalUI()
        j.toggle()
        assert j.handle_input("a") is False
        assert j.is_open is True


class TestJournalUIRender:
    def test_render_does_nothing_when_closed(self):
        j = journal_ui.JournalUI()
        console, engine = make_console(), make_engine()
        j.render(console, engine)
        console.print.assert_not_called()

    def test_render_empty_journal(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        j.render(console, engine)
        texts = printed_strings(console)
        assert any("冒険日誌" in t for t in texts)
        # Window frame drawn with box-drawing characters.
        assert any(t == "═" for t in texts)
        assert any(t == "║" for t in texts)
        assert any("現在アクティブなクエストはありません。" in t for t in texts)
        assert any("（まだいずれの真理にも到達していない）" in t for t in texts)
        assert any("(ESCで閉じる)" in t for t in texts)

    def test_render_with_active_quest_and_completed_records(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        objective = SimpleNamespace(
            is_completed=True, description="洞窟を探索する", current_count=3, required_count=3,
        )
        pending = SimpleNamespace(
            title="失われた遺物",
            description="遺物を探せ",
            objectives=[objective],
            status=QuestStatus.ACTIVE,
        )
        done = SimpleNamespace(title="最初の依頼", status=QuestStatus.COMPLETED)
        engine.main_quest_system.active_quest_id = "q1"
        engine.main_quest_system.quests = {"q1": pending, "q0": done}
        j.render(console, engine)
        texts = printed_strings(console)
        assert any("【現在の目標】" in t for t in texts)
        assert any(t == "失われた遺物" for t in texts)
        assert any(t == "遺物を探せ" for t in texts)
        assert any("達成条件:" in t for t in texts)
        assert any("✓ 洞窟を探索する (3/3)" in t for t in texts)
        assert any("【完了した記録】" in t for t in texts)
        assert any(t == "✓ 最初の依頼" for t in texts)
        for call in console.print.call_args_list:
            if len(call.args) >= 3 and call.args[2] == "✓ 最初の依頼":
                assert call.kwargs["fg"] == j.highlight_color

    def test_render_incomplete_objective_uses_open_mark(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        objective = SimpleNamespace(
            is_completed=False, description="敵を倒す", current_count=1, required_count=5,
        )
        engine.main_quest_system.active_quest_id = "q1"
        engine.main_quest_system.quests = {
            "q1": SimpleNamespace(title="討伐", description="倒せ", objectives=[objective],
                                  status=QuestStatus.ACTIVE),
        }
        j.render(console, engine)
        assert any("○ 敵を倒す (1/5)" in t for t in printed_strings(console))

    def test_render_procedural_quests_section(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        comp = engine.player.procedural_quest
        comp.accepted_quests = []
        comp.completed_quest_ids = ["gq_001", "gq_002"]
        engine.procedural_quest_manager = MagicMock()
        j.render(console, engine)
        texts = printed_strings(console)
        assert any("【生成クエスト（受諾中）】" in t for t in texts)
        assert any("（なし）" in t for t in texts)
        assert any("【完了した生成クエスト】" in t for t in texts)
        assert any("✓ gq_001" in t for t in texts)
        assert any("✓ gq_002" in t for t in texts)

    def test_render_archaeology_summary(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        amgr = engine.archaeology_manager
        amgr.registry.find_site_for_depth.return_value = "site_1"
        amgr.registry.get_site.return_value = {"name": "月影遺跡"}
        amgr.registry.get_truth.return_value = {"name": "星読みの真理"}
        amgr.registry.get_ending.return_value = {"name": "静かな終焉"}
        comp = engine.player.archaeology
        comp.collected_fragments = ["f1", "f2", "f3"]
        comp.decoded_fragments = ["f1", "f2"]
        comp.reached_truths = ["truth_1"]
        comp.leaned_endings = {"truth_1": "ending_1"}
        comp.decoder_hints_seen = ["壁画に赤い顔"]
        j.render(console, engine)
        texts = printed_strings(console)
        assert any("発掘可能: 月影遺跡" in t for t in texts)
        assert any(
            "出土断片: 3" in t and "解読済: 2" in t and "到達真理: 1" in t for t in texts
        )
        assert any("星読みの真理" in t and "静かな終焉" in t for t in texts)
        assert any("（[e]で解釈を記録）" in t for t in texts)
        assert any("【手がかり（未解読ヒント）】" in t for t in texts)
        assert any("💡 壁画に赤い顔" in t for t in texts)

    def test_render_archaeology_without_site(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        j.render(console, engine)
        assert any("（この深度に発掘可能な遺跡なし）" in t for t in printed_strings(console))

    def test_render_arch_interpret_prompt(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console, engine = make_console(), make_engine()
        engine.arch_interpret_active = True
        engine.arch_interpret_truth_idx = 0
        engine.arch_interpret_ending_idx = 1
        engine.arch_interpret_groups_cache = [
            {"name": "輪廻の真理", "endings": ["e_good", "e_bad"]},
        ]
        engine.archaeology_manager.registry.get_ending.side_effect = (
            lambda eid: {"name": f"終焉:{eid}"}
        )
        j.render(console, engine)
        texts = printed_strings(console)
        assert any("解釈プロンプト" in t for t in texts)
        assert any("輪廻の真理" in t for t in texts)
        assert any("終焉:e_bad" in t for t in texts)

    def test_render_without_archaeology_manager(self):
        j = journal_ui.JournalUI()
        j.toggle()
        console = make_console()
        engine = make_engine(archaeology_manager=None)
        j.render(console, engine)
        assert any("（考古学システム未登録）" in t for t in printed_strings(console))


