"""Script to add media URLs to the yt-dl-manager SQLite queue."""

import sys
from .queue import Queue
from .config import get_config_path

class AddToQueue:
    """Class to manage adding URLs to the yt-dl-manager queue."""
    def __init__(self):
        """Initialize with the database path."""
        self.queue = Queue()

    def add_url(self, media_url):
        """Add a media URL to the downloads queue."""
        success, message = self.queue.add_url(media_url)
        print(message)
        return success

    def queue_length(self):
        """Return the number of items in the queue."""
        return self.queue.get_queue_length()

def main(args):
    """Main function for adding a URL to the queue."""
    config_file_path = get_config_path()
    if not config_file_path.exists():
        print("Config file not found. Please run 'yt-dl-manager init' to create one.")
        return
    queue_adder = AddToQueue()
    queue_adder.add_url(args.url)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python -m yt_dl_manager.add_to_queue <media_url>")
        sys.exit(1)
    input_url = sys.argv[1]
    adder = AddToQueue()
    adder.add_url(input_url)
