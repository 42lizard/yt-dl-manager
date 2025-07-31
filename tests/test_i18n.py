"""Test internationalization functionality."""

import unittest
import tempfile
import os
from unittest.mock import patch

from yt_dl_manager.i18n import (
    setup_translation, _, detect_system_locale,
    get_available_languages, get_current_language
)


class TestI18n(unittest.TestCase):
    """Test internationalization functionality."""

    def setUp(self):
        """Set up test environment."""
        # Reset to English for each test
        setup_translation('en')

    def test_available_languages(self):
        """Test getting available languages."""
        languages = get_available_languages()
        self.assertIn('en', languages)
        self.assertIn('de', languages)
        self.assertEqual(len(languages), 2)

    def test_english_translation(self):
        """Test English translation (identity)."""
        setup_translation('en')
        result = _("Add a video to the queue.")
        self.assertEqual(result, "Add a video to the queue.")

    def test_german_translation(self):
        """Test German translation."""
        setup_translation('de')
        result = _("Add a video to the queue.")
        self.assertEqual(result, "Ein Video zur Warteschlange hinzufügen.")

    def test_fallback_to_english(self):
        """Test fallback to English for unsupported language."""
        setup_translation('fr')  # French not supported
        current = get_current_language()
        self.assertEqual(current, 'en')

    def test_auto_detection_fallback(self):
        """Test automatic language detection fallback."""
        with patch.dict(os.environ, {'LANG': 'invalid_locale'}):
            detected = detect_system_locale()
            self.assertEqual(detected, 'en')  # Should fallback to English

    def test_german_locale_detection(self):
        """Test German locale detection."""
        with patch('yt_dl_manager.i18n.locale.getlocale', return_value=(None, None)):
            with patch.dict(os.environ, {'LANG': 'de_DE.UTF-8'}):
                detected = detect_system_locale()
                self.assertEqual(detected, 'de')

    def test_current_language_detection(self):
        """Test current language detection."""
        setup_translation('en')
        self.assertEqual(get_current_language(), 'en')

        setup_translation('de')
        self.assertEqual(get_current_language(), 'de')

    def test_untranslated_string(self):
        """Test that untranslated strings return the original."""
        setup_translation('de')
        result = _("This string does not exist in translations")
        self.assertEqual(result, "This string does not exist in translations")


if __name__ == '__main__':
    unittest.main()