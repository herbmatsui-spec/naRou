"""Unit tests for ConfigManager."""

from __future__ import annotations

from config_manager import ConfigManager, get_config_manager


def test_missing_config_returns_empty():
    cfg = ConfigManager("nonexistent_config_file.yaml")
    assert cfg.config == {}


def test_get_default_when_missing():
    cfg = ConfigManager("nonexistent_config_file.yaml")
    assert cfg.get("does_not_exist", "fallback") == "fallback"


def test_player_and_pet_config_defaults():
    cfg = ConfigManager("nonexistent_config_file.yaml")
    assert cfg.get_player_config() == {}
    assert cfg.get_pet_config() == {}


def test_global_singleton():
    a = get_config_manager()
    b = get_config_manager()
    assert a is b


def test_telemetry_default_off():
    cfg = ConfigManager("nonexistent_config_file.yaml")
    assert cfg.get_telemetry_enabled() is False
