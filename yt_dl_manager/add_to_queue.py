"""Script to add media URLs to the yt-dl-manager SQLite queue."""

import sys
from yt_dl_manager.queue import Queue

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

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_to_queue.py <media_url>")
        sys.exit(1)
    input_url = sys.argv[1]
    adder = AddToQueue()
    adder.add_url(input_url)
