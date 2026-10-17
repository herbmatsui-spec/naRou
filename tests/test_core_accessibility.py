"""core/accessibility.py の単体テスト。

design_tokens の読み込み、色覚バリアント解決、OS アクセシビリティスタブを検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.accessibility import (
    _TOKEN_FILES,
    _VALID_VARIANTS,
    _resolve_variant,
    detect_os_a11y,
    get_active_tokens,
    load_design_tokens,
)

_VARIANTS = ("none", "deutan", "protan", "tritan", "high_contrast")


class TestResolveVariant:
    """_resolve_variant（色覚バリアント解決）をテストする。"""

    @pytest.mark.parametrize("variant", _VARIANTS)
    def test_valid_variant_returned_as_is(self, variant):
        """有効なバリアントはそのまま返される。"""
        assert _resolve_variant(variant) == variant

    def test_invalid_variant_falls_back_to_none(self, monkeypatch):
        """不正なバリアントは 'none' にフォールバックする。"""
        monkeypatch.delenv("COLOR_VISION", raising=False)
        assert _resolve_variant("invalid_variant") == "none"

    def test_env_color_vision_overrides_requested(self, monkeypatch):
        """COLOR_VISION 環境変数が引数より優先される。"""
        monkeypatch.setenv("COLOR_VISION", "deutan")
        assert _resolve_variant("none") == "deutan"

    def test_env_invalid_falls_back_to_none(self, monkeypatch):
        """COLOR_VISION が不正値なら 'none' にフォールバックする。"""
        monkeypatch.setenv("COLOR_VISION", "bogus")
        assert _resolve_variant("deutan") == "none"


class TestLoadDesignTokens:
    """load_design_tokens をテストする。"""

    @pytest.mark.parametrize("variant", _VARIANTS)
    def test_variant_returns_dict_with_color(self, variant):
        """各バリアントのトークンファイルを読み込み dict を返す。"""
        tokens = load_design_tokens(variant)
        assert isinstance(tokens, dict)
        assert "color" in tokens

    def test_invalid_variant_loads_none_file(self):
        """不正なバリアントは design_tokens.json を読む。"""
        tokens = load_design_tokens("bogus")
        assert isinstance(tokens, dict)
        assert "color" in tokens

    def test_missing_file_falls_back_to_design_tokens_json(self, monkeypatch):
        """指定ファイルが存在しない場合 design_tokens.json にフォールバックする。"""
        monkeypatch.setattr(Path, "exists", lambda self: False)
        tokens = load_design_tokens("deutan")
        assert isinstance(tokens, dict)
        assert "color" in tokens

    def test_token_files_covers_all_variants(self):
        """_TOKEN_FILES と _VALID_VARIANTS は全バリアントを網羅する。"""
        assert set(_TOKEN_FILES.keys()) == _VALID_VARIANTS
        for variant in _VARIANTS:
            assert variant in _TOKEN_FILES


class TestGetActiveTokens:
    """get_active_tokens をテストする。"""

    def test_get_active_tokens_returns_dict(self):
        """デフォルト（color_vision=none）でトークン dict を返す。"""
        tokens = get_active_tokens()
        assert isinstance(tokens, dict)
        assert "color" in tokens

    def test_get_active_tokens_uses_config_variant(self, monkeypatch):
        """config の accessibility.color_vision を見てトークンを返す。"""

        def fake_get_config(key, default=None):
            return "deutan" if key == "accessibility.color_vision" else default

        monkeypatch.setattr("config.get_config", fake_get_config)
        tokens = get_active_tokens()
        assert isinstance(tokens, dict)
        assert "color" in tokens


class TestDetectOsA11y:
    """detect_os_a11y をテストする。"""

    def test_detect_os_a11y_always_returns_none(self):
        """プラットフォーム非依存のスタブで常に 'none' を返す。"""
        assert detect_os_a11y() == "none"

