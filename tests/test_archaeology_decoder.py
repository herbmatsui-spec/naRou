"""Unit tests for Archaeology & Decoder System (Phase 5, Steps 25-48)"""

import pytest

from naRou.ecs.components import ArchaeologyComponent
from naRou.ecs.entity import Entity
from naRou.systems.archaeology_decoder_system import ArchaeologyDecoderSystem, obfuscate_text


def test_obfuscate_text_full_and_zero():
    text = "我が剣折れ、盾砕くとも、星の導きが汝の歩みを照らし続けんことを。"
    
    # 1.0 (完全解読) では原文と一致すること
    decoded = obfuscate_text(text, decode_ratio=1.0)
    assert decoded == text

    # 0.0 (未解読) では句読点以外がグリフ化されていること
    masked = obfuscate_text(text, decode_ratio=0.0)
    assert masked != text
    assert "、" in masked and "。" in masked
    assert "我が剣" not in masked


def test_obfuscate_text_partial_multibyte_safe():
    text = "小さな命が哭いている。母を呼び、光を恐れ、ただ巣の温もりを求めて震えていた。"
    
    # 部分解読 (50%)
    partial = obfuscate_text(text, decode_ratio=0.5)
    assert len(partial) == len(text)  # 文字数が一致しマルチバイトでも崩れないこと
    assert partial != text
    assert "。" in partial


def test_archaeology_decoder_system_flow():
    system = ArchaeologyDecoderSystem()
    assert len(system.memory_fragments) >= 5
    assert len(system.decoder_keys) >= 3

    player = Entity(name="Explorer")
    player.archaeology = ArchaeologyComponent()

    # 1. フラグメント発見
    success, msg = system.collect_fragment(player, "goblin_child_screams")
    assert success is True
    assert "goblin_child_screams" in player.archaeology.collected_fragments
    assert player.archaeology.decipherment_gauge == 20

    # 2. 初期状態 (鍵なし) では部分解読
    state = system.get_fragment_state(player, "goblin_child_screams")
    assert state is not None
    assert state["is_decoded"] is False
    assert state["has_key"] is False
    assert state["displayed_text"] != state["translated_text"]

    # 3. 鍵を獲得
    success, msg = system.unlock_decoder_key(player, "goblin_rune_key")
    assert success is True
    assert "goblin_rune_key" in player.archaeology.owned_keys

    # 4. 鍵獲得後は完全解読状態になっていること
    state_after = system.get_fragment_state(player, "goblin_child_screams")
    assert state_after["is_decoded"] is True
    assert state_after["has_key"] is True
    assert state_after["displayed_text"] == state_after["translated_text"]
    assert "小さな命が哭いている" in state_after["displayed_text"]
