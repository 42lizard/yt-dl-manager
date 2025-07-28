"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import logging
import time
from .queue import Queue
from .config import get_config_path
from .download_utils import download_media

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds
MAX_RETRIES = 3


class YTDLManagerDaemon:
    """Daemon for managing yt-dlp downloads from an SQLite queue."""

    def __init__(self):
        """Initialize the daemon with the database path."""
        self.running = True
        self.queue = Queue()

    def poll_pending(self):
        """Fetch all pending downloads from the database."""
        return self.queue.get_pending()

    def mark_downloading(self, row_id):
        """Mark a download as 'downloading' in the database."""
        self.queue.start_download(row_id)

    def mark_downloaded(self, row_id, filename, extractor):
        """Mark a download as 'downloaded' and store metadata in the database."""
        self.queue.complete_download(row_id, filename, extractor)

    def mark_failed(self, row_id):
        """Mark a download as 'failed' in the database."""
        self.queue.fail_download(row_id)

    def increment_retries(self, row_id):
        """Increment the retry counter for a download in the database."""
        self.queue.increment_retries(row_id)

    def download_media(self, row_id, url, retries):
        """Download media using shared utility."""
        download_media(self.queue, row_id, url,
                       retries, max_retries=MAX_RETRIES)

    def run(self):
        """Main loop for polling and processing downloads."""
        startup_msg = 'Daemon started. Polling for pending downloads...'
        logger.info(startup_msg)
        print(startup_msg)  # Print for daemon visibility
        try:
            while self.running:
                pending = self.poll_pending()
                if pending:
                    pending_msg = f'Found {len(pending)} pending downloads.'
                    logger.info(pending_msg)
                    print(pending_msg)  # Print for daemon visibility
                    for row_id, url, retries in pending:
                        self.download_media(row_id, url, retries)
                else:
                    no_pending_msg = 'No pending downloads.'
                    logger.debug(no_pending_msg)
                    print(no_pending_msg)  # Print for daemon visibility
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            shutdown_msg = 'Daemon stopped.'
            logger.info(shutdown_msg)
            print(shutdown_msg)  # Print for daemon visibility


def main():
    """Main function for the daemon."""
    config_file_path = get_config_path()
    if not config_file_path.exists():
        logger.error("Config file not found. Please run 'yt-dl-manager init' to create one.")
        return
    daemon = YTDLManagerDaemon()
    daemon.run()


if __name__ == '__main__':
    main()
