"""winsound / pygame が無い環境でも効果音が鳴ることを保証するテスト。

このホスト（Linux・pygame 未インストール・winsound なし）では
`SoundManager._play_tone` が無言で return し、ゲームが無音になっていた。
音は実際に鳴らさず、「どのプレイヤーにどのファイルを渡すか」と
「バックエンドが無いときに一度だけ大声で報告するか」だけを検証する。
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import time
import wave

import pytest

import sound_manager
from sound_manager import SoundManager

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(REPO_ROOT, "assets", "audio")

# OGG をデコードできるのは aplay 以外（aplay は ALSA 生鳴き = WAV 専用）。
# ハードコードすると候補テーブルにプレイヤーを足した瞬間 silently に壊れるので、
# 実装側の表から導出する。
OGG_CAPABLE_PLAYERS = {
    name for name, supported in sound_manager._PLAYER_CANDIDATES if ".ogg" in supported
}


class _FakeProcess:
    """Popen 戻り値の最小スタブ。communicate() で即完了したことにする。"""

    def __init__(self, argv: list[str]) -> None:
        self.args = argv
        self.returncode = 0

    def communicate(self, input=None):  # noqa: A002, ANN001
        return (b"", b"")

    def wait(self, timeout=None):  # noqa: ANN001
        return 0

    def poll(self):
        return 0

    def terminate(self):
        return None

    def kill(self):
        return None


class _RecordingPopen:
    """Popen の記録器。実際の音は出さず、渡された argv と音源サイズだけ保存する。"""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int]] = []
        self.called = threading.Event()

    def __call__(self, argv, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        command = list(argv)
        source = command[-1]
        size = os.path.getsize(source) if os.path.isfile(source) else -1
        self.calls.append((command, size))
        self.called.set()
        return _FakeProcess(command)


@pytest.fixture(autouse=True)
def _clean_audio_state(monkeypatch):
    """SoundManager のクラス状態と診断ログの一回フラグを毎回リセットする。"""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(SoundManager, "_enabled", True)
    monkeypatch.setattr(SoundManager, "_audio_initialized", False)
    monkeypatch.setattr(SoundManager, "_se_cache", {})
    monkeypatch.setattr(SoundManager, "_se_files", {}, raising=False)
    monkeypatch.setattr(SoundManager, "_terrain_footstep_map", {})
    monkeypatch.setattr(sound_manager, "_missing_backend_reported", False, raising=False)
    yield


@pytest.fixture
def recorder(monkeypatch):
    """subprocess.Popen を差し替え、生音を一切出さずに argv を記録する。"""
    rec = _RecordingPopen()
    monkeypatch.setattr(sound_manager.subprocess, "Popen", rec)
    return rec


def _wait_for(count: int, rec: _RecordingPopen, timeout: float = 10.0) -> bool:
    """ワーカースレッドが count 件ディッチするまで待つ。"""
    deadline = time.monotonic() + timeout
    while len(rec.calls) < count and time.monotonic() < deadline:
        time.sleep(0.01)
    return len(rec.calls) >= count


# ---------------------------------------------------------------- プレイヤー解決


def test_resolve_audio_player_finds_executable_on_this_host():
    """このホストには実在する再生プレイヤーが解決されなければならない。"""
    for suffix in (".ogg", ".wav"):
        player = sound_manager.resolve_audio_player(suffix)
        assert player is not None, f"{suffix} を再生できるプレイヤーが見つからない"
        assert os.path.isabs(player)
        assert os.access(player, os.X_OK)


def test_resolve_audio_player_picks_ogg_capable_player():
    """aplay は WAV 専用なので、OGG には必然的に他のプレイヤーが選ばれる。"""
    player = sound_manager.resolve_audio_player(".ogg")
    assert os.path.basename(player) in OGG_CAPABLE_PLAYERS


def test_resolve_audio_player_returns_none_when_nothing_installed(monkeypatch):
    """候補テーブルを空にすれば『バックエンド無し』を再現できる。"""
    monkeypatch.setattr(sound_manager, "_PLAYER_CANDIDATES", ())
    assert sound_manager.resolve_audio_player(".wav") is None


def _player_takes_volume(player: str) -> bool:
    """音量が argv に反映されるプレイヤーか。音量dependent なプレイヤー名を書かずに済む。"""
    return sound_manager.build_player_command(
        player, "x.wav", volume=0.1
    ) != sound_manager.build_player_command(player, "x.wav", volume=0.9)


def test_build_player_command_carries_player_source_and_volume():
    """コマンドは必ず「プレイヤー … 音源」の順で、音源が末尾に来る。"""
    player = sound_manager.resolve_audio_player(".wav")
    command = sound_manager.build_player_command(player, "/tmp/beep.wav", volume=0.5)
    assert command[0] == player
    assert command[-1] == "/tmp/beep.wav"
    if _player_takes_volume(player):
        assert any("--volume" in arg or arg in ("-volume", "-v") for arg in command[1:-1])
    else:
        # 音量に未対応のプレイヤーでも音源は渡る
        assert command == [player, "-q", "/tmp/beep.wav"]


def test_build_player_command_clamps_volume():
    player = sound_manager.resolve_audio_player(".wav")
    for raw in (-5.0, 42.0):
        command = sound_manager.build_player_command(player, "x.wav", volume=raw)
        assert command[0] == player
        assert command[-1] == "x.wav"


# ---------------------------------------------------------------- tone 合成


def test_render_tone_wav_produces_playable_pcm():
    """生成された WAV は標準ライブラリで読めて、実際に信号が入っている。"""
    payload = sound_manager.render_tone_wav(220, 40)
    assert payload[:4] == b"RIFF"
    assert payload[8:12] == b"WAVE"

    with wave.open(io.BytesIO(payload), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        frames = handle.getnframes()
        rate = handle.getframerate()
        samples = handle.readframes(frames)

    assert frames > 0
    assert 30 <= frames * 1000 // rate <= 60  # 約 40ms
    peak = max(
        abs(int.from_bytes(samples[i : i + 2], "little", signed=True))
        for i in range(0, len(samples), 2)
    )
    assert peak > 0


# ---------------------------------------------------------------- 実際の振り分け


def test_play_se_hit_dispatches_tone_wav_to_player(recorder):
    """`play_se("hit")` が外部プレイヤーに WAV を渡す（長年の無音バグの回帰テスト）。"""
    assert sound_manager.HAS_WINSOUND is False  # Linux 上では必ずこの経路を通る

    SoundManager.play_se("hit")

    assert recorder.called.wait(10), "Popen が呼ばれなかった（無音のまま）"
    command, size = recorder.calls[0]
    assert command[0] == sound_manager.resolve_audio_player(".wav")
    assert command[-1].endswith(".wav")
    assert size > 0, "一時 WAV が空だった"


def test_play_se_level_up_emits_multiple_tones(recorder):
    """複数音色の SE は音ごとに 1 プロセスずつ渡る。"""
    SoundManager.play_se("level_up")

    assert recorder.called.wait(10)
    assert _wait_for(4, recorder)
    assert len(recorder.calls) == 4


def test_winsound_path_is_preserved_on_windows(monkeypatch, recorder):
    """HAS_WINSOUND の環境では従来どおり Beep を呼び、プレイヤーは起動しない。"""
    beeps: list[tuple[int, int]] = []
    beeped = threading.Event()

    class _FakeWinsound:
        @staticmethod
        def Beep(frequency, duration):  # noqa: N802
            beeps.append((frequency, duration))
            beeped.set()

    monkeypatch.setattr(sound_manager, "winsound", _FakeWinsound, raising=False)
    monkeypatch.setattr(sound_manager, "HAS_WINSOUND", True)

    SoundManager.play_se("hit")

    assert beeped.wait(10), "winsound.Beep が呼ばれなかった"
    assert beeps == [(220, 40)]
    assert recorder.calls == []


# ---------------------------------------------------------------- OGG アセット経路


def test_resolve_audio_asset_adds_extension_and_reports_missing():
    """`fanfare_victory` のように拡張子無しでも解決し、無いファイルは None。"""
    assert sound_manager.resolve_audio_asset("fanfare_victory") is None
    assert sound_manager.resolve_audio_asset("knifeSlice2") == os.path.join(
        "assets", "audio", "knifeSlice2.ogg"
    )
    assert sound_manager.resolve_audio_asset("") is None


def test_play_audio_file_passes_real_ogg_to_player(recorder):
    """既存の OGG アセットがそのままプレイヤーへ渡る。"""
    source = sound_manager.resolve_audio_asset("metalClick.ogg")
    assert source is not None
    assert sound_manager.play_audio_file(source)

    assert recorder.called.wait(10)
    command, size = recorder.calls[0]
    assert command[-1] == source
    assert size > 0


def test_play_se_ogg_uses_file_player_when_backend_missing(monkeypatch, recorder):
    """audio.backend が使えないとき、設定で紐づいた OGG を実ファイル再生する。"""

    class _UnavailableBackend:
        is_available = False
        backend = "none"

    monkeypatch.setattr(sound_manager, "get_audio_backend", _UnavailableBackend)
    monkeypatch.setattr(sound_manager, "is_enabled", lambda name: name == "ENABLE_AUDIO_PACK")

    SoundManager.play_se_ogg("kill", volume=0.8)

    assert recorder.called.wait(10), "アセット再生に回らなかった"
    command, _ = recorder.calls[0]
    assert os.path.basename(command[-1]) == "knifeSlice2.ogg"
    assert os.path.exists(command[-1])


def test_play_footstep_uses_file_player_when_backend_missing(monkeypatch, recorder):
    """足音も terrain 設定の OGG を直接再生する。"""

    class _UnavailableBackend:
        is_available = False
        backend = "none"

    monkeypatch.setattr(sound_manager, "get_audio_backend", _UnavailableBackend)
    monkeypatch.setattr(sound_manager, "is_enabled", lambda name: name == "ENABLE_AUDIO_PACK")

    SoundManager.play_footstep("wood")

    assert recorder.called.wait(10)
    command, size = recorder.calls[0]
    assert os.path.basename(command[-1]) == "footstep02.ogg"
    assert size > 0


# ---------------------------------------------------------------- バックエンド無し診断


def test_missing_backend_logs_one_loud_diagnostic(monkeypatch, caplog):
    """何も無ければ 1 度だけ、原因と対処を示す ERROR を出す（無言で捨てない）。"""
    monkeypatch.setattr(sound_manager, "_PLAYER_CANDIDATES", ())
    monkeypatch.setattr(sound_manager.subprocess, "Popen", subprocess.Popen)

    with caplog.at_level("ERROR", logger=sound_manager.__name__):
        for _ in range(5):
            SoundManager.play_se("hit")

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1, f"ERROR が {len(errors)} 件（1 回であるべき）"
    message = errors[0].getMessage()
    assert "効果音" in message
    assert "pip install" in message  # 何を入れればよいかの指示
    assert "pygame" in message


def test_play_audio_file_returns_false_without_backend(monkeypatch):
    monkeypatch.setattr(sound_manager, "_PLAYER_CANDIDATES", ())
    source = sound_manager.resolve_audio_asset("metalClick.ogg")
    assert sound_manager.play_audio_file(source) is False


def test_disabled_manager_never_spawns_player(recorder):
    SoundManager.set_enabled(False)
    try:
        SoundManager.play_se("hit")
    finally:
        SoundManager.set_enabled(True)
    threading.Event().wait(0.3)  # 起動しないことを見るため僅かに待つ
    assert recorder.calls == []


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
