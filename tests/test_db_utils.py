"""Unit tests for db_utils.py module."""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from yt_dl_manager.db_utils import DatabaseUtils, ensure_database_schema


class TestDatabaseUtils(unittest.TestCase):
    """Test cases for DatabaseUtils class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.addCleanup(os.close, self.test_db_fd)
        self.addCleanup(os.unlink, self.test_db_path)

        # Initialize the DatabaseUtils instance
        self.db_utils = DatabaseUtils(self.test_db_path)

    def test_ensure_schema_creates_table(self):
        """Test that schema creation works properly."""
        # Verify table exists by querying it
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'")
        table_exists = cur.fetchone() is not None
        conn.close()
        self.assertTrue(table_exists)

    def test_poll_pending_empty(self):
        """Test polling when no pending downloads exist."""
        result = self.db_utils.poll_pending()
        self.assertEqual(result, [])

    def test_poll_pending_with_data(self):
        """Test polling with pending downloads."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested, retries) "
            "VALUES (?, ?, ?, ?)",
            ("https://test1.com", "pending", datetime.now(timezone.utc).isoformat(), 0)
        )
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested, retries) "
            "VALUES (?, ?, ?, ?)",
            ("https://test2.com", "downloaded", datetime.now(timezone.utc).isoformat(), 0)
        )
        conn.commit()
        conn.close()

        result = self.db_utils.poll_pending()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "https://test1.com")  # URL
        self.assertEqual(result[0][2], 0)  # retries

    def test_mark_downloading(self):
        """Test marking a download as downloading."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, ?, ?)",
            ("https://test.com", "pending", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()

        # Mark as downloading
        self.db_utils.mark_downloading(row_id)

        # Verify status changed
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM downloads WHERE id = ?", (row_id,))
        status = cur.fetchone()[0]
        conn.close()
        self.assertEqual(status, "downloading")

    def test_mark_downloaded(self):
        """Test marking a download as downloaded with metadata."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, ?, ?)",
            ("https://test.com", "downloading", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()

        # Mark as downloaded
        test_filename = "/path/to/file.mp4"
        test_extractor = "youtube"
        self.db_utils.mark_downloaded(row_id, test_filename, test_extractor)

        # Verify all fields were updated
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT status, final_filename, extractor, timestamp_downloaded "
            "FROM downloads WHERE id = ?",
            (row_id,)
        )
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row[0], "downloaded")
        self.assertEqual(row[1], test_filename)
        self.assertEqual(row[2], test_extractor)
        self.assertIsNotNone(row[3])  # timestamp should be set

    def test_mark_failed(self):
        """Test marking a download as failed."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, ?, ?)",
            ("https://test.com", "downloading", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()

        # Mark as failed
        self.db_utils.mark_failed(row_id)

        # Verify status changed
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM downloads WHERE id = ?", (row_id,))
        status = cur.fetchone()[0]
        conn.close()
        self.assertEqual(status, "failed")

    def test_increment_retries(self):
        """Test incrementing retry counter."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested, retries) "
            "VALUES (?, ?, ?, ?)",
            ("https://test.com", "pending", datetime.now(timezone.utc).isoformat(), 1)
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()

        # Increment retries
        self.db_utils.increment_retries(row_id)

        # Verify retries incremented
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT retries FROM downloads WHERE id = ?", (row_id,))
        retries = cur.fetchone()[0]
        conn.close()
        self.assertEqual(retries, 2)

    def test_set_status_to_pending(self):
        """Test setting status back to pending."""
        # Insert test data
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, ?, ?)",
            ("https://test.com", "failed", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()

        # Set to pending
        self.db_utils.set_status_to_pending(row_id)

        # Verify status changed
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT status FROM downloads WHERE id = ?", (row_id,))
        status = cur.fetchone()[0]
        conn.close()
        self.assertEqual(status, "pending")

    def test_add_url_new(self):
        """Test adding a new URL."""
        test_url = "https://www.youtube.com/watch?v=test"
        success, message = self.db_utils.add_url(test_url)

        self.assertTrue(success)
        self.assertEqual(message, f"URL added to queue: {test_url}")

        # Verify in database
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT url, status FROM downloads WHERE url = ?", (test_url,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], test_url)
        self.assertEqual(row[1], "pending")

    def test_add_url_duplicate(self):
        """Test adding a duplicate URL."""
        test_url = "https://www.youtube.com/watch?v=duplicate"

        # Add first time
        self.db_utils.add_url(test_url)

        # Add second time
        success, message = self.db_utils.add_url(test_url)

        self.assertFalse(success)
        self.assertIn("URL already exists in queue", message)
        self.assertIn(test_url, message)

    def test_queue_length_empty(self):
        """Test queue length when empty."""
        length = self.db_utils.queue_length()
        self.assertEqual(length, 0)

    def test_queue_length_with_items(self):
        """Test queue length with items."""
        # Add multiple URLs
        urls = [
            "https://test1.com",
            "https://test2.com",
            "https://test3.com"
        ]

        for url in urls:
            self.db_utils.add_url(url)

        length = self.db_utils.queue_length()
        self.assertEqual(length, 3)


class TestEnsureDatabaseSchemaBackwardCompatibility(unittest.TestCase):
    """Test cases for backward compatibility function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.addCleanup(os.close, self.test_db_fd)
        self.addCleanup(os.unlink, self.test_db_path)

    def test_ensure_database_schema_creates_table(self):
        """Test that the backward compatibility function still works."""
        ensure_database_schema(self.test_db_path)

        # Verify table exists
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'")
        table_exists = cur.fetchone() is not None
        conn.close()
        self.assertTrue(table_exists)


if __name__ == '__main__':
    unittest.main()
