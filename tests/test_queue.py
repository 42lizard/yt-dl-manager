"""Unit tests for the Queue class."""

import unittest
import tempfile
import os
from yt_dl_manager.queue import Queue


class TestQueue(unittest.TestCase):
    """Test cases for the Queue class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.queue = Queue(self.test_db_path)

    def tearDown(self):
        """Clean up after each test method."""
        # Close and remove the temporary database file
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_initialization_with_path(self):
        """Test queue initialization with explicit database path."""
        queue = Queue(self.test_db_path)
        self.assertEqual(queue.db_path, self.test_db_path)
        self.assertIsNotNone(queue.db)

    def test_initialization_from_env(self):
        """Test queue initialization using explicit db_path parameter."""
        # Create a temporary file for this test
        temp_fd, temp_path = tempfile.mkstemp(suffix='test_env.db')
        os.close(temp_fd)
        try:
            # Use explicit db_path parameter instead of config
            queue = Queue(db_path=temp_path)
            self.assertEqual(queue.db_path, temp_path)
        finally:
            os.unlink(temp_path)

    def test_initialization_default_path(self):
        """Test queue initialization with default database path from config."""
        # Test without mocking - this should use the actual config system
        queue = Queue()
        # The path should be from the config system - calculate expected path dynamically
        from platformdirs import user_data_dir  # pylint: disable=import-outside-toplevel
        from pathlib import Path  # pylint: disable=import-outside-toplevel
        data_dir = user_data_dir("yt-dl-manager", "yt-dl-manager")
        expected_path = str(Path(data_dir) / 'yt_dl_manager.db')
        self.assertEqual(queue.db_path, expected_path)

    def test_add_url_new(self):
        """Test adding a new URL to the queue."""
        test_url = "https://www.example.com/video"
        success, message = self.queue.add_url(test_url)
        self.assertTrue(success)
        self.assertIn("URL added to queue", message)
        self.assertIn(test_url, message)

    def test_add_url_duplicate(self):
        """Test adding a duplicate URL to the queue."""
        test_url = "https://www.example.com/video"
        # Add URL first time
        self.queue.add_url(test_url)
        # Try to add same URL again
        success, message = self.queue.add_url(test_url)
        self.assertFalse(success)
        self.assertIn("URL already exists", message)

    def test_add_url_invalid_empty_string(self):
        """Test adding an empty string URL raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.add_url("")
        self.assertIn("must be a non-empty string", str(context.exception))

    def test_add_url_invalid_whitespace_only(self):
        """Test adding a whitespace-only URL raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.add_url("   ")
        self.assertIn("must be a non-empty string", str(context.exception))

    def test_add_url_invalid_non_string(self):
        """Test adding a non-string URL raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.add_url(123)
        self.assertIn("must be a non-empty string", str(context.exception))

    def test_get_pending_empty(self):
        """Test getting pending downloads from empty queue."""
        pending = self.queue.get_pending()
        self.assertEqual(pending, [])

    def test_get_pending_with_data(self):
        """Test getting pending downloads with data in queue."""
        test_url = "https://www.example.com/video"
        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0][1], test_url)  # URL is second element
        self.assertEqual(pending[0][2], 0)  # retries is third element

    def test_start_download_invalid_id(self):
        """Test starting download with invalid ID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.start_download(0)
        self.assertIn("must be a positive integer", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.queue.start_download(-1)
        self.assertIn("must be a positive integer", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.queue.start_download("invalid")
        self.assertIn("must be a positive integer", str(context.exception))

    def test_complete_download_invalid_parameters(self):
        """Test completing download with invalid parameters raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.complete_download(0, "test.mp4", "youtube")
        self.assertIn("must be a positive integer", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.queue.complete_download(1, "", "youtube")
        self.assertIn("must be a non-empty string", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.queue.complete_download(1, "test.mp4", "")
        self.assertIn("must be a non-empty string", str(context.exception))

    def test_fail_download_invalid_id(self):
        """Test failing download with invalid ID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.fail_download(0)
        self.assertIn("must be a positive integer", str(context.exception))

    def test_retry_download_invalid_id(self):
        """Test retrying download with invalid ID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.retry_download(-1)
        self.assertIn("must be a positive integer", str(context.exception))

    def test_increment_retries_invalid_id(self):
        """Test incrementing retries with invalid ID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.queue.increment_retries("invalid")
        self.assertIn("must be a positive integer", str(context.exception))

    def test_start_download(self):
        """Test marking a download as started."""
        test_url = "https://www.example.com/video"
        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        download_id = pending[0][0]

        self.queue.start_download(download_id)
        # After marking as downloading, it should not appear in pending
        pending_after = self.queue.get_pending()
        self.assertEqual(len(pending_after), 0)

    def test_complete_download(self):
        """Test marking a download as completed."""
        test_url = "https://www.example.com/video"
        test_filename = "/path/to/video.mp4"
        test_extractor = "youtube"

        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        download_id = pending[0][0]

        self.queue.complete_download(download_id, test_filename, test_extractor)
        # After completion, should not appear in pending
        pending_after = self.queue.get_pending()
        self.assertEqual(len(pending_after), 0)

    def test_fail_download(self):
        """Test marking a download as failed."""
        test_url = "https://www.example.com/video"
        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        download_id = pending[0][0]

        self.queue.fail_download(download_id)
        # After marking as failed, should not appear in pending
        pending_after = self.queue.get_pending()
        self.assertEqual(len(pending_after), 0)

    def test_retry_download(self):
        """Test preparing a download for retry."""
        test_url = "https://www.example.com/video"
        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        download_id = pending[0][0]

        # Mark as downloading first
        self.queue.start_download(download_id)
        self.assertEqual(len(self.queue.get_pending()), 0)

        # Now retry
        self.queue.retry_download(download_id)
        # Should appear in pending again with incremented retries
        pending_after = self.queue.get_pending()
        self.assertEqual(len(pending_after), 1)
        self.assertEqual(pending_after[0][2], 1)  # retries should be 1

    def test_increment_retries(self):
        """Test incrementing retry counter."""
        test_url = "https://www.example.com/video"
        self.queue.add_url(test_url)
        pending = self.queue.get_pending()
        download_id = pending[0][0]

        self.queue.increment_retries(download_id)
        # Check retries were incremented
        pending_after = self.queue.get_pending()
        self.assertEqual(pending_after[0][2], 1)  # retries should be 1

    def test_get_queue_length_empty(self):
        """Test getting queue length when empty."""
        length = self.queue.get_queue_length()
        self.assertEqual(length, 0)

    def test_get_queue_length_with_items(self):
        """Test getting queue length with items."""
        self.queue.add_url("https://www.example.com/video1")
        self.queue.add_url("https://www.example.com/video2")
        length = self.queue.get_queue_length()
        self.assertEqual(length, 2)

    def test_get_queue_status_empty(self):
        """Test getting queue status when empty."""
        status = self.queue.get_queue_status()
        expected = {
            'pending': 0,
            'downloading': 0,
            'downloaded': 0,
            'failed': 0
        }
        self.assertEqual(status, expected)

    def test_get_queue_status_with_items(self):
        """Test getting queue status with various items."""
        # Add multiple URLs and set different statuses
        self.queue.add_url("https://www.example.com/video1")
        self.queue.add_url("https://www.example.com/video2")
        self.queue.add_url("https://www.example.com/video3")

        pending = self.queue.get_pending()
        # Mark one as downloading
        self.queue.start_download(pending[0][0])
        # Mark one as completed
        self.queue.complete_download(pending[1][0], "test.mp4", "youtube")
        # Mark one as failed
        self.queue.fail_download(pending[2][0])

        status = self.queue.get_queue_status()
        self.assertEqual(status['downloading'], 1)
        self.assertEqual(status['downloaded'], 1)
        self.assertEqual(status['failed'], 1)
        self.assertEqual(status['pending'], 0)


if __name__ == '__main__':
    unittest.main()
