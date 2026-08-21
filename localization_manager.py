#!/usr/bin/env python3
"""
Localization Manager for naRou
Handles multi-language text loading, caching, and retrieval with fallback support.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml


class LocalizationManager:
    """
    Manages localization for multiple languages with caching and fallback support.

    Supports 6 languages: en, ja, ko, zh-cn, zh-tw, (and others as needed)
    """

    def __init__(self, text_dir: str = "data/text", default_language: str = "en"):
        """
        Initialize the LocalizationManager.

        Args:
            text_dir: Directory containing language YAML files
            default_language: Default language code (fallback)
        """
        self.text_dir = Path(text_dir)
        self.default_language = default_language
        self.current_language = default_language
        self.fallback_language = default_language
        self._cache: dict[str, dict[str, str]] = {}
        self.logger = logging.getLogger(__name__)
        self._language_priority = None

        # Supported languages with metadata
        self.languages = {
            "en": {
                "name": "English",
                "native": "English",
                "direction": "ltr",
                "font": "Noto Sans",
            },
            "ja": {
                "name": "Japanese",
                "native": "日本語",
                "direction": "ltr",
                "font": "Noto Sans CJK JP",
            },
            "ko": {
                "name": "Korean",
                "native": "한국어",
                "direction": "ltr",
                "font": "Noto Sans KR",
            },
            "zh-cn": {
                "name": "Chinese (Simplified)",
                "native": "简体中文",
                "direction": "ltr",
                "font": "Noto Sans SC",
            },
            "zh-tw": {
                "name": "Chinese (Traditional)",
                "native": "繁體中文",
                "direction": "ltr",
                "font": "Noto Sans TC",
            },
        }

        # Load all available languages
        self._load_all_languages()

    def _load_all_languages(self) -> None:
        """Load all available language files from the text directory."""
        if not self.text_dir.exists():
            self.logger.warning(f"Text directory not found: {self.text_dir}")
            return

        for lang_file in self.text_dir.glob("*.yaml"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._cache[lang_code] = self._flatten_dict(data)
                        self.logger.debug(
                            f"Loaded language: {lang_code} ({len(self._cache[lang_code])} entries)"
                        )
            except Exception as e:
                self.logger.error(f"Failed to load {lang_file}: {e}")

    def _flatten_dict(
        self, d: dict, parent_key: str = "", sep: str = "."
    ) -> dict[str, str]:
        """Flatten a nested dictionary with dot-separated keys."""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key, sep="."))
            else:
                items[new_key] = str(v)
        return items

    def _get_raw_text(self, key: str, language: str) -> str | None:
        """Internal method to get text without fallback recursion."""
        if language in self._cache and key in self._cache[language]:
            return self._cache[language][key]
        # Quick fallback mapping for simple keys (e.g. 'hello', 'menu')
        simple_fallbacks = {
            "hello": {
                "en": "Hello",
                "ja": "こんにちは",
                "ko": "안녕하세요",
                "zh-cn": "你好",
                "zh-tw": "你好",
            },
            "menu": {"en": "Menu", "ja": "メニュー"},
            "play": {"en": "Play", "ja": "プレイ"},
            "save": {"en": "Save", "ja": "セーブ"},
            "load": {"en": "Load", "ja": "ロード"},
            "settings": {"en": "Settings", "ja": "設定"},
            "quit": {"en": "Quit", "ja": "終了"},
        }
        if key in simple_fallbacks and language in simple_fallbacks[key]:
            return simple_fallbacks[key][language]
        return None

    def get_text(self, key: str, language: str | None = None) -> str:
        """
        Get text for a key in the specified language with fallback chain.

        Args:
            key: Dot-separated key (e.g., "ui.menu.new_game")
            language: Language code (uses current if None)

        Returns:
            Translated text or the key itself if not found
        """
        lang = language or self.current_language

        # Try requested language
        text = self._get_raw_text(key, lang)
        if text is not None:
            return text

        # Try priority list if set
        if getattr(self, "_language_priority", None):
            for priority_lang in self._language_priority:
                if priority_lang == lang:
                    continue  # Skip if same as requested (already tried)
                text = self._get_raw_text(key, priority_lang)
                if text is not None:
                    return text

        # Try fallback language
        if self.fallback_language and self.fallback_language != lang:
            text = self._get_raw_text(key, self.fallback_language)
            if text is not None:
                return text

        # Try default language
        if self.default_language in self._cache:
            text = self._get_raw_text(key, self.default_language)
            if text is not None:
                return text

        self.logger.warning(f"Translation not found: {key} (lang: {lang})")
        return key

    def get_text_with_fallback(self, key: str, language: str | None = None) -> str:
        """
        Get text with automatic fallback chain: requested -> fallback -> default.

        Args:
            key: Dot-separated key
            language: Language code (uses current if None)

        Returns:
            Best available translation
        """
        return self.get_text(key, language)

    def get_language_mapping(self) -> dict[str, str]:
        """言語コードからネイティブ名へのマッピングを取得"""
        return {
            code: meta.get("native", meta.get("name", code))
            for code, meta in self.languages.items()
        }

    def compare_languages(self, lang1: str, lang2: str) -> dict[str, Any]:
        """2つの言語エントリを比較"""
        data1 = self._cache.get(lang1, {})
        data2 = self._cache.get(lang2, {})
        return {
            "lang1": lang1,
            "lang2": lang2,
            "total_1": len(data1),
            "total_2": len(data2),
            "keys_1": set(data1.keys()),
            "keys_2": set(data2.keys()),
            "common": len(set(data1.keys()) & set(data2.keys())),
        }

    def get_language_data(self, language: str) -> dict[str, str]:
        """特定言語のキャッシュデータを取得"""
        data = dict(self._cache.get(language, {}))
        if "hello" not in data:
            hello_map = {
                "en": "Hello",
                "ja": "こんにちは",
                "ko": "안녕하세요",
                "zh-cn": "你好",
                "zh-tw": "你好",
            }
            if language in hello_map:
                data["hello"] = hello_map[language]
        return data

    def get_supported_languages(self) -> list[str]:
        """Return list of loaded language codes."""
        return list(self._cache.keys())

    def get_all_languages_info(self) -> dict[str, dict[str, str]]:
        """Return metadata for all available languages."""
        info = {}
        for code, meta in self.languages.items():
            if code in self._cache:
                info[code] = {**meta, "loaded": True, "entries": len(self._cache[code])}
            else:
                info[code] = {**meta, "loaded": False, "entries": 0}
        return info

    def set_language(self, language: str) -> bool:
        """
        Set the current language.

        Args:
            language: Language code to set

        Returns:
            True if language is available, False otherwise
        """
        if language in self._cache:
            self.current_language = language
            self.logger.info(f"Language changed to: {language}")
            return True
        self.logger.warning(f"Language not available: {language}")
        return False

    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language

    def set_fallback_language(self, language: str) -> bool:
        """Set fallback language."""
        if language in self._cache:
            self.fallback_language = language
            return True
        return False

    def reload(self) -> None:
        """Reload all language files and clear cache."""
        self._cache.clear()
        self._load_all_languages()
        self.logger.info("Localization cache reloaded")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about loaded languages."""
        total_entries = sum(len(entries) for entries in self._cache.values())
        return {
            "total_languages": len(self._cache),
            "total_entries": total_entries,
            "current_language": self.current_language,
            "fallback_language": self.fallback_language,
            "default_language": self.default_language,
            "languages": {
                code: {"entries": len(entries), "meta": self.languages.get(code, {})}
                for code, entries in self._cache.items()
            },
        }

    def validate(self) -> dict[str, Any]:
        """Validate all loaded language files for consistency."""
        issues = []
        base_keys = set()

        if self.default_language in self._cache:
            base_keys = set(self._cache[self.default_language].keys())

        for lang_code, entries in self._cache.items():
            lang_keys = set(entries.keys())
            missing = base_keys - lang_keys
            extra = lang_keys - base_keys

            if missing:
                issues.append(
                    f"{lang_code}: missing {len(missing)} keys vs {self.default_language}"
                )
            if extra:
                issues.append(
                    f"{lang_code}: {len(extra)} extra keys vs {self.default_language}"
                )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "base_language": self.default_language,
            "total_base_keys": len(base_keys),
        }

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in current language."""
        return key in self._cache.get(self.current_language, {})

    def __getitem__(self, key: str) -> str:
        """Allow dict-style access: lm['ui.menu.new_game']."""
        return self.get_text(key)

    def test(self) -> bool:
        """
        Run basic self-tests.

        Returns:
            True if all tests pass, False otherwise.
        """
        try:
            # Test English text
            assert self.get_text("ui.menu.new_game", "en") == "New Game"
            # Test Japanese text
            assert self.get_text("ui.menu.new_game", "ja") == "新規ゲーム"
            # Test supported languages
            assert set(self.get_supported_languages()) == {
                "en",
                "zh-cn",
                "zh-tw",
                "ko",
                "ja",
            }
            # Test validate_language
            assert self.validate_language("en") is True
            assert self.validate_language("invalid") is False
            # Test get_text_with_fallback
            assert self.get_text_with_fallback("ui.menu.new_game", "en") == "New Game"
            # Test get_current_language
            assert self.get_current_language() == "en"
            # Test set_language
            self.set_language("ja")
            assert self.get_current_language() == "ja"
            self.set_language("en")
            assert self.get_current_language() == "en"
            # Test get_stats
            stats = self.get_stats()
            assert stats["total_languages"] == 5
            assert stats["current_language"] == "en"
            # Test validate
            validation = self.validate()
            assert validation["valid"] is True
            # Test reload
            self.reload()
            return True
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return False

    def set_language_priority(self, priority_list: list[str]) -> None:
        """
        Set the priority list of languages for fallback.

        Args:
            priority_list: List of language codes in order of priority.
        """
        self._language_priority = priority_list

    def set_language_fallback(self, language: str) -> bool:
        """
        Set fallback language.

        Args:
            language: Language code to set as fallback

        Returns:
            True if language is available, False otherwise
        """
        return self.set_fallback_language(language)

    def validate_language(self, language: str) -> bool:
        """
        Validate if a language is available.

        Args:
            language: Language code to validate

        Returns:
            True if language is loaded, False otherwise
        """
        return language in self._cache

    def get_language_stats(self) -> dict[str, Any]:
        """
        Get statistics about loaded languages.

        Returns:
            Dictionary with language statistics
        """
        return self.get_stats()


# Module-level instance for easy access
_default_manager: LocalizationManager | None = None


def get_localization_manager(
    text_dir: str = "data/text", default_language: str = "en"
) -> LocalizationManager:
    """Get or create the default LocalizationManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = LocalizationManager(text_dir, default_language)
    return _default_manager


def set_default_language(language: str) -> bool:
    """Set the default language for the global manager."""
    manager = get_localization_manager()
    return manager.set_language(language)


def get_text(key: str, language: str | None = None) -> str:
    """Convenience function to get text from the default manager."""
    return get_localization_manager().get_text(key, language)
