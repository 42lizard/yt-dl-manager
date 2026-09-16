"""SQLite persistence for Downloads."""

import re
import sqlite3
import datetime
import json
import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional
from .config import config


class DownloadStatus(StrEnum):
    """A Download's persisted lifecycle state."""
    PENDING = 'pending'
    DOWNLOADING = 'downloading'
    DOWNLOADED = 'downloaded'
    FAILED = 'failed'


class DownloadSort(StrEnum):
    """Domain-level ordering choices for Download reads."""
    REQUESTED = 'requested'
    COMPLETED = 'completed'
    RETRIES = 'retries'
    URL = 'url'
    ID = 'id'
    EXTRACTOR = 'extractor'


@dataclass(frozen=True)
# The persisted Download has eight domain facts by design.
# pylint: disable=too-many-instance-attributes
class Download:
    """A Download returned through the persistence interface."""

    id: int
    url: str
    status: DownloadStatus
    requested_at: Optional[datetime.datetime]
    completed_at: Optional[datetime.datetime]
    filename: Optional[Path]
    extractor: Optional[str]
    retries: int


@dataclass(frozen=True)
class DownloadQuery:
    """Domain-level choices for selecting Downloads."""

    status: DownloadStatus
    limit: Optional[int] = None
    sort: DownloadSort = DownloadSort.REQUESTED
    descending: bool = True
    retries: Optional[int] = None
    extractor: Optional[str] = None


def _is_valid_url(url):
    """Validate that the URL is a proper http(s) URL."""
    url_pattern = re.compile(r"^https?://[^\s]+$")
    return isinstance(url, str) and url_pattern.match(url.strip())


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


class DownloadStore:
    """Persist Downloads in SQLite."""

    @staticmethod
    def _to_download(row):
        """Translate a SQLite row into a Download."""
        if row is None:
            return None
        requested = row['timestamp_requested']
        completed = row['timestamp_downloaded']
        filename = row['final_filename']
        return Download(
            id=row['id'],
            url=row['url'],
            status=DownloadStatus(row['status']),
            requested_at=(
                datetime.datetime.fromisoformat(requested)
                if requested else None
            ),
            completed_at=(
                datetime.datetime.fromisoformat(completed)
                if completed else None
            ),
            filename=Path(filename) if filename else None,
            extractor=row['extractor'],
            retries=row['retries'],
        )

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
        Return whether it was claimed and its current record when present.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ? "
            "WHERE id = ? AND status = ? "
            "RETURNING *",
            (DownloadStatus.DOWNLOADING.value,
             row_id,
             DownloadStatus.PENDING.value))
        row = cur.fetchone()
        claimed = row is not None
        if row is None:
            cur.execute(
                "SELECT * FROM downloads WHERE id = ?",
                (row_id,),
            )
            row = cur.fetchone()
        conn.commit()
        conn.close()
        return claimed, self._to_download(row)

    def record_failed_attempt(self, row_id, max_attempts):
        """Atomically increment attempts and schedule retry or mark failed."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads "
            "SET retries = retries + 1, status = CASE "
            "WHEN retries + 1 >= ? THEN ? ELSE ? END "
            "WHERE id = ? AND status = ? "
            "RETURNING *",
            (
                max_attempts,
                DownloadStatus.FAILED.value,
                DownloadStatus.PENDING.value,
                row_id,
                DownloadStatus.DOWNLOADING.value,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return self._to_download(row)

    def __init__(self, db_path=None):
        """Initialize the Download store with a database path.
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

    def mark_downloaded(self, row_id, filename, extractor):
        """Mark a download as 'downloaded' and store metadata in the database.
        Args:
            row_id (int): The database row ID of the download.
            filename (str): The final filename of the downloaded file.
            extractor (str): The extractor used for the download.
        """
        # Store the full filename path for file existence checks
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = ?, "
            "timestamp_downloaded = ?, "
            "final_filename = ?, extractor = ? WHERE id = ?",
            (DownloadStatus.DOWNLOADED.value,
             datetime.datetime.now(datetime.timezone.utc).isoformat(),
             filename, extractor, row_id)
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
        # Security: Validate URL before inserting
        if not _is_valid_url(media_url):
            return False, "Invalid URL. Only http(s) URLs are allowed.", None

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

    def status_counts(self):
        """Count Downloads in each lifecycle state.

        Returns:
            dict: Counts keyed by DownloadStatus.

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
            counts = {
                DownloadStatus.PENDING: 0,
                DownloadStatus.DOWNLOADING: 0,
                DownloadStatus.DOWNLOADED: 0,
                DownloadStatus.FAILED: 0,
            }

            # Update with actual counts
            for status, count in results:
                parsed_status = DownloadStatus(status)
                if parsed_status in counts:
                    counts[parsed_status] = count

            return counts
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(
                f"Failed to get queue status: {e}") from e

    def list_downloads(self, query):
        """Read Downloads using domain-level selection choices.

        Args:
            query (DownloadQuery): Domain-level selection choices.

        Returns:
            list: Immutable Download values.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cur = conn.cursor()

        statement = "SELECT * FROM downloads WHERE status = ?"
        params = [query.status.value]

        if query.retries is not None:
            statement += " AND retries = ?"
            params.append(query.retries)

        if query.extractor:
            statement += " AND extractor = ?"
            params.append(query.extractor)

        # Validate sort field using safe mapping
        valid_sort_fields = {
            DownloadSort.REQUESTED: 'timestamp_requested',
            DownloadSort.COMPLETED: 'timestamp_downloaded',
            DownloadSort.RETRIES: 'retries',
            DownloadSort.URL: 'url',
            DownloadSort.ID: 'id',
            DownloadSort.EXTRACTOR: 'extractor',
        }
        statement += (
            f" ORDER BY {valid_sort_fields[query.sort]} "
            f"{'DESC' if query.descending else 'ASC'}"
        )

        if query.limit:
            statement += " LIMIT ?"
            params.append(query.limit)

        cur.execute(statement, params)
        rows = cur.fetchall()
        conn.close()

        return [self._to_download(row) for row in rows]

    def remove_by_status(self, status, older_than_days=None, dry_run=False):
        """Remove downloads by status with optional age filter.

        Args:
            status (DownloadStatus): Status of Downloads to remove.
            older_than_days (int, optional): Only remove items older than this many days.
            dry_run (bool): If True, return count without removing.

        Returns:
            int: Number of items that would be/were removed.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        query = "SELECT COUNT(*) FROM downloads WHERE status = ?"
        params = [status.value]

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

    def remove(self, download_ids, dry_run=False):
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

    def remove_by_url(self, url_pattern, dry_run=False):
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

    def reset(self, download_ids, reset_retries=True):
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

    def find_by_url(self, url_pattern):
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

        return [self._to_download(row) for row in rows]

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
            status = DownloadStatus(status_filter)
            cur.execute("SELECT * FROM downloads WHERE status = ? ORDER BY id",
                        [status.value])
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
