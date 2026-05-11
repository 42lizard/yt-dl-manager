
"""Add URLs to the yt-dl-manager SQLite queue and optionally download immediately."""

import logging
from .config import get_config_path
from .queue import Queue
from .download_utils import download_media

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
        queue = queue_adder.queue
        download_media(queue, row_id, args.url, 0, max_retries=3)
