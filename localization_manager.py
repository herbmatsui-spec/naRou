"""
LocalizationManager - Internationalization text management system.

This module provides functionality for loading and managing localized text
from YAML files for multiple languages.
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Any


class LocalizationManager:
    """Manages localized text for multiple languages."""

    def __init__(self, text_dir: str = "data/text", default_language: str = "en"):
        """Initialize the LocalizationManager.

        Args:
            text_dir: Directory containing language YAML files.
            default_language: Default language code to use.
        """
        self.text_dir = text_dir
        self.default_language = default_language
        self._cache: Dict[str, Dict[str, str]] = {}
        self._supported_languages: List[str] = []
        self._current_language = default_language
        self._language_priority: List[str] = [default_language]
        self._fallback_language = default_language
        self._config: Dict[str, Any] = {}
        self.config = self._config
        self.logger = logging.getLogger(__name__)
        self._load_all_languages()

    def _load_all_languages(self) -> None:
        """Load all language files from the text directory."""
        if not os.path.exists(self.text_dir):
            self.logger.warning(f"Text directory not found: {self.text_dir}")
            return

        for filename in os.listdir(self.text_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                lang_code = filename[:-5] if filename.endswith('.yaml') else filename[:-4]
                filepath = os.path.join(self.text_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data:
                            self._cache[lang_code] = data
                            if lang_code not in self._supported_languages:
                                self._supported_languages.append(lang_code)
                            self.logger.info(f"Loaded language: {lang_code} ({len(data)} entries)")
                except Exception as e:
                    self.logger.error(f"Failed to load language file {filename}: {e}")

    def get_text(self, key: str, language: str = None) -> str:
        """Get localized text for a key.

        Args:
            key: The text key to look up.
            language: Language code (uses current language if None).

        Returns:
            The localized text, or the key if not found.
        """
        if language is None:
            language = self._current_language

        if language in self._cache and key in self._cache[language]:
            return self._cache[language][key]

        # Try default language
        if language != self.default_language and self.default_language in self._cache:
            if key in self._cache[self.default_language]:
                return self._cache[self.default_language][key]

        return key

    def get_language_data(self, language: str) -> Dict[str, str]:
        """Return the raw text dictionary for a language.

        Args:
            language: Language code.

        Returns:
            Mapping of text keys to localized strings (empty if unsupported).
        """
        return dict(self._cache.get(language, {}))

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes.

        Returns:
            List of supported language codes.
        """
        return self._supported_languages.copy()

    def get_text_with_fallback(self, key: str, language: str = None) -> str:
        """Get localized text with fallback through priority languages.

        Args:
            key: The text key to look up.
            language: Language code to start with.

        Returns:
            The localized text, or the key if not found in any language.
        """
        if language is None:
            language = self._current_language

        # Try requested language first
        result = self.get_text(key, language)
        if result != key:
            return result

        # Try priority languages
        for lang in self._language_priority:
            if lang != language:
                result = self.get_text(key, lang)
                if result != key:
                    return result

        # Try fallback language
        if self._fallback_language != language:
            result = self.get_text(key, self._fallback_language)
            if result != key:
                return result

        return key

    def set_language(self, language: str) -> bool:
        """Set the current language.

        Args:
            language: Language code to set.

        Returns:
            True if language is supported, False otherwise.
        """
        if language in self._supported_languages:
            self._current_language = language
            self.logger.info(f"Language set to: {language}")
            return True
        self.logger.warning(f"Language not supported: {language}")
        return False

    def get_current_language(self) -> str:
        """Get the current language code.

        Returns:
            Current language code.
        """
        return self._current_language

    def set_language_priority(self, languages: List[str]) -> None:
        """Set language fallback priority order.

        Args:
            languages: List of language codes in priority order.
        """
        valid_langs = [lang for lang in languages if lang in self._supported_languages]
        self._language_priority = valid_langs
        self.logger.info(f"Language priority set to: {valid_langs}")

    def set_language_fallback(self, language: str) -> bool:
        """Set the fallback language.

        Args:
            language: Language code to use as fallback.

        Returns:
            True if language is supported, False otherwise.
        """
        if language in self._supported_languages:
            self._fallback_language = language
            self.logger.info(f"Fallback language set to: {language}")
            return True
        self.logger.warning(f"Fallback language not supported: {language}")
        return False

    def validate_language(self, language: str) -> bool:
        """Validate if a language is supported.

        Args:
            language: Language code to validate.

        Returns:
            True if supported, False otherwise.
        """
        return language in self._supported_languages

    def get_language_info(self, language: str) -> Optional[Dict[str, Any]]:
        """Get information about a language.

        Args:
            language: Language code.

        Returns:
            Dictionary with language info, or None if not supported.
        """
        if language not in self._supported_languages:
            return None
        return {
            'code': language,
            'entry_count': len(self._cache.get(language, {})),
            'is_current': language == self._current_language,
            'is_fallback': language == self._fallback_language,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded languages.

        Returns:
            Dictionary with statistics.
        """
        return {
            'supported_languages': self._supported_languages,
            'current_language': self._current_language,
            'fallback_language': self._fallback_language,
            'language_priority': self._language_priority,
            'total_entries': sum(len(v) for v in self._cache.values()),
            'entries_per_language': {k: len(v) for k, v in self._cache.items()},
        }

    def validate(self) -> Dict[str, Any]:
        """Validate all loaded language data for consistency.

        Returns:
            Dictionary with validation results.
        """
        results = {
            'valid': True,
            'issues': [],
            'warnings': [],
        }

        if not self._supported_languages:
            results['valid'] = False
            results['issues'].append("No languages loaded")
            return results

        # Check all languages have same keys (using default as reference)
        reference_keys = set(self._cache.get(self.default_language, {}).keys())
        for lang in self._supported_languages:
            if lang == self.default_language:
                continue
            lang_keys = set(self._cache.get(lang, {}).keys())
            missing = reference_keys - lang_keys
            extra = lang_keys - reference_keys
            if missing:
                results['warnings'].append(f"Language {lang} missing keys: {missing}")
            if extra:
                results['warnings'].append(f"Language {lang} has extra keys: {extra}")

        return results

    def reload(self) -> None:
        """Reload all language files from disk."""
        self._cache.clear()
        self._supported_languages.clear()
        self._load_all_languages()
        self.logger.info("All languages reloaded")

    def export_languages(self, output_dir: str) -> None:
        """Export all languages to YAML files.

        Args:
            output_dir: Directory to export to.
        """
        os.makedirs(output_dir, exist_ok=True)
        for lang, data in self._cache.items():
            filepath = os.path.join(output_dir, f"{lang}.yaml")
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=True)
            self.logger.info(f"Exported {lang} to {filepath}")

    def detect_language(self) -> str:
        """Detect system/browser language (stub implementation).

        Returns:
            Detected language code or default.
        """
        # In a real implementation, this would detect from system locale
        # For now, return default
        import locale
        try:
            sys_lang = locale.getdefaultlocale()[0]
            if sys_lang:
                # Convert locale format (e.g., ja_JP) to our format (ja)
                lang_code = sys_lang.split('_')[0].lower()
                if lang_code in self._supported_languages:
                    return lang_code
        except Exception:
            pass
        return self.default_language

    def compare_languages(self, language1: str, language2: str) -> Dict[str, Any]:
        """Compare two languages.

        Args:
            language1: First language code.
            language2: Second language code.

        Returns:
            Dictionary with comparison results.
        """
        if language1 not in self._supported_languages or language2 not in self._supported_languages:
            return {'error': 'One or both languages not supported'}

        keys1 = set(self._cache.get(language1, {}).keys())
        keys2 = set(self._cache.get(language2, {}).keys())

        return {
            'language1': language1,
            'language2': language2,
            'common_keys': list(keys1 & keys2),
            'only_in_1': list(keys1 - keys2),
            'only_in_2': list(keys2 - keys1),
            'total_1': len(keys1),
            'total_2': len(keys2),
            'match_percentage': len(keys1 & keys2) / max(len(keys1), len(keys2)) * 100 if keys1 or keys2 else 0,
        }

    def get_language_mapping(self) -> Dict[str, str]:
        """Get language code to display name mapping.

        Returns:
            Dictionary mapping language codes to display names.
        """
        mapping = {
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'zh-cn': '简体中文',
            'zh-tw': '繁體中文',
        }
        return {k: v for k, v in mapping.items() if k in self._supported_languages}

    def translate_text(self, text: str, from_lang: str, to_lang: str) -> str:
        """Translate text from one language to another (finds key and returns translation).

        Args:
            text: Text to translate.
            from_lang: Source language code.
            to_lang: Target language code.

        Returns:
            Translated text or original text if not found.
        """
        if from_lang not in self._supported_languages or to_lang not in self._supported_languages:
            return text

        # Find key by reverse lookup
        key = None
        for k, v in self._cache.get(from_lang, {}).items():
            if v == text:
                key = k
                break

        if key is None:
            return text

        return self.get_text(key, to_lang)

    def sync_languages(self) -> Dict[str, Any]:
        """Synchronize languages by ensuring all have the same keys.

        Returns:
            Dictionary with sync results.
        """
        reference_keys = set(self._cache.get(self.default_language, {}).keys())
        results = {'added': {}, 'removed': {}}

        for lang in self._supported_languages:
            if lang == self.default_language:
                continue
            lang_keys = set(self._cache.get(lang, {}).keys())
            missing = reference_keys - lang_keys
            extra = lang_keys - reference_keys

            if missing:
                for k in missing:
                    self._cache[lang][k] = self._cache[self.default_language][k]
                results['added'][lang] = list(missing)

            if extra:
                for k in extra:
                    del self._cache[lang][k]
                results['removed'][lang] = list(extra)

        self.logger.info(f"Languages synced: {results}")
        return results

    def backup_languages(self, backup_dir: str = "data/text_backup") -> None:
        """Backup all language files.

        Args:
            backup_dir: Directory to store backup.
        """
        import shutil
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(self.text_dir, backup_dir)
        self.logger.info(f"Languages backed up to {backup_dir}")

    def restore_languages(self, backup_dir: str = "data/text_backup") -> None:
        """Restore languages from backup.

        Args:
            backup_dir: Directory containing backup.
        """
        import shutil
        if os.path.exists(self.text_dir):
            shutil.rmtree(self.text_dir)
        shutil.copytree(backup_dir, self.text_dir)
        self.reload()
        self.logger.info(f"Languages restored from {backup_dir}")

    def import_languages(self, import_dir: str) -> Dict[str, Any]:
        """Import languages from directory.

        Args:
            import_dir: Directory containing language YAML files.

        Returns:
            Dictionary with import results.
        """
        results = {'imported': [], 'failed': []}
        for filename in os.listdir(import_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                lang_code = filename[:-5] if filename.endswith('.yaml') else filename[:-4]
                filepath = os.path.join(import_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data:
                            self._cache[lang_code] = data
                            if lang_code not in self._supported_languages:
                                self._supported_languages.append(lang_code)
                            results['imported'].append(lang_code)
                except Exception as e:
                    results['failed'].append({'language': lang_code, 'error': str(e)})
        self.logger.info(f"Languages imported: {results}")
        return results

    def merge_languages(self, language1: str, language2: str, target_language: str) -> bool:
        """Merge two languages into a target language.

        Args:
            language1: First source language.
            language2: Second source language.
            target_language: Target language code.

        Returns:
            True if successful, False otherwise.
        """
        if language1 not in self._supported_languages or language2 not in self._supported_languages:
            return False

        merged = {}
        merged.update(self._cache.get(language1, {}))
        merged.update(self._cache.get(language2, {}))

        self._cache[target_language] = merged
        if target_language not in self._supported_languages:
            self._supported_languages.append(target_language)
        self.logger.info(f"Merged {language1} and {language2} into {target_language}")
        return True

    def split_languages(self, source_language: str, target_languages: List[str], key_mapping: Dict[str, str]) -> bool:
        """Split a language into multiple languages based on key mapping.

        Args:
            source_language: Source language to split.
            target_languages: List of target language codes.
            key_mapping: Mapping of keys to target languages.

        Returns:
            True if successful, False otherwise.
        """
        if source_language not in self._supported_languages:
            return False

        source_data = self._cache.get(source_language, {})
        for target in target_languages:
            self._cache[target] = {}
            if target not in self._supported_languages:
                self._supported_languages.append(target)

        for key, value in source_data.items():
            target = key_mapping.get(key, target_languages[0])
            if target in self._cache:
                self._cache[target][key] = value

        self.logger.info(f"Split {source_language} into {target_languages}")
        return True

    def combine_languages(self, languages: List[str], target_language: str) -> bool:
        """Combine multiple languages into one.

        Args:
            languages: List of source language codes.
            target_language: Target language code.

        Returns:
            True if successful, False otherwise.
        """
        for lang in languages:
            if lang not in self._supported_languages:
                return False

        combined = {}
        for lang in languages:
            combined.update(self._cache.get(lang, {}))

        self._cache[target_language] = combined
        if target_language not in self._supported_languages:
            self._supported_languages.append(target_language)
        self.logger.info(f"Combined {languages} into {target_language}")
        return True

    def separate_languages(self, source_language: str, separator_key: str) -> Dict[str, Dict[str, str]]:
        """Separate a language by a separator key prefix.

        Args:
            source_language: Language to separate.
            separator_key: Key prefix to separate by.

        Returns:
            Dictionary of separated language data.
        """
        if source_language not in self._supported_languages:
            return {}

        source_data = self._cache.get(source_language, {})
        separated = {}

        for key, value in source_data.items():
            key_str = str(key)
            if key_str.startswith(separator_key):
                suffix = key_str[len(separator_key):]
                if suffix not in separated:
                    separated[suffix] = {}
                separated[suffix][key] = value

        self.logger.info(f"Separated {source_language} by {separator_key}: {len(separated)} groups")
        return separated

    def integrate_languages(self) -> Dict[str, Any]:
        """Integrate all languages - validate, sync, and report.

        Returns:
            Dictionary with integration results.
        """
        validation = self.validate()
        sync_result = self.sync_languages()
        stats = self.get_stats()

        return {
            'validation': validation,
            'sync': sync_result,
            'stats': stats,
            'integrated': True,
        }

    def test(self) -> bool:
        """Run basic self-tests.

        Returns:
            True if all tests pass, False otherwise.
        """
        try:
            assert self.get_text('hello', 'en') == 'Hello'
            assert self.get_text('hello', 'ja') == 'こんにちは'
            assert self.get_supported_languages() == ['en', 'zh-cn', 'zh-tw', 'ko', 'ja']
            assert self.validate_language('en') is True
            assert self.validate_language('invalid') is False
            assert self.get_text_with_fallback('missing_key', 'en') == 'missing_key'
            assert self.get_current_language() == 'en'
            self.set_language('ja')
            assert self.get_current_language() == 'ja'
            self.set_language('en')
            assert self.get_stats()['total_entries'] == 175
            assert self.validate()['valid'] is True
            self.reload()
            return True
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return False


__all__ = ['LocalizationManager']