"""Database utility functions and schema management for yt-dl-manager."""

import sqlite3
import datetime
import os
import json
import csv
import io
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

    def _build_in_clause_placeholders(self, count):
        """Build a safe IN clause with the specified number of placeholders.

        Args:
            count (int): Number of placeholders needed.

        Returns:
            str: Safe placeholder string like "?,?,?"
        """
        return ','.join('?' * count)

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
        self._ensure_schema()

    def _ensure_schema(self):
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
            # Edge case: IntegrityError but no row found - should not normally happen
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

    def get_downloads_by_status(self, status, limit=None, sort_by='timestamp_requested',
                                order='DESC', **filters):
        """Get downloads filtered by status with optional filters.

        Args:
            status (str): Download status to filter by.
            limit (int, optional): Maximum number of results.
            sort_by (str): Field to sort by (timestamp_requested, retries, url, id).
            order (str): Sort order (ASC, DESC).
            **filters: Additional filters (retry_count, extractor).

        Returns:
            list: List of download records as dictionaries.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cur = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM downloads WHERE status = ?"
        params = [status]

        if 'retry_count' in filters and filters['retry_count'] is not None:
            query += " AND retries = ?"
            params.append(filters['retry_count'])

        if 'extractor' in filters and filters['extractor']:
            query += " AND extractor = ?"
            params.append(filters['extractor'])

        # Validate sort field using safe mapping
        valid_sort_fields = {
            'timestamp_requested': 'timestamp_requested',
            'retries': 'retries',
            'url': 'url',
            'id': 'id',
            'timestamp_downloaded': 'timestamp_downloaded',
            'extractor': 'extractor'
        }
        safe_sort_by = valid_sort_fields.get(sort_by, 'timestamp_requested')

        # Validate order using safe mapping
        valid_orders = {'ASC': 'ASC', 'DESC': 'DESC'}
        safe_order = valid_orders.get(order.upper(), 'DESC')

        query += f" ORDER BY {safe_sort_by} {safe_order}"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        # Convert to list of dictionaries
        return [dict(row) for row in rows]

    def get_downloads_missing_files(self):
        """Get downloaded items where the file no longer exists.

        Returns:
            list: List of download records with missing files.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM downloads 
            WHERE status = ? AND final_filename IS NOT NULL
        """, (DownloadStatus.DOWNLOADED.value,))

        rows = cur.fetchall()
        conn.close()

        missing_files = []
        for row in rows:
            if not os.path.exists(row['final_filename']):
                missing_files.append(dict(row))

        return missing_files

    def remove_downloads_by_status(self, status, older_than_days=None, dry_run=False):
        """Remove downloads by status with optional age filter.

        Args:
            status (str): Status of downloads to remove.
            older_than_days (int, optional): Only remove items older than this many days.
            dry_run (bool): If True, return count without removing.

        Returns:
            int: Number of items that would be/were removed.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        query = "SELECT COUNT(*) FROM downloads WHERE status = ?"
        params = [status]

        if older_than_days:
            cutoff_date = (datetime.datetime.now() -
                           datetime.timedelta(days=older_than_days)).isoformat()
            query += " AND timestamp_requested < ?"
            params.append(cutoff_date)

        cur.execute(query, params)
        count = cur.fetchone()[0]

        if not dry_run and count > 0:
            delete_query = query.replace("SELECT COUNT(*)", "DELETE")
            cur.execute(delete_query, params)
            conn.commit()

        conn.close()
        return count

    def remove_downloads_by_ids(self, download_ids, dry_run=False):
        """Remove downloads by their database IDs.

        Args:
            download_ids (list): List of database IDs to remove.
            dry_run (bool): If True, return count without removing.

        Returns:
            int: Number of items that would be/were removed.
        """
        if not download_ids:
            return 0

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        placeholders = self._build_in_clause_placeholders(len(download_ids))

        # Use string concatenation instead of f-string for SQL
        query = "SELECT COUNT(*) FROM downloads WHERE id IN (" + \
            placeholders + ")"

        cur.execute(query, download_ids)
        count = cur.fetchone()[0]

        if not dry_run and count > 0:
            delete_query = "DELETE FROM downloads WHERE id IN (" + \
                placeholders + ")"
            cur.execute(delete_query, download_ids)
            conn.commit()

        conn.close()
        return count

    def remove_downloads_by_url_pattern(self, url_pattern, dry_run=False):
        """Remove downloads by URL pattern matching.

        Args:
            url_pattern (str): URL pattern to match (supports LIKE syntax).
            dry_run (bool): If True, return count without removing.

        Returns:
            int: Number of items that would be/were removed.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        query = "SELECT COUNT(*) FROM downloads WHERE url LIKE ?"
        cur.execute(query, [f"%{url_pattern}%"])
        count = cur.fetchone()[0]

        if not dry_run and count > 0:
            delete_query = "DELETE FROM downloads WHERE url LIKE ?"
            cur.execute(delete_query, [f"%{url_pattern}%"])
            conn.commit()

        conn.close()
        return count

    def reset_downloads_to_pending(self, download_ids, reset_retries=True):
        """Reset downloads back to pending status.

        Args:
            download_ids (list): List of database IDs to reset.
            reset_retries (bool): Whether to reset retry count to 0.

        Returns:
            int: Number of downloads reset.
        """
        if not download_ids:
            return 0

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        placeholders = self._build_in_clause_placeholders(len(download_ids))

        if reset_retries:
            query = ("UPDATE downloads "
                     "SET status = ?, retries = 0, "
                     "timestamp_downloaded = NULL, final_filename = NULL "
                     "WHERE id IN (" + placeholders + ")")
            params = [DownloadStatus.PENDING.value] + download_ids
        else:
            query = ("UPDATE downloads "
                     "SET status = ?, timestamp_downloaded = NULL, final_filename = NULL "
                     "WHERE id IN (" + placeholders + ")")
            params = [DownloadStatus.PENDING.value] + download_ids

        cur.execute(query, params)
        updated = cur.rowcount
        conn.commit()
        conn.close()
        return updated

    def find_downloads_by_url_pattern(self, url_pattern):
        """Find downloads matching a URL pattern.

        Args:
            url_pattern (str): URL pattern to search for.

        Returns:
            list: List of matching download records.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM downloads WHERE url LIKE ?",
                    [f"%{url_pattern}%"])
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def cleanup_database(self, dry_run=False):
        """Perform database maintenance operations.

        Args:
            dry_run (bool): If True, return statistics without making changes.

        Returns:
            dict: Statistics about cleanup operations.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        stats = {
            'orphaned_records': 0,
            'space_saved_kb': 0,
            'vacuum_performed': False
        }

        # Check for orphaned records (basic integrity check)
        cur.execute(
            "SELECT COUNT(*) FROM downloads WHERE url IS NULL OR url = ''")
        orphaned_count = cur.fetchone()[0]
        stats['orphaned_records'] = orphaned_count

        if not dry_run:
            # Remove orphaned records
            if orphaned_count > 0:
                cur.execute(
                    "DELETE FROM downloads WHERE url IS NULL OR url = ''")
                conn.commit()

            # Get database size before vacuum
            cur.execute("PRAGMA page_count")
            pages_before = cur.fetchone()[0]
            cur.execute("PRAGMA page_size")
            page_size = cur.fetchone()[0]
            size_before = pages_before * page_size

            # Vacuum database
            cur.execute("VACUUM")

            # Get database size after vacuum
            cur.execute("PRAGMA page_count")
            pages_after = cur.fetchone()[0]
            size_after = pages_after * page_size

            stats['space_saved_kb'] = (size_before - size_after) // 1024
            stats['vacuum_performed'] = True

        conn.close()
        return stats

    def export_data(self, output_format='json', status_filter=None):
        """Export queue data for backup or analysis.

        Args:
            output_format (str): Export format ('json' or 'csv').
            status_filter (str, optional): Only export downloads with this status.

        Returns:
            str: Formatted data string.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if status_filter:
            cur.execute("SELECT * FROM downloads WHERE status = ? ORDER BY id",
                        [status_filter])
        else:
            cur.execute("SELECT * FROM downloads ORDER BY id")

        rows = cur.fetchall()
        conn.close()

        data = [dict(row) for row in rows]

        if output_format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)

        if output_format.lower() == 'csv':
            if not data:
                return ""

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        raise ValueError("output_format must be 'json' or 'csv'")

    def get_storage_usage_summary(self):
        """Get storage usage summary for downloaded files.

        Returns:
            dict: Storage statistics.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT final_filename FROM downloads 
            WHERE status = ? AND final_filename IS NOT NULL
        """, (DownloadStatus.DOWNLOADED.value,))

        rows = cur.fetchall()
        conn.close()

        total_size = 0
        files_found = 0
        files_missing = 0

        for row in rows:
            filename = row['final_filename']
            if os.path.exists(filename):
                try:
                    total_size += os.path.getsize(filename)
                    files_found += 1
                except OSError:
                    files_missing += 1
            else:
                files_missing += 1

        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'files_found': files_found,
            'files_missing': files_missing,
            'total_files': files_found + files_missing
        }
