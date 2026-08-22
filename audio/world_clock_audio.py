"""
World Clock Audio Manager
Steps 55-60: Audio integration for time system
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

try:
    from naRou.audio.dynamic_audio import play_ui_sound
    from naRou.time_system import TimePhase, get_world_clock
except ImportError:
    from time_system import TimePhase


class WorldClockAudioManager:
    """世界時計音響管理"""

    def __init__(self):
        self._enabled = True
        self._master_volume = 0.7
        self._ambience_volume = 0.5
        self._current_ambience: Optional[str] = None
        self._ambience_thread: Optional[threading.Thread] = None
        self._stop_ambience = False
        self._backend_play_func: Optional[Callable] = None
        self._sync_mode = False  # テスト用同期モード

        # 音響ファイルパス
        self.audio_files = {
            "clock_tower_bell": "audio/Audio/clock_tower_bell.ogg",
            "shift_change_announcement": "audio/Audio/shift_change_announcement.ogg",
            "night_ambience": "audio/Audio/night_ambience.ogg",
            "dawn_ambience": "audio/Audio/dawn_ambience.ogg",
        }

        # 環境音マッピング (フェーズ -> ファイルキー)
        self.phase_ambience = {
            TimePhase.DAWN: "dawn_ambience",
            TimePhase.DAY: None,  # 既存のtown_day使用
            TimePhase.DUSK: None,  # 既存のtown_night使用
            TimePhase.NIGHT: "night_ambience",
        }

    def set_backend(self, play_func: Callable[[str, float], None]) -> None:
        """再生バックエンド設定"""
        self._backend_play_func = play_func

    def set_sync_mode(self, sync: bool) -> None:
        """同期モード設定 (テスト用)"""
        self._sync_mode = sync

    def set_enabled(self, enabled: bool) -> None:
        """有効/無効切替"""
        self._enabled = enabled
        if not enabled:
            self.stop_ambience()

    def set_master_volume(self, volume: float) -> None:
        """マスターボリューム設定"""
        self._master_volume = max(0.0, min(1.0, volume))

    def set_ambience_volume(self, volume: float) -> None:
        """環境音ボリューム設定"""
        self._ambience_volume = max(0.0, min(1.0, volume))

    # --- 時報鐘 ---
    def play_hour_bell(self, hour: int) -> None:
        """時報鐘再生 (時間分の鐘)"""
        if not self._enabled or not self._backend_play_func:
            return

        # 0時は12回、それ以外は時間分
        bell_count = 12 if hour == 0 else hour

        def _play_bells():
            for i in range(bell_count):
                if not self._enabled:
                    break
                self._backend_play_func(
                    self.audio_files["clock_tower_bell"],
                    self._master_volume * 0.8
                )
                if i < bell_count - 1 and not self._sync_mode:
                    time.sleep(1.5)  # 鐘の間隔

        if self._sync_mode:
            _play_bells()
        else:
            threading.Thread(target=_play_bells, daemon=True).start()

    def play_phase_bell(self, phase: TimePhase) -> None:
        """フェーズ境界鐘再生"""
        if not self._enabled or not self._backend_play_func:
            return

        # フェーズ別の特別な鐘
        bell_patterns = {
            TimePhase.DAWN: 3,   # 夜明け: 3回 (高音)
            TimePhase.DAY: 1,    # 昼: 1回
            TimePhase.DUSK: 2,   # 夕暮れ: 2回
            TimePhase.NIGHT: 4,  # 夜: 4回 (低音)
        }

        count = bell_patterns.get(phase, 1)

        def _play_bells():
            for i in range(count):
                if not self._enabled:
                    break
                self._backend_play_func(
                    self.audio_files["clock_tower_bell"],
                    self._master_volume * 0.9
                )
                if i < count - 1 and not self._sync_mode:
                    time.sleep(1.0)

        if self._sync_mode:
            _play_bells()
        else:
            threading.Thread(target=_play_bells, daemon=True).start()

    # --- シフト変更アナウンス ---
    def play_shift_change_announcement(self, phase: TimePhase) -> None:
        """シフト変更アナウンス再生"""
        if not self._enabled or not self._backend_play_func:
            return

        self._backend_play_func(
            self.audio_files["shift_change_announcement"],
            self._master_volume * 0.9
        )

        # テキスト表示用コールバックがあれば呼ぶ
        phase_names = {
            TimePhase.DAWN: "夜明けシフトに切り替わります",
            TimePhase.DAY: "昼シフトに切り替わります",
            TimePhase.DUSK: "夕方シフトに切り替わります",
            TimePhase.NIGHT: "夜勤シフトに切り替わります",
        }
        message = phase_names.get(phase, "シフト変更")
        print(f"[アナウンス] {message}")  # 実際にはUIに通知

    # --- 環境音制御 ---
    def start_ambience(self, phase: TimePhase) -> None:
        """環境音ループ開始"""
        if not self._enabled:
            return

        ambience_key = self.phase_ambience.get(phase)
        if not ambience_key:
            return  # DAY/DUSKは既存システム使用

        if self._current_ambience == ambience_key:
            return  # 同じ環境音なら何もしない

        self.stop_ambience()

        self._current_ambience = ambience_key
        self._stop_ambience = False

        def _play_ambience_loop():
            while not self._stop_ambience and self._enabled:
                if self._backend_play_func:
                    self._backend_play_func(
                        self.audio_files[ambience_key],
                        self._master_volume * self._ambience_volume
                    )
                # ループ間隔 (環境音の長さに合わせて調整)
                time.sleep(30.0)  # 30秒ごとに再生

        self._ambience_thread = threading.Thread(target=_play_ambience_loop, daemon=True)
        self._ambience_thread.start()

    def stop_ambience(self) -> None:
        """環境音停止"""
        self._stop_ambience = True
        self._current_ambience = None
        if self._ambience_thread:
            self._ambience_thread.join(timeout=1.0)
            self._ambience_thread = None

    def crossfade_ambience(self, old_phase: TimePhase, new_phase: TimePhase, duration: float = 1.0) -> None:
        """環境音クロスフェード"""
        old_key = self.phase_ambience.get(old_phase)
        new_key = self.phase_ambience.get(new_phase)

        if old_key == new_key:
            return

        # 古い環境音をフェードアウトしながら新しいものをフェードイン
        # 簡易実装: 即座に切り替え
        self.stop_ambience()
        self.start_ambience(new_phase)

    # --- WorldClock連携 ---
    def on_phase_changed(self, old_phase: TimePhase, new_phase: TimePhase) -> None:
        """フェーズ変更時コールバック"""
        # シフト変更アナウンス
        self.play_shift_change_announcement(new_phase)

        # フェーズ境界鐘
        self.play_phase_bell(new_phase)

        # 環境音切替
        self.crossfade_ambience(old_phase, new_phase)

    def on_hour_changed(self, hour: int) -> None:
        """時変更時コールバック (時報)"""
        self.play_hour_bell(hour)

    def on_day_changed(self, day: int) -> None:
        """日変更時コールバック"""
        # 日付変更時の特別な音
        if self._enabled and self._backend_play_func:
            self._backend_play_func(
                self.audio_files["clock_tower_bell"],
                self._master_volume * 0.7
            )

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return {
            "enabled": self._enabled,
            "master_volume": self._master_volume,
            "ambience_volume": self._ambience_volume,
            "current_ambience": self._current_ambience,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldClockAudioManager":
        mgr = cls()
        mgr._enabled = data.get("enabled", True)
        mgr._master_volume = data.get("master_volume", 0.7)
        mgr._ambience_volume = data.get("ambience_volume", 0.5)
        mgr._current_ambience = data.get("current_ambience")
        return mgr


# --- グローバルインスタンス ---
_world_clock_audio_manager: WorldClockAudioManager | None = None


def get_world_clock_audio_manager() -> WorldClockAudioManager:
    """グローバル音響マネージャー取得"""
    global _world_clock_audio_manager
    if _world_clock_audio_manager is None:
        _world_clock_audio_manager = WorldClockAudioManager()
    return _world_clock_audio_manager
