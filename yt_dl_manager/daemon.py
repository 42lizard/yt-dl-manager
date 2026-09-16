"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import logging
import time
from .download_store import (
    DownloadQuery,
    DownloadSort,
    DownloadStatus,
    DownloadStore,
)
from .config import load_paths
from .download import DownloadLifecycle, DownloadOutcomeKind

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds


class YTDLManagerDaemon:
    """Daemon for managing yt-dlp downloads from an SQLite queue."""

    def __init__(self):
        """Initialize the daemon with the database path."""
        self.running = True
        paths = load_paths('database_path', 'target_folder')
        self.store = DownloadStore(paths['database_path'])
        self.downloads = DownloadLifecycle(self.store, paths['target_folder'])

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
                pending = self.store.list_downloads(DownloadQuery(
                    status=DownloadStatus.PENDING,
                    sort=DownloadSort.ID,
                    descending=False,
                ))
                if pending:
                    pending_msg = f'Found {len(pending)} pending downloads.'
                    logger.info(pending_msg)
                    print(pending_msg)  # Print for daemon visibility
                    for download in pending:
                        self._print_outcome(
                            self.downloads.execute(download.id)
                        )
                else:
                    logger.debug('No pending downloads.')
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            shutdown_msg = 'Daemon stopped.'
            logger.info(shutdown_msg)
            print(shutdown_msg)  # Print for daemon visibility


def main():
    """Main function for the daemon."""
    daemon = YTDLManagerDaemon()
    daemon.run()
