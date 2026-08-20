"""Audio backend wrapper for OGG/WAV playback using simpleaudio."""
from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Dict, Optional
import weakref

# Try to import simpleaudio
try:
    import simpleaudio as sa
    HAS_SIMPLEAUDIO = True
except ImportError:
    HAS_SIMPLEAUDIO = False
    sa = None

# Try to import pygame as fallback
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    pygame = None

from feature_flags import is_enabled


class AudioBackend:
    """Unified audio backend supporting simpleaudio and pygame."""
    
    def __init__(self):
        self._sounds: Dict[str, any] = {}
        self._play_objects: list = []
        self._lock = threading.Lock()
        self._volume = 1.0
        self._bgm_player: Optional[any] = None
        self._bgm_volume = 0.7
        self._current_bgm_path: Optional[str] = None
        self._init_backend()
    
    def _init_backend(self):
        """Initialize the best available audio backend."""
        if HAS_PYGAME:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self._backend = "pygame"
                return
            except Exception:
                pass
        if HAS_SIMPLEAUDIO:
            self._backend = "simpleaudio"
            return
        self._backend = "none"
    
    @property
    def backend(self) -> str:
        return self._backend
    
    @property
    def is_available(self) -> bool:
        return self._backend != "none"
    
    def load_sound(self, sound_id: str, filepath: str) -> bool:
        """Load a sound file into memory."""
        if not self.is_available:
            return False
        
        path = Path(filepath)
        if not path.exists():
            return False
        
        try:
            with self._lock:
                if self._backend == "pygame":
                    sound = pygame.mixer.Sound(str(path))
                    self._sounds[sound_id] = sound
                elif self._backend == "simpleaudio":
                    wave_obj = sa.WaveObject.from_wave_file(str(path))
                    self._sounds[sound_id] = wave_obj
            return True
        except Exception as e:
            print(f"Failed to load sound {sound_id}: {e}")
            return False
    
    def play_sound(self, sound_id: str, volume: float = 1.0, blocking: bool = False) -> bool:
        """Play a loaded sound."""
        if not self.is_available or not is_enabled("ENABLE_AUDIO_PACK"):
            return False
        
        sound = self._sounds.get(sound_id)
        if not sound:
            return False
        
        try:
            with self._lock:
                if self._backend == "pygame":
                    sound.set_volume(volume * self._volume)
                    sound.play()
                elif self._backend == "simpleaudio":
                    play_obj = sound.play()
                    self._play_objects.append(play_obj)
                    # Clean up finished play objects
                    self._play_objects = [p for p in self._play_objects if p.is_playing()]
            return True
        except Exception as e:
            print(f"Failed to play sound {sound_id}: {e}")
            return False
    
    def play_bgm(self, filepath: str, volume: float = 0.7, loop: bool = True, fade_in: float = 1.0) -> bool:
        """Play background music with crossfade support."""
        if not self.is_available or not is_enabled("ENABLE_AUDIO_PACK"):
            return False
        
        path = Path(filepath)
        if not path.exists():
            return False
        
        try:
            with self._lock:
                # Stop current BGM with fade out
                if self._backend == "pygame" and pygame.mixer.music.get_busy():
                    pygame.mixer.music.fadeout(int(fade_in * 1000))
                
                if self._backend == "pygame":
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(volume * self._volume)
                    pygame.mixer.music.play(-1 if loop else 0, fade_ms=int(fade_in * 1000))
                    self._current_bgm_path = str(path)
                    self._bgm_volume = volume
                elif self._backend == "simpleaudio":
                    # simpleaudio doesn't support streaming BGM well
                    # For simpleaudio, we load and loop manually
                    wave_obj = sa.WaveObject.from_wave_file(str(path))
                    play_obj = wave_obj.play()
                    self._bgm_player = play_obj
                    self._current_bgm_path = str(path)
                    self._bgm_volume = volume
            return True
        except Exception as e:
            print(f"Failed to play BGM {filepath}: {e}")
            return False
    
    def stop_bgm(self, fade_out: float = 1.0) -> bool:
        """Stop background music with fade out."""
        if not self.is_available:
            return False
        
        try:
            with self._lock:
                if self._backend == "pygame":
                    pygame.mixer.music.fadeout(int(fade_out * 1000))
                    self._current_bgm_path = None
                elif self._backend == "simpleaudio":
                    if self._bgm_player and self._bgm_player.is_playing():
                        self._bgm_player.stop()
                    self._bgm_player = None
                    self._current_bgm_path = None
            return True
        except Exception:
            return False
    
    def set_master_volume(self, volume: float):
        """Set master volume (0.0 - 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if self._backend == "pygame" and self._current_bgm_path:
            pygame.mixer.music.set_volume(self._bgm_volume * self._volume)
    
    def set_bgm_volume(self, volume: float):
        """Set BGM volume (0.0 - 1.0)."""
        self._bgm_volume = max(0.0, min(1.0, volume))
        if self._backend == "pygame":
            pygame.mixer.music.set_volume(self._bgm_volume * self._volume)
    
    def cleanup(self):
        """Stop all sounds and cleanup."""
        with self._lock:
            if self._backend == "pygame":
                pygame.mixer.stop()
                pygame.mixer.music.stop()
            elif self._backend == "simpleaudio":
                for p in self._play_objects:
                    if p.is_playing():
                        p.stop()
                if self._bgm_player and self._bgm_player.is_playing():
                    self._bgm_player.stop()
                self._play_objects.clear()


# Global instance
_AUDIO_BACKEND = None

def get_audio_backend() -> AudioBackend:
    """Get global audio backend instance."""
    global _AUDIO_BACKEND
    if _AUDIO_BACKEND is None:
        _AUDIO_BACKEND = AudioBackend()
    return _AUDIO_BACKEND


def load_audio_manifest(manifest_path: str = "assets/audio/manifest.csv") -> Dict[str, Dict]:
    """Load audio manifest CSV and return dict of sound info."""
    import csv
    sounds = {}
    path = Path(manifest_path)
    if not path.exists():
        return sounds
    
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sounds[row['suggested_id']] = {
                'filename': row['filename'],
                'category': row['category'],
                'path': f"assets/audio/{row['filename']}"
            }
    return sounds


def preload_all_audio(manifest_path: str = "assets/audio/manifest.csv") -> int:
    """Preload all audio files from manifest."""
    backend = get_audio_backend()
    if not backend.is_available:
        return 0
    
    sounds = load_audio_manifest(manifest_path)
    loaded = 0
    for sound_id, info in sounds.items():
        if backend.load_sound(sound_id, info['path']):
            loaded += 1
    return loaded