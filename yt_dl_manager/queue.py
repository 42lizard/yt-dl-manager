"""Centralized queue management for yt-dl-manager."""

import logging
from .db_utils import DatabaseUtils
from .config import config


class Queue:
    """Centralized queue management class for yt-dl-manager.

    This class provides a high-level interface for all queue operations,
    consolidating functionality previously scattered across daemon and
    add_to_queue modules.
    """

    def claim_pending_for_download(self, download_id):
        """Atomically claim a pending download for processing.
        Returns True if claim succeeded, False otherwise.
        """
        return self.db.claim_pending_for_download(download_id)

    def __init__(self, db_path=None):
        """Initialize the Queue with database path.

        Args:
            db_path (str, optional): Path to the SQLite database.
                                   If None, uses DATABASE_PATH from config.
        """
        self.logger = logging.getLogger(__name__)

        if db_path is None:
            self.db_path = config['DEFAULT']['database_path']
        else:
            self.db_path = db_path
        self.db = DatabaseUtils(
            self.db_path
        )

    def add_url(self, media_url):
        """Add a media URL to the downloads queue.

        Args:
            media_url (str): The URL to add to the queue.

        Returns:
            tuple: (success, message, row_id) where success is bool,
            message is str, and row_id is int or None.

        Raises:
            ValueError: If media_url is not a valid string or is empty.
        """
        if not isinstance(media_url, str) or not media_url.strip():
            raise ValueError("media_url must be a non-empty string")

        self.logger.info("Adding URL to queue: %s", media_url)
        try:
            success, message, row_id = self.db.add_url(media_url)
            if success:
                self.logger.info(
                    "Successfully added URL to queue: %s", media_url)
            else:
                self.logger.warning(
                    "URL already exists in queue: %s", media_url)
            return success, message, row_id
        except Exception as e:
            self.logger.error(
                "Failed to add URL to queue: %s - %s", media_url, str(e))
            raise

    def get_pending(self):
        """Get all pending downloads from the queue.

        Returns:
            list: List of tuples (id, url, retries) for pending downloads.

        Raises:
            Exception: If database operation fails.
        """
        self.logger.debug("Retrieving pending downloads")
        try:
            pending = self.db.poll_pending()
            self.logger.debug("Found %d pending downloads", len(pending))
            return pending
        except Exception as e:
            self.logger.error(
                "Failed to retrieve pending downloads: %s", str(e))
            raise

    def get_in_progress(self):
        """Get all downloads currently in progress (status = 'downloading').

        Returns:
            list: List of dicts for in-progress downloads.

        Raises:
            Exception: If database operation fails.
        """
        self.logger.debug("Retrieving in-progress downloads")
        try:
            in_progress = self.db.get_downloads_by_status(
                'downloading',
                sort_by='timestamp_requested',
                sort_order='DESC'
            )
            self.logger.debug(
                "Found %d in-progress downloads", len(in_progress))
            return in_progress
        except Exception as e:
            self.logger.error(
                "Failed to retrieve in-progress downloads: %s", str(e))
            raise

    def start_download(self, download_id):
        """Mark a download as 'downloading' in the queue.

        Args:
            download_id (int): The database row ID of the download.

        Raises:
            ValueError: If download_id is not a positive integer.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        self.logger.info("Starting download with ID: %d", download_id)
        try:
            self.db.mark_downloading(download_id)
            self.logger.info(
                "Successfully marked download %d as downloading", download_id)
        except Exception as e:
            self.logger.error(
                "Failed to start download %d: %s", download_id, str(e))
            raise

    def complete_download(self, download_id, filename, extractor):
        """Mark a download as completed and store metadata.

        Args:
            download_id (int): The database row ID of the download.
            filename (str): The final filename of the downloaded file.
            extractor (str): The extractor used for the download.

        Raises:
            ValueError: If parameters are invalid.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename must be a non-empty string")
        if not isinstance(extractor, str) or not extractor.strip():
            raise ValueError("extractor must be a non-empty string")

        self.logger.info(
            "Completing download %d with filename: %s", download_id, filename)
        try:
            self.db.mark_downloaded(download_id, filename, extractor)
            self.logger.info("Successfully completed download %d", download_id)
        except Exception as e:
            self.logger.error(
                "Failed to complete download %d: %s", download_id, str(e))
            raise

    def fail_download(self, download_id):
        """Mark a download as failed in the queue.

        Args:
            download_id (int): The database row ID of the download.

        Raises:
            ValueError: If download_id is not a positive integer.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        self.logger.warning("Marking download %d as failed", download_id)
        try:
            self.db.mark_failed(download_id)
            self.logger.info(
                "Successfully marked download %d as failed", download_id)
        except Exception as e:
            self.logger.error(
                "Failed to mark download %d as failed: %s", download_id, str(e))
            raise

    def retry_download(self, download_id):
        """Prepare a download for retry by incrementing retry count and setting to pending.

        Args:
            download_id (int): The database row ID of the download.

        Raises:
            ValueError: If download_id is not a positive integer.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        self.logger.info("Preparing download %d for retry", download_id)
        try:
            self.db.increment_retries(download_id)
            self.db.set_status_to_pending(download_id)
            self.logger.info(
                "Successfully prepared download %d for retry", download_id)
        except Exception as e:
            self.logger.error(
                "Failed to prepare download %d for retry: %s", download_id, str(e))
            raise

    def increment_retries(self, download_id):
        """Increment the retry counter for a download.

        Args:
            download_id (int): The database row ID of the download.

        Raises:
            ValueError: If download_id is not a positive integer.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        self.logger.debug("Incrementing retries for download %d", download_id)
        try:
            self.db.increment_retries(download_id)
            self.logger.debug(
                "Successfully incremented retries for download %d", download_id)
        except Exception as e:
            self.logger.error("Failed to increment retries for download %d: %s",
                              download_id, str(e))
            raise

    def set_status_to_pending(self, download_id):
        """Set a download status back to 'pending' without incrementing retries.

        Args:
            download_id (int): The database row ID of the download.

        Raises:
            ValueError: If download_id is not a positive integer.
            Exception: If database operation fails.
        """
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        self.logger.debug("Setting download %d status to pending", download_id)
        try:
            self.db.set_status_to_pending(download_id)
            self.logger.debug(
                "Successfully set download %d to pending", download_id)
        except Exception as e:
            self.logger.error(
                "Failed to set download %d to pending: %s", download_id, str(e))
            raise

    def get_queue_length(self):
        """Get the total number of items in the queue.

        Returns:
            int: Total number of downloads in the database.

        Raises:
            Exception: If database operation fails.
        """
        self.logger.debug("Getting queue length")
        try:
            length = self.db.queue_length()
            self.logger.debug("Queue length: %d", length)
            return length
        except Exception as e:
            self.logger.error("Failed to get queue length: %s", str(e))
            raise

    def get_queue_status(self):
        """Get queue statistics by status.

        Returns:
            dict: Dictionary with counts for each status (pending, downloading, downloaded, failed).

        Raises:
            Exception: If database operation fails.
        """
        self.logger.debug("Getting queue status statistics")
        try:
            return self.db.get_queue_status()
        except Exception as e:
            self.logger.error("Failed to get queue status: %s", str(e))
            raise
