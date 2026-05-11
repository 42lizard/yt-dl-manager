
"""Add URLs to the yt-dl-manager SQLite queue and optionally download immediately."""

import logging
import sys
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

    def queue_length(self):
        """Return the number of items in the queue."""
        return self.queue.get_queue_length()


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


if __name__ == '__main__':
    if len(sys.argv) != 2:
        # Keep as print for CLI usage
        print("Usage: python -m yt_dl_manager.add_to_queue <media_url>")
        sys.exit(1)
    input_url = sys.argv[1]
    adder = AddToQueue()
    adder.add_url(input_url)
