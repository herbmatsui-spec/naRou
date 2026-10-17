"""多言語キー整合テスト (Phase 3 Step 65)"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

TEXT_DIR = Path(_ROOT) / "data" / "text"
LOCALES = ("ja", "en", "ko", "zh-cn", "zh-tw")


def _flatten(d: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in d.items():
        full = f"{prefix}{k}"
        if isinstance(v, dict):
            keys |= _flatten(v, full + ".")
        else:
            keys.add(full)
    return keys


def _locale_keys(locale: str) -> set[str]:
    path = TEXT_DIR / f"{locale}.yaml"
    assert path.exists(), f"{locale}.yaml が存在しない"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _flatten(data)


def test_all_locales_have_identical_key_sets():
    """Step 65.2: 5ロケール (en/ja/ko/zh-cn/zh-tw) のキー集合が完全一致すること"""
    base = _locale_keys("ja")
    assert len(base) >= 100, f"ja ロケールのキーが異常に少ない: {len(base)}"

    for locale in ("en", "ko", "zh-cn", "zh-tw"):
        keys = _locale_keys(locale)
        missing = base - keys
        extra = keys - base
        assert not missing, f"{locale}: ja に有り {locale} に無いキー: {sorted(missing)[:8]}"
        assert not extra, f"{locale}: ja に無く {locale} に有るキー: {sorted(extra)[:8]}"


def test_english_locale_is_not_a_stub():
    """Step 65.1: en.yaml が13バイトスタブでないこと"""
    path = TEXT_DIR / "en.yaml"
    assert path.stat().st_size > 1000, f"en.yaml がまだスタブの可能性: {path.stat().st_size} bytes"
    keys = _locale_keys("en")
    assert len(keys) >= 100, f"en ロケールのキー数: {len(keys)}"


def test_default_language_is_japanese():
    """Step 65.4: 本番向け既定言語が ja であること (日本語が主言語)"""
    from localization_manager import LocalizationManager

    mgr = LocalizationManager()
    default = getattr(mgr, "default_language", None) or getattr(mgr, "language", None)
    assert default == "ja", f"既定言語が ja でない: {default}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
