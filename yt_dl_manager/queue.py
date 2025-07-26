"""Centralized queue management for yt-dl-manager."""

import os
import sqlite3
from dotenv import load_dotenv
from .db_utils import DatabaseUtils

load_dotenv()

class Queue:
    """Centralized queue management class for yt-dl-manager.

    This class provides a high-level interface for all queue operations,
    consolidating functionality previously scattered across daemon and
    add_to_queue modules.
    """

    def __init__(self, db_path=None):
        """Initialize the Queue with database path.

        Args:
            db_path (str, optional): Path to the SQLite database.
                                   If None, uses DATABASE_PATH from environment.
        """
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')
        self.db_path = db_path
        self.db = DatabaseUtils(self.db_path)

    def add_url(self, media_url):
        """Add a media URL to the downloads queue.

        Args:
            media_url (str): The URL to add to the queue.

        Returns:
            tuple: (success, message) where success is bool and message is str.
        """
        return self.db.add_url(media_url)

    def get_pending(self):
        """Get all pending downloads from the queue.

        Returns:
            list: List of tuples (id, url, retries) for pending downloads.
        """
        return self.db.poll_pending()

    def start_download(self, download_id):
        """Mark a download as 'downloading' in the queue.

        Args:
            download_id (int): The database row ID of the download.
        """
        self.db.mark_downloading(download_id)

    def complete_download(self, download_id, filename, extractor):
        """Mark a download as completed and store metadata.

        Args:
            download_id (int): The database row ID of the download.
            filename (str): The final filename of the downloaded file.
            extractor (str): The extractor used for the download.
        """
        self.db.mark_downloaded(download_id, filename, extractor)

    def fail_download(self, download_id):
        """Mark a download as failed in the queue.

        Args:
            download_id (int): The database row ID of the download.
        """
        self.db.mark_failed(download_id)

    def retry_download(self, download_id):
        """Prepare a download for retry by incrementing retry count and setting to pending.

        Args:
            download_id (int): The database row ID of the download.
        """
        self.db.increment_retries(download_id)
        self.db.set_status_to_pending(download_id)

    def increment_retries(self, download_id):
        """Increment the retry counter for a download.

        Args:
            download_id (int): The database row ID of the download.
        """
        self.db.increment_retries(download_id)

    def set_status_to_pending(self, download_id):
        """Set a download status back to 'pending' without incrementing retries.

        Args:
            download_id (int): The database row ID of the download.
        """
        self.db.set_status_to_pending(download_id)

    def get_queue_length(self):
        """Get the total number of items in the queue.

        Returns:
            int: Total number of downloads in the database.
        """
        return self.db.queue_length()

    def get_queue_status(self):
        """Get queue statistics by status.

        Returns:
            dict: Dictionary with counts for each status (pending, downloading, downloaded, failed).
        """
        # This is a new feature that provides queue statistics
        # We'll implement it using existing database infrastructure
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*)
            FROM downloads
            GROUP BY status
        """)
        results = cur.fetchall()
        conn.close()

        # Initialize all possible statuses with 0
        status_counts = {
            'pending': 0,
            'downloading': 0,
            'downloaded': 0,
            'failed': 0
        }

        # Update with actual counts
        for status, count in results:
            if status in status_counts:
                status_counts[status] = count

        return status_counts
