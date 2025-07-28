"""Database utility functions and schema management for yt-dl-manager."""

import sqlite3
import datetime
from enum import Enum
from .config import config


class DownloadStatus(Enum):
    """Enumeration for download status values."""
    PENDING = 'pending'
    DOWNLOADING = 'downloading'
    DOWNLOADED = 'downloaded'
    FAILED = 'failed'


def ensure_database_schema(db_path):
    """Create or verify the downloads table schema.
    Args:
        db_path (str): Path to the SQLite database file.
    Raises:
        sqlite3.OperationalError: If database connection fails during setup.
    Note:
        This function is kept for backward compatibility.
        New code should use DatabaseUtils class instead.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(DOWNLOADS_TABLE_SCHEMA)
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # If we can't connect to the database during initialization,
        # we'll let the error happen later during actual operations
        pass


# Database schema definition
DOWNLOADS_TABLE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    status TEXT,
    timestamp_requested DATETIME,
    timestamp_downloaded DATETIME,
    final_filename TEXT,
    extractor TEXT,
    retries INTEGER DEFAULT 0
);
'''


class DatabaseUtils:
    """Centralized database operations for yt-dl-manager."""

    def claim_pending_for_download(self, row_id):
        """Atomically claim a pending download for processing.
        Sets status to 'downloading' only if current status is 'pending'.
        Returns True if claim succeeded, False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ? "
            "WHERE id = ? AND status = ?",
            (DownloadStatus.DOWNLOADING.value,
             row_id,
             DownloadStatus.PENDING.value))
        updated = cur.rowcount
        conn.commit()
        conn.close()
        return updated == 1

    def __init__(self, db_path=None):
        """Initialize DatabaseUtils with database path.
        Args:
            db_path (str, optional): Path to the SQLite database file. Defaults to None.
        """
        self.db_path = db_path if db_path else config['DEFAULT']['database_path']
        self.ensure_schema()

    def ensure_schema(self):
        """Create or verify the downloads table schema.
        Raises:
            sqlite3.OperationalError: If database connection fails during setup.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(DOWNLOADS_TABLE_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass

    def poll_pending(self):
        """Fetch all pending downloads from the database.
        Returns:
            list: List of tuples (id, url, retries) for pending downloads.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, url, retries FROM downloads WHERE status = ?",
            (DownloadStatus.PENDING.value,)
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def mark_downloading(self, row_id):
        """Mark a download as 'downloading' in the database.
        Args:
            row_id (int): The database row ID of the download.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ? WHERE id = ?",
            (DownloadStatus.DOWNLOADING.value, row_id)
        )
        conn.commit()
        conn.close()

    def mark_downloaded(self, row_id, filename, extractor):
        """Mark a download as 'downloaded' and store metadata in the database.
        Args:
            row_id (int): The database row ID of the download.
            filename (str): The final filename of the downloaded file.
            extractor (str): The extractor used for the download.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ?, "
            "timestamp_downloaded = datetime('now'), "
            "final_filename = ?, extractor = ? WHERE id = ?",
            (DownloadStatus.DOWNLOADED.value, filename, extractor, row_id)
        )
        conn.commit()
        conn.close()

    def mark_failed(self, row_id):
        """Mark a download as 'failed' in the database.
        Args:
            row_id (int): The database row ID of the download.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ? WHERE id = ?",
            (DownloadStatus.FAILED.value, row_id)
        )
        conn.commit()
        conn.close()

    def increment_retries(self, row_id):
        """Increment the retry counter for a download in the database.
        Args:
            row_id (int): The database row ID of the download.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET retries = retries + 1 WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()

    def set_status_to_pending(self, row_id):
        """Set a download status back to 'pending' for retry.
        Args:
            row_id (int): The database row ID of the download.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ? WHERE id = ?",
            (DownloadStatus.PENDING.value, row_id)
        )
        conn.commit()
        conn.close()

    def add_url(self, media_url):
        """Add a media URL to the downloads queue.
        Args:
            media_url (str): The URL to add to the queue.
        Returns:
            tuple: (success, message, row_id) where success is bool,
            message is str, and row_id is int or None.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO downloads (url, status, timestamp_requested) "
                "VALUES (?, ?, ?)",
                (
                    media_url,
                    DownloadStatus.PENDING.value,
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                ),
            )
            conn.commit()
            row_id = cur.lastrowid
            return True, f"URL added to queue: {media_url}", row_id
        except sqlite3.IntegrityError:
            cur.execute(
                "SELECT id, final_filename, status FROM downloads WHERE url = ?", (media_url,))
            row = cur.fetchone()
            if row:
                row_id, filename, status = row
                if filename:
                    message = (
                        f"URL already exists in queue: {media_url}\n"
                        f"Status: {status}\nDownloaded file: {filename}"
                    )
                else:
                    message = f"URL already exists in queue: {media_url}\nStatus: {status}"
                return False, message, row_id
            message = f"URL already exists in queue: {media_url}"
            return False, message, None
        finally:
            conn.close()

    def queue_length(self):
        """Return the number of items in the queue.
        Returns:
            int: Total number of downloads in the database.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM downloads")
        count = cur.fetchone()[0]
        conn.close()
        return count

    def get_queue_status(self):
        """Get queue statistics by status.

        Returns:
            dict: Dictionary with counts for each status (pending, downloading, downloaded, failed).

        Raises:
            sqlite3.OperationalError: If database connection or query fails.
        """
        try:
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
                DownloadStatus.PENDING.value: 0,
                DownloadStatus.DOWNLOADING.value: 0,
                DownloadStatus.DOWNLOADED.value: 0,
                DownloadStatus.FAILED.value: 0
            }

            # Update with actual counts
            for status, count in results:
                if status in status_counts:
                    status_counts[status] = count

            return status_counts
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(
                f"Failed to get queue status: {e}") from e
