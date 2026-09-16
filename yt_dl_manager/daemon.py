"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import logging
import time
from .queue import Queue
from .config import get_config_path
from .download import DownloadLifecycle, DownloadOutcomeKind

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds


class YTDLManagerDaemon:
    """Daemon for managing yt-dlp downloads from an SQLite queue."""

    def __init__(self):
        """Initialize the daemon with the database path."""
        self.running = True
        self.queue = Queue()
        self.downloads = DownloadLifecycle(self.queue)

    @staticmethod
    def _print_outcome(outcome):
        """Render a Download outcome for daemon users."""
        if outcome.kind is DownloadOutcomeKind.COMPLETED:
            print(f"Downloaded: {outcome.filename}")
        elif outcome.kind is DownloadOutcomeKind.RETRY_SCHEDULED:
            print(
                f"Download {outcome.download_id} failed; retry scheduled "
                f"(attempt {outcome.attempts}): {outcome.error}"
            )
        elif outcome.kind is DownloadOutcomeKind.FAILED:
            print(
                f"Download {outcome.download_id} failed after "
                f"{outcome.attempts} attempts: {outcome.error}"
            )
        else:
            print(
                f"Download {outcome.download_id} is not available "
                f"(status: {outcome.status or 'missing'})."
            )

    def run(self):
        """Main loop for polling and processing downloads."""
        startup_msg = 'Daemon started. Polling for pending downloads...'
        logger.info(startup_msg)
        print(startup_msg)  # Print for daemon visibility
        try:
            while self.running:
                pending = self.queue.get_pending()
                if pending:
                    pending_msg = f'Found {len(pending)} pending downloads.'
                    logger.info(pending_msg)
                    print(pending_msg)  # Print for daemon visibility
                    for row_id, _, _ in pending:
                        self._print_outcome(self.downloads.execute(row_id))
                else:
                    logger.debug('No pending downloads.')
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            shutdown_msg = 'Daemon stopped.'
            logger.info(shutdown_msg)
            print(shutdown_msg)  # Print for daemon visibility


def main():
    """Main function for the daemon."""
    config_file_path = get_config_path()
    if not config_file_path.exists():
        logger.error(
            "Config file not found. Please run 'yt-dl-manager init' to create one.")
        return
    daemon = YTDLManagerDaemon()
    daemon.run()
