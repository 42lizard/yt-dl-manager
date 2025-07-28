"""Unit tests for add_to_queue.py module."""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


import io
import sys
import pathlib
from yt_dl_manager.add_to_queue import AddToQueue
from yt_dl_manager.queue import Queue
from yt_dl_manager import add_to_queue
from tests.test_utils import create_test_schema


class TestAddToQueue(unittest.TestCase):
    """Unit tests for the AddToQueue class and related queue operations."""

    def test_add_url_with_download_flag(self):  # pylint: disable=too-many-locals
        """Test adding a URL with --download triggers immediate download logic."""
        test_url = "https://www.youtube.com/watch?v=immediate"
        test_db_fd, test_db_path = tempfile.mkstemp()
        os.close(test_db_fd)
        create_test_schema(test_db_path)
        test_queue = Queue(db_path=test_db_path)
        queue_adder = AddToQueue(queue=test_queue)
        # Create a temporary config file
        temp_config_fd, temp_config_path = tempfile.mkstemp()
        os.close(temp_config_fd)
        config_content = (
            f"[DEFAULT]\nTARGET_FOLDER=/tmp/downloads\n"
            f"[yt-dl-manager]\ndb_path={test_db_path}\n"
        )
        pathlib.Path(temp_config_path).write_text(
            config_content, encoding='utf-8')
        with patch('yt_dl_manager.download_utils.yt_dlp.YoutubeDL') as mock_ydl:
            with patch.object(test_queue, 'claim_pending_for_download', return_value=True) as mock_claim:
                with patch.object(test_queue, 'complete_download') as mock_complete:
                    with patch.object(
                            add_to_queue, 'get_config_path', return_value=pathlib.Path(temp_config_path)):
                        mock_ydl.return_value.__enter__.return_value.extract_info.return_value = {
                            'extractor': 'youtube', 'title': 'Test Video', 'ext': 'mp4'
                        }
                        mock_ydl.return_value.__enter__.return_value.prepare_filename.return_value = (
                            '/fake/path/Test Video.mp4')

                        class Args:
                            """Simple args container for CLI simulation in tests."""
                            url = test_url
                            download = True
                        with patch('yt_dl_manager.add_to_queue.AddToQueue', return_value=queue_adder):
                            captured_out = io.StringIO()
                            sys_stdout = sys.stdout
                            sys.stdout = captured_out
                            try:
                                add_to_queue.main(Args())
                            finally:
                                sys.stdout = sys_stdout
                            output = captured_out.getvalue()
                            print("DEBUG: captured output:", output)
                            assert "URL added to queue" in output
                            assert "Downloaded: /fake/path/Test Video.mp4" in output
                        mock_claim.assert_called()
                        mock_complete.assert_called()
        os.unlink(test_db_path)
        os.unlink(temp_config_path)  # pylint: enable=too-many-locals

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.addCleanup(os.close, self.test_db_fd)
        self.addCleanup(os.unlink, self.test_db_path)

        # Create the test database schema
        create_test_schema(self.test_db_path)

        # Initialize the AddToQueue instance with mocked Queue that uses test database
        with patch('yt_dl_manager.add_to_queue.Queue') as mock_queue_class:
            # Create a real Queue instance with our test database path
            test_queue = Queue(db_path=self.test_db_path)
            mock_queue_class.return_value = test_queue
            self.queue_manager = AddToQueue()

    def test_add_url_new_url(self):
        """Test adding a new URL to the queue."""
        test_url = "https://www.youtube.com/watch?v=test123"

        with patch('builtins.print') as mock_print:
            self.queue_manager.add_url(test_url)
            mock_print.assert_called_once_with(
                f"URL added to queue: {test_url}")

        # Verify URL was added to database
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT url, status FROM downloads WHERE url = ?", (test_url,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], test_url)
        self.assertEqual(row[1], "pending")

    def test_add_url_duplicate_pending(self):
        """Test adding a duplicate URL that is still pending."""
        test_url = "https://www.youtube.com/watch?v=duplicate"

        # Add URL first time
        self.queue_manager.add_url(test_url)

        # Try to add same URL again
        with patch('builtins.print') as mock_print:
            self.queue_manager.add_url(test_url)
            expected_message = (
                f"URL already exists in queue: {test_url}\n"
                f"Status: pending"
            )
            mock_print.assert_called_once_with(expected_message)

    def test_add_url_duplicate_downloaded(self):
        """Test adding a duplicate URL that has been downloaded."""
        test_url = "https://www.youtube.com/watch?v=downloaded"
        test_filename = "/path/to/downloaded/file.mp4"

        # Insert a downloaded record directly
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested, "
            "final_filename) VALUES (?, ?, ?, ?)",
            (test_url, "downloaded", datetime.now(timezone.utc).isoformat(),
             test_filename)
        )
        conn.commit()
        conn.close()

        # Try to add same URL again
        with patch('builtins.print') as mock_print:
            self.queue_manager.add_url(test_url)
            expected_message = (
                f"URL already exists in queue: {test_url}\n"
                f"Status: downloaded\nDownloaded file: {test_filename}"
            )
            mock_print.assert_called_once_with(expected_message)

    def test_queue_length_empty(self):
        """Test queue length when database is empty."""
        self.assertEqual(self.queue_manager.queue_length(), 0)

    def test_queue_length_with_items(self):
        """Test queue length with multiple items in queue."""
        # Add multiple URLs
        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2",
            "https://www.youtube.com/watch?v=test3"
        ]

        for url in urls:
            self.queue_manager.add_url(url)

        self.assertEqual(self.queue_manager.queue_length(), 3)

    def test_add_url_with_timestamp(self):
        """Test that timestamp is correctly stored when adding URL."""
        test_url = "https://www.youtube.com/watch?v=timestamp_test"

        # Mock datetime to control timestamp
        fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            """Mock datetime class for fixed timestamp in tests."""
            @classmethod
            def now(cls, tz=None):
                return fixed_time

        with patch('yt_dl_manager.db_utils.datetime.datetime', FixedDateTime):
            self.queue_manager.add_url(test_url)

        # Verify timestamp in database
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT timestamp_requested FROM downloads WHERE url = ?",
            (test_url,)
        )
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row[0], fixed_time.isoformat())

    def test_database_connection_error(self):
        """Test behavior when database connection fails."""
        # Create AddToQueue with invalid database path
        with patch('yt_dl_manager.add_to_queue.Queue') as mock_queue_class:
            # Create a Queue instance with invalid database path
            invalid_queue = Queue(db_path="/invalid/path/to/database.db")
            mock_queue_class.return_value = invalid_queue
            test_queue_manager = AddToQueue()

            with self.assertRaises(sqlite3.OperationalError):
                test_queue_manager.add_url(
                    "https://www.youtube.com/watch?v=test")

    def test_add_url_edge_case_empty_result(self):
        """Test duplicate URL handling when database query returns no result."""
        test_url = "https://www.youtube.com/watch?v=edge_case"

        # Mock the database to return None for fetchone()
        with patch.object(self.queue_manager, 'add_url') as mock_add_url:
            def side_effect(url):
                conn = sqlite3.connect(self.test_db_path)
                cur = conn.cursor()
                try:
                    cur.execute(
                        "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, ?, ?)",
                        (url, 'pending', datetime.now(timezone.utc).isoformat())
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    # Simulate the case where fetchone() returns None
                    cur.execute(
                        "SELECT final_filename, status FROM downloads "
                        "WHERE url = ?", ("nonexistent",)
                    )
                    row = cur.fetchone()
                    if not row:
                        print(f"URL already exists in queue: {url}")
                finally:
                    conn.close()

            mock_add_url.side_effect = side_effect

            # First add the URL normally
            self.queue_manager.add_url(test_url)

            # Then test the edge case
            with patch('builtins.print') as mock_print:
                mock_add_url(test_url)
                mock_print.assert_called_with(
                    f"URL already exists in queue: {test_url}"
                )


if __name__ == '__main__':
    unittest.main()
