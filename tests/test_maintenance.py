"""Tests for maintenance commands functionality."""

import unittest
import tempfile
import os
import json
from unittest.mock import patch
from yt_dl_manager.maintenance import MaintenanceCommands


class TestMaintenanceCommands(unittest.TestCase):
    """Test cases for MaintenanceCommands class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        os.close(self.test_db_fd)
        self.maintenance = MaintenanceCommands(self.test_db_path)

        # Add some test data
        self.test_urls = [
            "https://example.com/video1",
            "https://example.com/video2",
            "https://example.com/video3"
        ]

        for url in self.test_urls:
            self.maintenance.db.add_url(url)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_list_downloads_pending(self):
        """Test listing pending downloads."""
        downloads = self.maintenance.list_downloads('pending')
        self.assertEqual(len(downloads), 3)
        self.assertEqual(downloads[0]['status'], 'pending')

    def test_list_downloads_with_limit(self):
        """Test listing downloads with limit."""
        downloads = self.maintenance.list_downloads('pending', limit=2)
        self.assertEqual(len(downloads), 2)

    def test_list_downloads_missing_files(self):
        """Test listing downloads with missing files."""
        # Mark one as downloaded with non-existent file
        self.maintenance.db.mark_downloaded(
            1, "/nonexistent/file.mp4", "youtube")

        downloads = self.maintenance.list_downloads(
            'downloaded', missing_files=True)
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0]['id'], 1)

    @patch('builtins.print')
    def test_print_downloads_table_pending(self, mock_print):
        """Test printing pending downloads table."""
        downloads = self.maintenance.list_downloads('pending')
        self.maintenance.print_downloads_table(downloads, 'pending')

        # Check that print was called with table headers
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('PENDING DOWNLOADS' in call for call in calls))
        self.assertTrue(
            any('ID' in call and 'RETRIES' in call for call in calls))

    @patch('builtins.print')
    def test_print_downloads_table_empty(self, mock_print):
        """Test printing empty downloads table."""
        self.maintenance.print_downloads_table([], 'pending')
        mock_print.assert_called_with("No pending downloads found.")

    @patch('builtins.print')
    def test_show_status(self, mock_print):
        """Test show status command."""
        self.maintenance.show_status()

        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any('YT-DL-MANAGER QUEUE STATUS' in call for call in calls))
        self.assertTrue(any('Total downloads:' in call for call in calls))

    def test_remove_failed_dry_run(self):
        """Test removing failed downloads in dry run mode."""
        # Mark one as failed
        self.maintenance.db.mark_failed(1)

        count = self.maintenance.remove_failed(dry_run=True)
        self.assertEqual(count, 1)

        # Verify item still exists
        remaining = self.maintenance.list_downloads('failed')
        self.assertEqual(len(remaining), 1)

    def test_remove_failed_actual(self):
        """Test actually removing failed downloads."""
        # Mark one as failed
        self.maintenance.db.mark_failed(1)

        count = self.maintenance.remove_failed(dry_run=False)
        self.assertEqual(count, 1)

        # Verify item is removed
        remaining = self.maintenance.list_downloads('failed')
        self.assertEqual(len(remaining), 0)

    def test_remove_by_ids(self):
        """Test removing downloads by IDs."""
        count = self.maintenance.remove_by_ids([1, 2])
        self.assertEqual(count, 2)

        # Verify items are removed
        remaining = self.maintenance.list_downloads('pending')
        self.assertEqual(len(remaining), 1)

    def test_remove_by_url_pattern(self):
        """Test removing downloads by URL pattern."""
        count = self.maintenance.remove_by_url_pattern("video1")
        self.assertEqual(count, 1)

        # Verify correct item is removed
        remaining = self.maintenance.list_downloads('pending')
        self.assertEqual(len(remaining), 2)
        urls = [item['url'] for item in remaining]
        self.assertNotIn("https://example.com/video1", urls)

    def test_retry_downloads(self):
        """Test retrying downloads."""
        # Mark one as failed
        self.maintenance.db.mark_failed(1)

        count = self.maintenance.retry_downloads(download_ids=[1])
        self.assertEqual(count, 1)

        # Verify status is reset to pending
        pending = self.maintenance.list_downloads('pending')
        ids = [item['id'] for item in pending]
        self.assertIn(1, ids)

    def test_retry_failed_only(self):
        """Test retrying all failed downloads."""
        # Mark two as failed
        self.maintenance.db.mark_failed(1)
        self.maintenance.db.mark_failed(2)

        count = self.maintenance.retry_downloads(failed_only=True)
        self.assertEqual(count, 2)

        # Verify all are back to pending
        pending = self.maintenance.list_downloads('pending')
        self.assertEqual(len(pending), 3)

    def test_redownload_items(self):
        """Test marking items for redownload."""
        # Mark one as downloaded
        self.maintenance.db.mark_downloaded(1, "/some/file.mp4", "youtube")

        count = self.maintenance.redownload_items([1])
        self.assertEqual(count, 1)

        # Verify status is reset to pending
        pending = self.maintenance.list_downloads('pending')
        ids = [item['id'] for item in pending]
        self.assertIn(1, ids)

    @patch('os.path.exists')
    def test_verify_files(self, mock_exists):
        """Test file verification."""
        # Mark one as downloaded
        self.maintenance.db.mark_downloaded(1, "/some/file.mp4", "youtube")

        # Mock file doesn't exist
        mock_exists.return_value = False

        stats = self.maintenance.verify_files()

        self.assertEqual(stats['total_downloaded'], 1)
        self.assertEqual(stats['files_missing'], 1)
        self.assertEqual(stats['files_found'], 0)

    @patch('os.path.exists')
    def test_verify_files_with_fix(self, mock_exists):
        """Test file verification with auto-fix."""
        # Mark one as downloaded
        self.maintenance.db.mark_downloaded(1, "/some/file.mp4", "youtube")

        # Mock file doesn't exist
        mock_exists.return_value = False

        self.maintenance.verify_files(fix_missing=True)

        # Verify item is marked for redownload
        pending = self.maintenance.list_downloads('pending')
        ids = [item['id'] for item in pending]
        self.assertIn(1, ids)

    @patch('builtins.print')
    def test_cleanup_database_dry_run(self, mock_print):
        """Test database cleanup in dry run mode."""
        stats = self.maintenance.cleanup_database(dry_run=True)

        self.assertIn('orphaned_records', stats)
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any('DATABASE CLEANUP RESULTS' in call for call in calls))

    def test_export_data_json(self):
        """Test exporting data as JSON."""
        result = self.maintenance.export_data('json')
        data = json.loads(result)

        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['status'], 'pending')

    def test_export_data_csv(self):
        """Test exporting data as CSV."""
        result = self.maintenance.export_data('csv')

        self.assertIn('id,url,status', result)
        self.assertIn('pending', result)

    def test_find_downloads_by_url(self):
        """Test finding downloads by URL pattern."""
        matches = self.maintenance.find_downloads_by_url('video1')

        self.assertEqual(len(matches), 1)
        self.assertIn('video1', matches[0]['url'])


if __name__ == '__main__':
    unittest.main()
