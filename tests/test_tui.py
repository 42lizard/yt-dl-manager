"""Tests for the TUI (Text User Interface) module."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import sys
from io import StringIO

# Add the parent directory to the Python path for importing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dl_manager.tui import main as tui_main
from yt_dl_manager.db_utils import DatabaseUtils


class TestTUI(unittest.TestCase):
    """Test cases for TUI functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name

    def tearDown(self):
        """Clean up after each test."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_creates_database(self, mock_stdout, mock_input):
        """Test that TUI creates database if it doesn't exist."""
        # Set up mock input to exit immediately
        mock_input.side_effect = ['6']  # Exit option

        # Mock the config to use our test database
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_utils.return_value = mock_db_instance

            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance.return_value = mock_maintenance_instance

                # Run TUI
                tui_main()

                # Verify database utils was initialized (which creates database)
                mock_db_utils.assert_called_once()
                mock_maintenance.assert_called_once()

                # Check that the database path was printed
                output = mock_stdout.getvalue()
                self.assertIn("Database initialized at:", output)
                self.assertIn("YT-DL-MANAGER - Text User Interface", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_status_command(self, mock_stdout, mock_input):
        """Test that TUI status command works."""
        # Set up mock input: status, then exit
        mock_input.side_effect = ['1', '6']
        
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_utils.return_value = mock_db_instance
            
            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance.return_value = mock_maintenance_instance
                
                # Run TUI
                tui_main()
                
                # Verify show_status was called twice (once at start, once from menu)
                self.assertEqual(mock_maintenance_instance.show_status.call_count, 2)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_add_url_command(self, mock_stdout, mock_input):
        """Test that TUI add URL command works."""
        test_url = "https://www.youtube.com/watch?v=test"
        # Set up mock input: add URL, then exit
        mock_input.side_effect = ['5', test_url, '6']
        
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_instance.add_url.return_value = (True, f"URL added to queue: {test_url}", 1)
            mock_db_utils.return_value = mock_db_instance
            
            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance.return_value = mock_maintenance_instance
                
                # Run TUI
                tui_main()
                
                # Verify add_url was called with test URL
                mock_db_instance.add_url.assert_called_once_with(test_url)
                
                # Check output shows success
                output = mock_stdout.getvalue()
                self.assertIn("✓", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_list_commands(self, mock_stdout, mock_input):
        """Test that TUI list commands work."""
        # Test pending, failed, downloaded lists, then exit
        mock_input.side_effect = ['2', '3', '4', '6']
        
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_utils.return_value = mock_db_instance
            
            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance_instance.list_downloads.return_value = []
                mock_maintenance.return_value = mock_maintenance_instance
                
                # Run TUI
                tui_main()
                
                # Verify list_downloads was called for each status
                expected_calls = [
                    unittest.mock.call(status='pending', limit=10),
                    unittest.mock.call(status='failed', limit=10),
                    unittest.mock.call(status='downloaded', limit=10)
                ]
                mock_maintenance_instance.list_downloads.assert_has_calls(expected_calls)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_keyboard_interrupt(self, mock_stdout, mock_input):
        """Test that TUI handles keyboard interrupt gracefully."""
        # Simulate keyboard interrupt
        mock_input.side_effect = KeyboardInterrupt()
        
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_utils.return_value = mock_db_instance
            
            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance.return_value = mock_maintenance_instance
                
                # Run TUI (should not raise exception)
                tui_main()
                
                # Check that goodbye message was printed
                output = mock_stdout.getvalue()
                self.assertIn("Goodbye!", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_invalid_choice(self, mock_stdout, mock_input):
        """Test that TUI handles invalid menu choices."""
        # Invalid choice, then exit
        mock_input.side_effect = ['9', '6']
        
        with patch('yt_dl_manager.tui.DatabaseUtils') as mock_db_utils:
            mock_db_instance = MagicMock()
            mock_db_instance.db_path = self.db_path
            mock_db_utils.return_value = mock_db_instance
            
            with patch('yt_dl_manager.tui.MaintenanceCommands') as mock_maintenance:
                mock_maintenance_instance = MagicMock()
                mock_maintenance.return_value = mock_maintenance_instance
                
                # Run TUI
                tui_main()
                
                # Check that invalid choice message was shown
                output = mock_stdout.getvalue()
                self.assertIn("Invalid choice", output)

    @patch('yt_dl_manager.tui.DatabaseUtils')
    @patch('sys.stdout', new_callable=StringIO)
    def test_tui_database_error(self, mock_stdout, mock_db_utils):
        """Test that TUI handles database initialization errors."""
        # Make DatabaseUtils raise an exception
        mock_db_utils.side_effect = OSError("Database connection failed")

        # Run TUI (should exit with error)
        with self.assertRaises(SystemExit) as cm:
            tui_main()

        # Check exit code
        self.assertEqual(cm.exception.code, 1)

        # Check error message was displayed
        output = mock_stdout.getvalue()
        self.assertIn("Error initializing database", output)


if __name__ == '__main__':
    unittest.main()