from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import wave
from array import array
from typing import Any

import yaml

logger = logging.getLogger(__name__)

try:
    import winsound

    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Import audio backend for OGG playback
try:
    from audio.backend import get_audio_backend, load_audio_manifest, preload_all_audio

    HAS_AUDIO_BACKEND = True
except ImportError:
    HAS_AUDIO_BACKEND = False

from feature_flags import is_enabled

# ---------------------------------------------------------------- 効果音フォールバック

AUDIO_ASSET_DIR = "assets/audio"

# 外部プレイヤー探索テーブル (実行ファイル名, 対応拡張子)。
# 優先度順に並べ、PATH に存在するものを選ぶ。
# aplay だけは ALSA 生鳴きなので WAV 専用 —— OGG を渡すと黙って死ぬため末尾に置く。
# pw-play を paplay より前に置く理由: PipeWire 環境では PulseAudio 互換サーバ側の
# 接続に失敗することが実測で確認されたが、ネイティブの pw-play は通る。
_PLAYER_CANDIDATES: tuple[tuple[str, frozenset[str]], ...] = (
    ("ffplay", frozenset({".ogg", ".wav", ".mp3", ".flac", ".m4a", ".opus"})),
    ("afplay", frozenset({".ogg", ".wav", ".mp3", ".flac", ".m4a", ".aiff"})),
    ("pw-play", frozenset({".ogg", ".wav", ".mp3", ".flac"})),
    ("paplay", frozenset({".ogg", ".wav", ".mp3", ".flac"})),
    ("aplay", frozenset({".wav"})),
)

# 診断ログは一度だけ。効果音のたびに同じエラーを吐かないための制御。
_missing_backend_reported = False
_player_errors_reported: set[str] = set()

# 起動に失敗したプレイヤー。以後の効果音では候補から外す。
_player_failures: set[str] = set()


def resolve_audio_player(suffix: str) -> str | None:
    """拡張子を再生できる外部プレイヤーの実体パスを返す。無ければ None。"""
    for name, supported in _PLAYER_CANDIDATES:
        if suffix and suffix not in supported:
            continue
        if name in _player_failures:
            continue
        found = shutil.which(name)
        if found:
            return found
    return None


def build_player_command(player: str, source: str, volume: float = 1.0) -> list[str]:
    """外部プレイヤーの実行コマンドを組み立てる（音量対応はプレイヤー次第）。"""
    level = max(0.0, min(1.0, volume))
    name = os.path.basename(player)
    if name == "pw-play":
        return [player, f"--volume={level}", source]
    if name == "paplay":
        return [player, f"--volume={int(level * 65536)}", source]
    if name == "ffplay":
        return [
            player,
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
            "-volume",
            str(int(level * 100)),
            source,
        ]
    if name == "afplay":
        return [player, "-v", f"{level:.2f}", source]
    if name == "aplay":
        return [player, "-q", source]
    return [player, source]


def resolve_audio_asset(filename: str) -> str | None:
    """設定で指定された効果音名を assets/audio 配下の実ファイルへ解決する。"""
    if not filename:
        return None
    stem = filename if "." in filename else f"{filename}.ogg"
    for candidate in (stem, f"{stem}.ogg", f"{stem}.wav"):
        path = os.path.join(AUDIO_ASSET_DIR, candidate)
        if os.path.isfile(path):
            return path
    return None


def report_missing_audio_backend() -> None:
    """再生手段が無いことを一度だけ大声で報告する（効果音ごとに黙って捨てるな）。"""
    global _missing_backend_reported
    if _missing_backend_reported:
        return
    _missing_backend_reported = True
    tried = " / ".join(
        f"{name}({'失敗' if name in _player_failures else '無し/未対応拡張子'})"
        for name, _ in _PLAYER_CANDIDATES
    )
    logger.error(
        "効果音を再生できるバックエンドが無い。試行=%s, winsound=%s。"
        " 対処: `pip install pygame` で OGG 再生を有効にするか、"
        " PipeWire(pw-play) / PulseAudio(paplay) / ALSA(aplay) / ffplay / afplay"
        " のいずれかをインストール・復旧する。",
        tried,
        HAS_WINSOUND,
    )


def _report_player_error(name: str, returncode: int, detail: str) -> None:
    """プレイヤー側の失敗をプレイヤーごとに一度だけ報告する。"""
    if name in _player_errors_reported:
        return
    _player_errors_reported.add(name)
    logger.error("効果音の再生に失敗した (player=%s, rc=%s): %s", name, returncode, detail)


def _spawn_player(
    command: list[str],
    cleanup: str | None = None,
    on_failure: Callable[[], None] | None = None,
) -> None:
    """外部プレイヤーを非同期で起動し、終了後に一時ファイルを片付ける。"""
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        _report_player_error(os.path.basename(command[0]), -1, str(exc))
        if on_failure:
            on_failure()
        return

    def _reap() -> None:
        _, stderr = process.communicate()
        if process.returncode:
            _report_player_error(
                os.path.basename(command[0]),
                process.returncode,
                stderr.decode("utf-8", "replace").strip(),
            )
            if on_failure:
                on_failure()
        if cleanup:
            try:
                os.unlink(cleanup)
            except OSError:
                pass

    threading.Thread(target=_reap, daemon=True).start()


def _play_path(path: str, volume: float, cleanup: str | None, retry: bool) -> bool:
    """path を再生できるプレイヤーへ渡す。失敗したら次の候補で一度だけ再試行する。"""
    player = resolve_audio_player(os.path.splitext(path)[1])
    if player is None:
        report_missing_audio_backend()
        return False

    def _retry() -> None:
        # PATH に存在してもMach デバイスを開けたり接続できなかったりする。
        # 失敗したプレイヤーは候補から外し、次の一手（初回のみ）を試す。
        _player_failures.add(os.path.basename(player))
        if retry:
            _play_path(path, volume, cleanup, retry=False)

    _spawn_player(
        build_player_command(player, path, volume),
        cleanup=cleanup,
        on_failure=_retry if retry else None,
    )
    return True


def play_audio_file(path: str | None, volume: float = 1.0) -> bool:
    """実ファイル（OGG/WAV）を外部プレイヤーへ渡して再生する。失敗なら False。"""
    if not path:
        return False
    return _play_path(path, volume, None, retry=True)


def render_tone_wav(frequency: int, duration_ms: int, sample_rate: int = 22050) -> bytes:
    """winsound.Beep の代わりに、矩形波 beep を WAV バイト列として合成する。

    winsound は Windows 専用なので、Linux/macOS では外部プレイヤーへ
    流せる形に自前変換する。依存は標準ライブラリのみ。
    """
    total = max(1, sample_rate * duration_ms // 1000)
    half_period = max(1, sample_rate // (2 * max(1, frequency)))
    attack = max(1, total // 8)
    samples = array("h", bytes(2 * total))
    for index in range(total):
        # 立ち上がり/立ち下がりを線形に伸ばしてクリックノイズを抑える
        level = 6000 if index % (2 * half_period) < half_period else -6000
        fade = min(index, total - 1 - index, attack)
        samples[index] = level * fade // attack

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


class BGMManager:
    """BGM管理システム（クロスフェード・テーマ切り替え） (Step 7.1, 7.3)"""

    def __init__(self, config_path: str = "data/audio_config.yaml"):
        self.config_path = config_path
        self.current_track: str | None = None
        self.current_theme: str | None = None
        self.volume: float = 0.8
        self.is_crisis: bool = False
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                logger.exception("ロード失敗")
            return {}

    def play_bgm(self, theme: str, fade_in: bool = True) -> str:
        """指定テーマのBGMを再生/クロスフェード切り替え (Step 7.1)"""
        bgm_conf = (self.config or {}).get("bgm", {}).get(theme, {})
        track_id = bgm_conf.get("track", f"bgm_{theme}")
        self.current_theme = theme
        self.current_track = track_id
        self.volume = bgm_conf.get("volume", 0.8)
        return f"Playing BGM [{track_id}] (Theme: {theme}, Volume: {self.volume})"

    def check_crisis_trigger(self, hp: int, max_hp: int) -> str | None:
        """HP低下時の緊張BGMトリガー (Step 7.3)"""
        if max_hp > 0 and (hp / max_hp) <= 0.3:
            if not self.is_crisis:
                self.is_crisis = True
                return self.play_bgm("crisis")
        else:
            if self.is_crisis:
                self.is_crisis = False
                return self.play_bgm(self.current_theme or "dungeon")
        return None


class AmbientLayer:
    """環境音（アンビエント）レイヤー管理 (Step 7.2)"""

    def __init__(self, config_path: str = "data/audio_config.yaml"):
        self.config_path = config_path
        self.current_ambient: str | None = None
        self.volume: float = 0.5
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                logger.exception("ロード失敗")
            return {}

    def update_ambient(self, location_type: str) -> str:
        """場所に応じた環境音の動的切り替え (Step 7.2)"""
        amb_conf = self.config.get("ambient", {}).get(location_type, {})
        sound_id = amb_conf.get("sound", f"amb_{location_type}")
        self.current_ambient = sound_id
        self.volume = amb_conf.get("volume", 0.5)
        return f"Active Ambient: [{sound_id}] (Location: {location_type})"


class SoundManager:
    """効果音・BGM・環境音総合管理クラス (非同期スレッド再生)"""

    _enabled = True
    bgm_manager = BGMManager()
    ambient_layer = AmbientLayer()

    @classmethod
    def set_enabled(cls, enabled: bool):
        cls._enabled = enabled

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled

    @classmethod
    def _play_tone(cls, frequency: int, duration_ms: int):
        if not cls._enabled:
            return
        if HAS_WINSOUND:
            try:
                winsound.Beep(frequency, duration_ms)
                return
            except Exception:
                logger.exception("ロード失敗")
        # winsound が無い環境では合成 WAV を外部プレイヤーへ流す
        cls._play_wav_bytes(render_tone_wav(frequency, duration_ms))

    @classmethod
    def _play_wav_bytes(cls, payload: bytes):
        """合成した WAV を一時ファイル経由で外部プレイヤーへ流す。"""
        player = resolve_audio_player(".wav")
        if player is None:
            report_missing_audio_backend()
            return
        handle, temp_path = tempfile.mkstemp(prefix="narou_tone_", suffix=".wav")
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
        except OSError:
            logger.exception("ロード失敗")
            return
        _spawn_player(build_player_command(player, temp_path), cleanup=temp_path)

    @classmethod
    def play_se(cls, se_type: str):
        """非同期で効果音を再生 (ゲームループをブロックしない)"""
        if not cls._enabled:
            return

        def _worker():
            if se_type == "hit":
                cls._play_tone(220, 40)
            elif se_type == "kill":
                cls._play_tone(180, 50)
                cls._play_tone(130, 80)
            elif se_type == "level_up":
                for f in [523, 659, 784, 1046]:  # ド・ミ・ソ・高いド
                    cls._play_tone(f, 60)
            elif se_type == "heal":
                cls._play_tone(600, 50)
                cls._play_tone(800, 70)
            elif se_type == "cast":
                cls._play_tone(450, 40)
                cls._play_tone(650, 60)
            elif se_type == "get_item":
                cls._play_tone(880, 35)
                cls._play_tone(1175, 45)
            elif se_type == "equip":
                cls._play_tone(400, 30)
                cls._play_tone(500, 40)
            elif se_type == "mine":
                cls._play_tone(150, 50)
            elif se_type == "fanfare":
                for f in [523, 659, 784, 1046, 1318]:
                    cls._play_tone(f, 80)
            elif se_type == "step":
                pass

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def play_bgm(cls, theme: str = "dungeon", fade_in: bool = True) -> str:
        return cls.bgm_manager.play_bgm(theme, fade_in=fade_in)

    @classmethod
    def update_ambient(cls, location_type: str) -> str:
        return cls.ambient_layer.update_ambient(location_type)

    # ===== NEW: OGG Audio Pack Integration =====

    _audio_initialized = False
    _se_cache: dict[str, str] = {}  # se_type -> suggested_id mapping
    _se_files: dict[str, str] = {}  # se_type -> ファイル名 mapping
    _terrain_footstep_map: dict[str, str] = {}
    _terrain_footstep_files: dict[str, str] = {}

    @classmethod
    def _init_audio_pack(cls):
        """Initialize audio pack - load manifest and preload sounds."""
        if cls._audio_initialized or not HAS_AUDIO_BACKEND:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            return

        # Load SE mappings from config（backend 不在でも raw ファイル再生で必要）
        cls._load_se_mappings()

        backend = get_audio_backend()
        if not backend.is_available:
            return

        # Preload all audio
        loaded = preload_all_audio("assets/audio/manifest.csv")
        if loaded > 0:
            cls._audio_initialized = True
            print(f"Audio pack initialized: {loaded} sounds loaded (backend: {backend.backend})")

    @classmethod
    def _load_se_mappings(cls):
        """Load SE type -> suggested_id mappings from audio config."""
        try:
            if os.path.exists("data/audio_config.yaml"):
                with open("data/audio_config.yaml", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                se_map = config.get("se", {})
                for se_type, filename in se_map.items():
                    # Convert filename to suggested_id (e.g., metalClick.ogg -> se_metal_click)
                    suggested_id = "se_" + filename.replace(".ogg", "").replace(".", "_").lower()
                    cls._se_cache[se_type] = suggested_id
                    cls._se_files[se_type] = filename

                # Load terrain footstep mapping
                footstep_keys = [k for k in se_map if k.startswith("footstep_")]
                for key in footstep_keys:
                    terrain = key.replace("footstep_", "")
                    cls._terrain_footstep_map[terrain] = cls._se_cache.get(key, "")
                    cls._terrain_footstep_files[terrain] = cls._se_files.get(key, "")
        except Exception:
            logger.exception("ロード失敗")

    @classmethod
    def _play_mapped_asset(cls, se_type: str, volume: float = 1.0) -> bool:
        """audio.backend が無い環境で、設定が指す OGG をそのまま再生する。"""
        return play_audio_file(resolve_audio_asset(cls._se_files.get(se_type, "")), volume)

    @classmethod
    def _play_footstep_asset(cls, terrain: str, volume: float = 1.0) -> bool:
        """地形別の足音アセットを外部プレイヤーで再生する。"""
        filename = cls._terrain_footstep_files.get(terrain, "")
        if not filename:
            return False
        return play_audio_file(resolve_audio_asset(filename), volume)

    @classmethod
    def play_se_ogg(cls, se_type: str, volume: float = 1.0):
        """Play SE using OGG file from audio pack."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            # Fall back to tone-based SE
            cls.play_se(se_type)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.play_se(se_type)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            if not cls._play_mapped_asset(se_type, volume):
                cls.play_se(se_type)
            return

        suggested_id = cls._se_cache.get(se_type)
        if not suggested_id:
            # Try direct mapping
            suggested_id = cls._se_cache.get(se_type.lower())
        if not suggested_id:
            cls.play_se(se_type)  # Fallback
            return

        def _worker():
            backend.play_sound(suggested_id, volume=volume)

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def play_footstep(cls, terrain: str = "stone", volume: float = 0.6):
        """Play terrain-specific footstep sound."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.play_se("step")
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.play_se("step")
            return

        backend = get_audio_backend()
        if not backend.is_available:
            if not cls._play_footstep_asset(terrain, volume):
                cls.play_se("step")
            return

        se_type = cls._terrain_footstep_map.get(terrain, "footstep_stone")
        suggested_id = cls._se_cache.get(se_type)
        if suggested_id:

            def _worker():
                backend.play_sound(suggested_id, volume=volume)

            threading.Thread(target=_worker, daemon=True).start()
        else:
            cls.play_se("step")

    @classmethod
    def play_ui_sound(cls, ui_type: str, volume: float = 0.7):
        """Play UI sound (click, hover, notify, select, cancel)."""
        se_map = {
            "click": "ui_click",
            "hover": "ui_hover",
            "notify": "ui_notify",
            "select": "ui_select",
            "cancel": "ui_cancel",
        }
        se_type = se_map.get(ui_type, "ui_click")
        cls.play_se_ogg(se_type, volume)

    @classmethod
    def play_bgm_ogg(cls, theme: str = "dungeon", fade_in: float = 1.0, loop: bool = True):
        """Play BGM using OGG file with crossfade."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        config = cls.bgm_manager.config
        bgm_conf = config.get("bgm", {}).get(theme, {})
        track_filename = bgm_conf.get("track", f"bgm_{theme}.ogg")
        volume = bgm_conf.get("volume", 0.7)

        # Try to find the OGG file
        bgm_path = f"assets/audio/{track_filename}"
        if not os.path.exists(bgm_path):
            # Try with .ogg extension
            if not track_filename.endswith(".ogg"):
                bgm_path = f"assets/audio/{track_filename}.ogg"

        if os.path.exists(bgm_path):
            backend.play_bgm(bgm_path, volume=volume, loop=loop, fade_in=fade_in)
        else:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)

    @classmethod
    def update_ambient_ogg(cls, location_type: str, depth: int = 0):
        """Update ambient loop with depth-based variation."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.ambient_layer.update_ambient(location_type)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.ambient_layer.update_ambient(location_type)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.ambient_layer.update_ambient(location_type)
            return

        # Determine ambient variant based on location and depth
        if location_type == "dungeon":
            if depth >= 10:
                ambient_key = "dungeon_deep"
            elif depth >= 5:
                ambient_key = "dungeon_shallow"
            else:
                ambient_key = "dungeon_shallow"
        elif location_type == "town":
            ambient_key = "town_day"
        elif location_type == "forest":
            ambient_key = "forest"
        elif location_type == "cave":
            ambient_key = "cave"
        else:
            ambient_key = "dungeon_shallow"

        config = cls.ambient_layer.config
        ambient_loops = config.get("ambient_loops", {})
        sound_filename = ambient_loops.get(ambient_key, "amb_water_drop")

        ambient_path = f"assets/audio/{sound_filename}"
        if not ambient_path.endswith(".ogg"):
            ambient_path += ".ogg"

        if os.path.exists(ambient_path):
            # For ambient, we play as a looping BGM at lower volume
            volume = 0.3
            backend.play_bgm(ambient_path, volume=volume, loop=True, fade_in=2.0)
            cls.ambient_layer.current_ambient = ambient_key
        else:
            cls.ambient_layer.update_ambient(location_type)

    @classmethod
    def stop_bgm(cls, fade_out: float = 1.0):
        """Stop BGM with fade out."""
        if HAS_AUDIO_BACKEND and is_enabled("ENABLE_AUDIO_PACK"):
            backend = get_audio_backend()
            if backend.is_available:
                backend.stop_bgm(fade_out)
        cls.bgm_manager.current_track = None
