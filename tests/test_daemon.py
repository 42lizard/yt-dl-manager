"""Unit tests for daemon.py module."""

import os
import sqlite3
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import yt_dlp

from yt_dl_manager.daemon import YTDLManagerDaemon, MAX_RETRIES
from tests.test_utils import create_test_schema


class TestYTDLManagerDaemon(unittest.TestCase):
    """Test cases for YTDLManagerDaemon class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.addCleanup(os.close, self.test_db_fd)
        self.addCleanup(os.unlink, self.test_db_path)

        # Create the test database schema
        create_test_schema(self.test_db_path)

        # Create a temporary download directory
        self.download_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.download_dir)

        # Initialize the YTDLManagerDaemon instance
        self.daemon = YTDLManagerDaemon(db_path=self.test_db_path)

        # Set download and final directories for testing purposes
        self.daemon.download_dir = self.download_dir
        self.daemon.final_dir = self.download_dir
        self.daemon.work_dir = self.download_dir

    def _insert_test_download(self, url, status='pending', retries=0):
        """Helper method to insert a test download record."""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested, retries) "
            "VALUES (?, ?, ?, ?)",
            (url, status, datetime.now(timezone.utc).isoformat(), retries)
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id

    def test_poll_pending_empty_database(self):
        """Test polling when database is empty."""
        pending = self.daemon.poll_pending()
        self.assertEqual(pending, [])

    def test_poll_pending_with_items(self):
        """Test polling with pending downloads."""
        # Insert test data
        url1 = "https://www.youtube.com/watch?v=test1"
        url2 = "https://www.youtube.com/watch?v=test2"
        url3 = "https://www.youtube.com/watch?v=test3"

        id1 = self._insert_test_download(url1, 'pending', 0)
        id2 = self._insert_test_download(url2, 'pending', 1)
        # Should not be returned
        self._insert_test_download(url3, 'downloaded', 0)

        pending = self.daemon.poll_pending()

        self.assertEqual(len(pending), 2)
        # Check that returned data matches expected format (id, url, retries)
        expected_results = {(id1, url1, 0), (id2, url2, 1)}
        actual_results = {(row[0], row[1], row[2]) for row in pending}
        self.assertEqual(actual_results, expected_results)

    def test_mark_downloading(self):
        """Test marking a download as 'downloading'."""
        row_id = self._insert_test_download(
            "https://www.youtube.com/watch?v=test"
        )

        self.daemon.mark_downloading(row_id)

        # Verify status was updated
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM downloads WHERE id = ?", (row_id,))
        status = cur.fetchone()[0]
        conn.close()

        self.assertEqual(status, 'downloading')

    def test_mark_downloaded(self):
        """Test marking a download as 'downloaded' with metadata."""
        row_id = self._insert_test_download(
            "https://www.youtube.com/watch?v=test"
        )
        test_filename = "/path/to/downloaded/file.mp4"
        test_extractor = "youtube"

        self.daemon.mark_downloaded(row_id, test_filename, test_extractor)

        # Verify database was updated correctly
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT status, final_filename, extractor, timestamp_downloaded "
            "FROM downloads WHERE id = ?",
            (row_id,)
        )
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row[0], 'downloaded')
        self.assertEqual(row[1], test_filename)
        self.assertEqual(row[2], test_extractor)
        self.assertIsNotNone(row[3])  # timestamp_downloaded should be set

    def test_mark_failed(self):
        """Test marking a download as 'failed'."""
        row_id = self._insert_test_download(
            "https://www.youtube.com/watch?v=test"
        )

        self.daemon.mark_failed(row_id)

        # Verify status was updated
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM downloads WHERE id = ?", (row_id,))
        status = cur.fetchone()[0]
        conn.close()

        self.assertEqual(status, 'failed')

    def test_increment_retries(self):
        """Test incrementing retry counter."""
        row_id = self._insert_test_download(
            "https://www.youtube.com/watch?v=test", retries=1
        )

        self.daemon.increment_retries(row_id)

        # Verify retries was incremented
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT retries FROM downloads WHERE id = ?", (row_id,))
        retries = cur.fetchone()[0]
        conn.close()

        self.assertEqual(retries, 2)

    @patch.dict(os.environ, {'TARGET_FOLDER': 'test_downloads'})
    @patch('yt_dl_manager.daemon.yt_dlp.YoutubeDL')
    def test_download_media_success(self, mock_ytdl_class):
        """Test successful media download."""
        # Setup mocks
        mock_ytdl_instance = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl_instance

        mock_info = {
            'extractor': 'youtube',
            'title': 'Test Video'
        }
        mock_ytdl_instance.extract_info.return_value = mock_info
        mock_ytdl_instance.prepare_filename.return_value = (
            '/path/to/test_video.mp4'
        )

        # Insert test download
        test_url = "https://www.youtube.com/watch?v=test"
        row_id = self._insert_test_download(test_url)

        # Test download
        with patch.object(self.daemon.logger, 'info') as mock_logger_info:
            self.daemon.download_media(row_id, test_url, 0)

            # Verify yt-dlp was called correctly
            mock_ytdl_instance.extract_info.assert_called_once_with(
                test_url, download=True
            )
            mock_ytdl_instance.prepare_filename.assert_called_once_with(mock_info)

            # Verify database was updated
            conn = sqlite3.connect(self.test_db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT status, final_filename, extractor FROM downloads "
                "WHERE id = ?",
                (row_id,)
            )
            row = cur.fetchone()
            conn.close()

            self.assertEqual(row[0], 'downloaded')
            self.assertEqual(row[1], '/path/to/test_video.mp4')
            self.assertEqual(row[2], 'youtube')

            # Verify success message was logged
            mock_logger_info.assert_any_call("Downloaded successfully: %s", '/path/to/test_video.mp4')

    @patch.dict(os.environ, {'TARGET_FOLDER': 'test_downloads'})
    @patch('yt_dl_manager.daemon.yt_dlp.YoutubeDL')
    def test_download_media_failure_with_retry(self, mock_ytdl_class):
        """Test download failure that should be retried."""
        # Setup mocks
        mock_ytdl_instance = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl_instance

        # Simulate download error
        mock_ytdl_instance.extract_info.side_effect = (
            yt_dlp.utils.DownloadError("Network error")
        )

        # Insert test download
        test_url = "https://www.youtube.com/watch?v=test"
        row_id = self._insert_test_download(test_url)

        # Test download with retry count below max
        with patch.object(self.daemon.logger, 'warning') as mock_logger_warning:
            self.daemon.download_media(row_id, test_url, 1)

            # Verify database was updated for retry
            conn = sqlite3.connect(self.test_db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT status, retries FROM downloads WHERE id = ?", (row_id,)
            )
            row = cur.fetchone()
            conn.close()

            # Should be set back to pending for retry
            self.assertEqual(row[0], 'pending')
            self.assertEqual(row[1], 1)  # Retries should be incremented

            # Verify retry message was logged
            mock_logger_warning.assert_called_with(
                "Download failed for %s, will retry (attempt %d/%d): %s", 
                test_url, 2, MAX_RETRIES, "Network error"
            )

    @patch.dict(os.environ, {'TARGET_FOLDER': 'test_downloads'})
    @patch('yt_dl_manager.daemon.yt_dlp.YoutubeDL')
    def test_download_media_failure_max_retries(self, mock_ytdl_class):
        """Test download failure after max retries."""
        # Setup mocks
        mock_ytdl_instance = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl_instance

        # Simulate download error
        mock_ytdl_instance.extract_info.side_effect = (
            yt_dlp.utils.DownloadError("Network error")
        )

        # Insert test download with max retries - 1
        test_url = "https://www.youtube.com/watch?v=test"
        row_id = self._insert_test_download(test_url, retries=MAX_RETRIES-1)

        # Test download at max retries
        with patch.object(self.daemon.logger, 'error') as mock_logger_error:
            self.daemon.download_media(row_id, test_url, MAX_RETRIES-1)

            # Verify database was updated to failed
            conn = sqlite3.connect(self.test_db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT status, retries FROM downloads WHERE id = ?", (row_id,)
            )
            row = cur.fetchone()
            conn.close()

            self.assertEqual(row[0], 'failed')
            # Retries should be incremented to max
            self.assertEqual(row[1], MAX_RETRIES)

            # Verify failure message was logged
            mock_logger_error.assert_called_with(
                "Download failed for %s after %d attempts: %s", 
                test_url, MAX_RETRIES, "Network error"
            )

    @patch('yt_dl_manager.daemon.time.sleep')
    def test_run_no_pending_downloads(self, mock_sleep):
        """Test daemon run loop with no pending downloads."""
        # Stop daemon after first iteration
        def side_effect(*_):
            self.daemon.running = False

        mock_sleep.side_effect = side_effect

        # Run daemon
        with patch.object(self.daemon.logger, 'info') as mock_logger_info, \
             patch.object(self.daemon.logger, 'debug') as mock_logger_debug:
            self.daemon.run()

            # Verify behavior
            mock_logger_info.assert_any_call(
                'Daemon started. Polling for pending downloads...'
            )
            mock_logger_debug.assert_any_call('No pending downloads.')
            mock_sleep.assert_called_once_with(10)  # POLL_INTERVAL

    @patch('yt_dl_manager.daemon.time.sleep')
    def test_run_with_pending_downloads(self, mock_sleep):
        """Test daemon run loop with pending downloads."""
        # Insert test download
        test_url = "https://www.youtube.com/watch?v=test"
        self._insert_test_download(test_url)

        # Mock download_media to avoid actual download
        with patch.object(self.daemon, 'download_media') as mock_download:
            # Stop daemon after first iteration
            def side_effect(*_):
                self.daemon.running = False

            mock_sleep.side_effect = side_effect

            # Run daemon
            with patch.object(self.daemon.logger, 'info') as mock_logger_info:
                self.daemon.run()

                # Verify behavior
                mock_logger_info.assert_any_call(
                    'Daemon started. Polling for pending downloads...'
                )
                mock_logger_info.assert_any_call('Found %d pending downloads.', 1)
                mock_download.assert_called_once()
                mock_sleep.assert_called_once_with(10)

    @patch('yt_dl_manager.daemon.time.sleep')
    def test_run_keyboard_interrupt(self, mock_sleep):
        """Test daemon graceful shutdown on KeyboardInterrupt."""
        # Simulate KeyboardInterrupt on sleep
        mock_sleep.side_effect = KeyboardInterrupt()

        # Run daemon
        with patch.object(self.daemon.logger, 'info') as mock_logger_info:
            self.daemon.run()

            # Verify graceful shutdown message
            mock_logger_info.assert_any_call(
                'Daemon started. Polling for pending downloads...'
            )
            mock_logger_info.assert_any_call('Daemon stopped.')

    def test_ytdl_options_configuration(self):
        """Test that yt-dlp options are configured correctly."""
        test_url = "https://www.youtube.com/watch?v=test"
        row_id = self._insert_test_download(test_url)

        with patch.dict(os.environ, {'TARGET_FOLDER': 'custom_downloads'}):
            with patch('yt_dl_manager.daemon.yt_dlp.YoutubeDL') as mock_ytdl_class:
                mock_ytdl_instance = MagicMock()
                mock_ytdl_class.return_value.__enter__.return_value = (
                    mock_ytdl_instance
                )

                mock_info = {'extractor': 'youtube', 'title': 'Test'}
                mock_ytdl_instance.extract_info.return_value = mock_info
                mock_ytdl_instance.prepare_filename.return_value = (
                    '/path/test.mp4'
                )

                # Test download
                self.daemon.download_media(row_id, test_url, 0)

                # Verify YoutubeDL was called with correct options
                expected_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': (
                        'custom_downloads/%(extractor)s/%(title)s.%(ext)s'
                    ),
                    'writemetadata': True,
                    'embedmetadata': True,
                    'quiet': True,
                }
                mock_ytdl_class.assert_called_once_with(expected_opts)


if __name__ == '__main__':
    unittest.main()
