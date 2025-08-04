"""Internationalization (i18n) utilities for yt-dl-manager.

This module provides translation support using Python's gettext module.
Supports automatic locale detection and manual language override.
"""

import gettext
import locale
import os
from pathlib import Path
from typing import Optional, List

# Global variables for translation
_current_translation = None  # pylint: disable=invalid-name
_available_languages = ['en', 'de']


def get_locale_dir() -> Path:
    """Get the path to the locale directory."""
    return Path(__file__).parent / 'locale'


def get_available_languages() -> List[str]:
    """Get list of available language codes."""
    return _available_languages.copy()


def detect_system_locale() -> str:
    """Detect system locale and return supported language code.

    Returns:
        Language code ('en' or 'de'), defaults to 'en' if unsupported.
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
            if lang_code in _available_languages:
                return lang_code
    except (locale.Error, AttributeError, TypeError):
        pass

    # Default to English
    return 'en'


def setup_translation(language: Optional[str] = None) -> None:
    """Set up translation for the specified language.

    Args:
        language: Language code ('en', 'de'), or None for auto-detection.
    """
    global _current_translation  # pylint: disable=global-statement

    if language is None:
        language = detect_system_locale()
    elif language not in _available_languages:
        language = 'en'

    locale_dir = get_locale_dir()

    try:
        if language == 'en':
            # For English, use null translation (no .mo file needed)
            _current_translation = gettext.NullTranslations()
        else:
            # Load translation from .mo file
            _current_translation = gettext.translation(
                'yt-dl-manager',
                localedir=str(locale_dir),
                languages=[language],
                fallback=True
            )
    except (FileNotFoundError, OSError):
        # Fallback to null translation if files not found
        _current_translation = gettext.NullTranslations()


def _(message: str) -> str:
    """Translate a message using the current translation.

    Args:
        message: The message to translate.

    Returns:
        Translated message or original if no translation available.
    """
    if _current_translation is None:
        setup_translation()

    return _current_translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a message with plural forms.

    Args:
        singular: Singular form of the message.
        plural: Plural form of the message.
        n: Number to determine which form to use.

    Returns:
        Translated message in appropriate form.
    """
    if _current_translation is None:
        setup_translation()

    return _current_translation.ngettext(singular, plural, n)


def get_current_language() -> str:
    """Get the current language code being used.

    Returns:
        Current language code ('en' or 'de').
    """
    if _current_translation is None:
        return detect_system_locale()

    # Check if we have an actual translation loaded
    if (hasattr(_current_translation, '_catalog') and
            _current_translation._catalog):  # pylint: disable=protected-access
        # We have an actual translation loaded
        return 'de'  # Currently only German is loaded from files
    return 'en'


# Initialize translation on module import
setup_translation()
