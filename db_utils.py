"""Database utility functions for yt-dl-manager."""

import sqlite3
from datetime import datetime

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

    def __init__(self, db_path):
        """Initialize DatabaseUtils with database path.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
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
            # If we can't connect to the database during initialization,
            # we'll let the error happen later during actual operations
            pass

    def poll_pending(self):
        """Fetch all pending downloads from the database.

        Returns:
            list: List of tuples (id, url, retries) for pending downloads.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, url, retries FROM downloads WHERE status = 'pending'")
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
            "UPDATE downloads SET status = 'downloading' WHERE id = ?", (row_id,))
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
            "UPDATE downloads SET status = 'downloaded', "
            "timestamp_downloaded = datetime('now'), "
            "final_filename = ?, extractor = ? WHERE id = ?",
            (filename, extractor, row_id)
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
            "UPDATE downloads SET status = 'failed' WHERE id = ?", (row_id,))
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
            "UPDATE downloads SET status = 'pending' WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()

    def add_url(self, media_url):
        """Add a media URL to the downloads queue.

        Args:
            media_url (str): The URL to add to the queue.

        Returns:
            tuple: (success, message) where success is bool and message is str.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, 'pending', ?)",
                (media_url, datetime.utcnow().isoformat())
            )
            conn.commit()
            return True, f"URL added to queue: {media_url}"
        except sqlite3.IntegrityError:
            cur.execute(
                "SELECT final_filename, status FROM downloads WHERE url = ?", (media_url,))
            row = cur.fetchone()
            if row:
                filename, status = row
                if filename:
                    message = (
                        f"URL already exists in queue: {media_url}\n"
                        f"Status: {status}\nDownloaded file: {filename}"
                    )
                else:
                    message = f"URL already exists in queue: {media_url}\nStatus: {status}"
            else:
                message = f"URL already exists in queue: {media_url}"
            return False, message
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
