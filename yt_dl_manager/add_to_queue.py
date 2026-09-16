
"""Add URLs to the yt-dl-manager SQLite queue and optionally download immediately."""

import logging
from .config import get_config_path
from .queue import Queue
from .download import DownloadLifecycle, DownloadOutcomeKind

logger = logging.getLogger(__name__)


class AddToQueue:
    """Class to manage adding URLs to the yt-dl-manager queue."""

    def __init__(self, queue=None):
        """Initialize with the database path or a provided Queue instance."""
        self.queue = queue if queue is not None else Queue()

    def add_url(self, media_url):
        """Add a media URL to the downloads queue."""
        success, message, row_id = self.queue.add_url(media_url)
        print(message)  # Keep as print for CLI user feedback
        return success, row_id


def main(args):
    """Main function for adding a URL to the queue."""
    config_file_path = get_config_path()
    if not config_file_path.exists():
        logger.error(
            "Config file not found. Please run 'yt-dl-manager init' to create one.")
        print("Config file not found. Please run 'yt-dl-manager init' to create one.")
        return
    queue_adder = AddToQueue()
    success, row_id = queue_adder.add_url(args.url)
    if getattr(args, 'download', False) and success and row_id:
        outcome = DownloadLifecycle(queue_adder.queue).execute(row_id)
        if outcome.kind is DownloadOutcomeKind.COMPLETED:
            print(f"Downloaded: {outcome.filename}")
        elif outcome.kind is DownloadOutcomeKind.RETRY_SCHEDULED:
            print(
                f"Download {row_id} failed; retry scheduled "
                f"(attempt {outcome.attempts}): {outcome.error}"
            )
        elif outcome.kind is DownloadOutcomeKind.FAILED:
            print(
                f"Download {row_id} failed after {outcome.attempts} attempts: "
                f"{outcome.error}"
            )
        else:
            print(
                f"Download {row_id} is not available "
                f"(status: {outcome.status or 'missing'})."
            )
