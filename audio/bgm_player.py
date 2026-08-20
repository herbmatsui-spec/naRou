"""BGM Player with crossfade support for OGG files."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from feature_flags import is_enabled


class BGMPlayer:
    """Manages BGM playback with crossfade transitions."""

    def __init__(self):
        self._current_bgm: any | None = None
        self._current_path: str | None = None
        self._volume = 0.7
        self._fade_thread: threading.Thread | None = None
        self._stop_fade = False
        self._lock = threading.Lock()
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the best available audio backend."""
        try:
            import pygame

            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._backend = "pygame"
            return
        except Exception:
            pass

        try:
            self._backend = "simpleaudio"
            return
        except Exception:
            pass

        self._backend = "none"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_available(self) -> bool:
        return self._backend != "none"

    def play(
        self,
        filepath: str,
        volume: float = 0.7,
        loop: bool = True,
        fade_in: float = 1.0,
    ) -> bool:
        """Play BGM with crossfade from current track."""
        if not self.is_available or not is_enabled("ENABLE_AUDIO_PACK"):
            return False

        path = Path(filepath)
        if not path.exists():
            return False

        def _play_bgm():
            with self._lock:
                try:
                    if self._backend == "pygame":
                        import pygame

                        # Fade out current
                        if pygame.mixer.music.get_busy() and self._current_path:
                            pygame.mixer.music.fadeout(int(fade_in * 1000))
                            time.sleep(fade_in * 0.5)  # Brief wait for fade

                        pygame.mixer.music.load(str(path))
                        pygame.mixer.music.set_volume(volume)
                        pygame.mixer.music.play(
                            -1 if loop else 0, fade_ms=int(fade_in * 1000)
                        )
                        self._current_path = str(path)
                        self._volume = volume

                    elif self._backend == "simpleaudio":
                        import simpleaudio as sa

                        # Stop current
                        if self._current_bgm and self._current_bgm.is_playing():
                            self._current_bgm.stop()

                        wave_obj = sa.WaveObject.from_wave_file(str(path))
                        self._current_bgm = wave_obj.play()
                        self._current_path = str(path)
                        self._volume = volume

                except Exception as e:
                    print(f"BGM playback failed: {e}")

        threading.Thread(target=_play_bgm, daemon=True).start()
        return True

    def stop(self, fade_out: float = 1.0):
        """Stop BGM with fade out."""
        if not self.is_available:
            return

        def _stop_bgm():
            with self._lock:
                try:
                    if self._backend == "pygame":
                        import pygame

                        pygame.mixer.music.fadeout(int(fade_out * 1000))
                        self._current_path = None
                    elif self._backend == "simpleaudio":
                        if self._current_bgm and self._current_bgm.is_playing():
                            self._current_bgm.stop()
                        self._current_bgm = None
                        self._current_path = None
                except Exception:
                    pass

        threading.Thread(target=_stop_bgm, daemon=True).start()

    def set_volume(self, volume: float):
        """Set BGM volume (0.0 - 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if self._backend == "pygame" and self._current_path:
            import pygame

            pygame.mixer.music.set_volume(self._volume)


# Global instance
_BGM_PLAYER = None


def get_bgm_player() -> BGMPlayer:
    """Get global BGM player instance."""
    global _BGM_PLAYER
    if _BGM_PLAYER is None:
        _BGM_PLAYER = BGMPlayer()
    return _BGM_PLAYER
