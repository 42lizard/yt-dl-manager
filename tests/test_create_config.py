"""Unit tests for create_config.py module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dl_manager.create_config import create_default_config, CONFIG_FILE_NAME


class TestCreateConfig(unittest.TestCase):
    """Test cases for create_config.py functions."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for config files
        # pylint: disable=consider-using-with
        self.temp_config_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_config_dir.cleanup)

        # Mock user_config_dir and user_data_dir to point to our temp directory
        self.patcher_config_dir = patch(
            'yt_dl_manager.create_config.user_config_dir',
            return_value=self.temp_config_dir.name
        )
        self.patcher_data_dir = patch(
            'yt_dl_manager.create_config.user_data_dir',
            return_value=self.temp_config_dir.name
        )
        self.mock_config_dir = self.patcher_config_dir.start()
        self.mock_data_dir = self.patcher_data_dir.start()
        self.addCleanup(self.patcher_config_dir.stop)
        self.addCleanup(self.patcher_data_dir.stop)

        self.config_file_path = Path(
            self.temp_config_dir.name) / CONFIG_FILE_NAME

    def test_create_default_config_new_file(self):
        """Test that a new config file is created when it doesn't exist."""
        self.assertFalse(self.config_file_path.exists())

        with patch('builtins.print') as mock_print:
            create_default_config()
            mock_print.assert_called_once_with(
                f"Default configuration created at: {self.config_file_path}"
            )

        self.assertTrue(self.config_file_path.exists())
        # Basic check for content
        with open(self.config_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[DEFAULT]", content)
            self.assertIn("target_folder", content)
            self.assertIn("database_path", content)

    def test_create_default_config_force_overwrite(self):
        """Test that an existing config file is overwritten with --force."""
        # Create a dummy existing config file
        with open(self.config_file_path, 'w', encoding='utf-8') as f:
            f.write("[DEFAULT]\nOLD_SETTING=old_value\n")

        self.assertTrue(self.config_file_path.exists())

        with patch('builtins.print') as mock_print:
            create_default_config(force=True)
            mock_print.assert_called_once_with(
                f"Default configuration created at: {self.config_file_path}"
            )

        self.assertTrue(self.config_file_path.exists())
        # Verify content is new, not old
        with open(self.config_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[DEFAULT]", content)
            self.assertIn("target_folder", content)
            self.assertIn("database_path", content)
            self.assertNotIn("OLD_SETTING", content)

    def test_create_default_config_no_force_no_overwrite(self):
        """Test that an existing config file is not overwritten without --force."""
        # Create a dummy existing config file
        original_content = "[DEFAULT]\nEXISTING_SETTING=existing_value\n"
        with open(self.config_file_path, 'w', encoding='utf-8') as f:
            f.write(original_content)

        self.assertTrue(self.config_file_path.exists())

        with patch('builtins.print') as mock_print:
            create_default_config(force=False)
            mock_print.assert_called_once_with(
                f"Config file already exists at: {self.config_file_path}\nUse --force to overwrite."
            )

        self.assertTrue(self.config_file_path.exists())
        # Verify content is still original
        with open(self.config_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, original_content)


if __name__ == '__main__':
    unittest.main()
