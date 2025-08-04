"""Internationalization (i18n) utilities for yt-dl-manager.

This module provides translation support using Python's gettext module.
Supports automatic locale detection and manual language override.
"""

import gettext
import locale
import os
from pathlib import Path
from typing import Optional, List


class TranslationManager:
    """Manages translation state and operations."""

    def __init__(self):
        """Initialize translation manager."""
        self.current_translation = None
        self.current_language = None

    def setup(self, language: Optional[str] = None) -> None:
        """Set up translation for the specified language.

        Args:
            language: Language code from available languages, or None for auto-detection.
        """
        if language is None:
            language = detect_system_locale()
        elif language not in get_available_languages():
            language = 'en'

        self.current_language = language
        locale_dir = get_locale_dir()

        try:
            if language == 'en':
                # For English, use null translation (no .mo file needed)
                self.current_translation = gettext.NullTranslations()
            else:
                # Load translation from .mo file
                self.current_translation = gettext.translation(
                    'yt-dl-manager',
                    localedir=str(locale_dir),
                    languages=[language],
                    fallback=True
                )
        except (FileNotFoundError, OSError):
            # Fallback to null translation if files not found
            self.current_translation = gettext.NullTranslations()

    def gettext(self, message: str) -> str:
        """Translate a message using the current translation.

        Args:
            message: The message to translate.

        Returns:
            Translated message or original if no translation available.
        """
        if self.current_translation is None:
            self.setup()

        return self.current_translation.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Translate a message with plural forms.

        Args:
            singular: Singular form of the message.
            plural: Plural form of the message.
            n: Number to determine which form to use.

        Returns:
            Translated message in appropriate form.
        """
        if self.current_translation is None:
            self.setup()

        return self.current_translation.ngettext(singular, plural, n)

    def get_current_language(self) -> str:
        """Get the current language code being used.

        Returns:
            Current language code from available languages.
        """
        if self.current_language is not None:
            return self.current_language

        if self.current_translation is None:
            return detect_system_locale()

        # Check if we have an actual translation loaded by checking the domain
        info = self.current_translation.info()
        if info:
            # We have translation info, check available languages to determine which one
            available_langs = get_available_languages()
            # Return first non-English language if we have translation info
            for lang in available_langs:
                if lang != 'en':
                    return lang
        return 'en'


# Module-level translation manager instance
translation_manager = TranslationManager()


def get_locale_dir() -> Path:
    """Get the path to the locale directory."""
    return Path(__file__).parent / 'locale'


def get_available_languages() -> List[str]:
    """Get list of available language codes by scanning locale directory."""
    locale_dir = get_locale_dir()
    # English is always available (default/source language)
    available_langs = ['en']

    if not locale_dir.exists():
        return available_langs

    # Scan for language directories with translation files
    for lang_dir in locale_dir.iterdir():
        if lang_dir.is_dir() and lang_dir.name != 'en':
            mo_file = lang_dir / 'LC_MESSAGES' / 'yt-dl-manager.mo'
            po_file = lang_dir / 'LC_MESSAGES' / 'yt-dl-manager.po'
            # Check if either .mo or .po file exists
            if mo_file.exists() or po_file.exists():
                available_langs.append(lang_dir.name)

    return sorted(available_langs)


def detect_system_locale() -> str:
    """Detect system locale and return supported language code.

    Returns:
        Language code from available languages, defaults to 'en' if unsupported.
    """
    try:
        # Get system locale
        system_locale, _ = locale.getlocale()
        if not system_locale:
            # Use LANG environment variable as fallback
            system_locale = os.environ.get('LANG', 'en_US').split('.')[0]

        if system_locale:
            # Extract language code (first 2 characters)
            lang_code = system_locale.lower()[:2]
            if lang_code in get_available_languages():
                return lang_code
    except (locale.Error, AttributeError, TypeError):
        pass

    # Default to English
    return 'en'


def setup_translation(language: Optional[str] = None) -> None:
    """Set up translation for the specified language.

    Args:
        language: Language code from available languages, or None for auto-detection.
    """
    translation_manager.setup(language)


def _(message: str) -> str:
    """Translate a message using the current translation.

    Args:
        message: The message to translate.

    Returns:
        Translated message or original if no translation available.
    """
    return translation_manager.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a message with plural forms.

    Args:
        singular: Singular form of the message.
        plural: Plural form of the message.
        n: Number to determine which form to use.

    Returns:
        Translated message in appropriate form.
    """
    return translation_manager.ngettext(singular, plural, n)


def get_current_language() -> str:
    """Get the current language code being used.

    Returns:
        Current language code from available languages.
    """
    return translation_manager.get_current_language()


# Initialize translation on module import
setup_translation()
