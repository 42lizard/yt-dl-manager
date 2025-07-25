
"""Script to add media URLs to the yt-dl-manager SQLite queue."""

import os
import sys
from dotenv import load_dotenv
from db_utils import DatabaseUtils

load_dotenv()
DB_PATH = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')

class AddToQueue:
    """Class to manage adding URLs to the yt-dl-manager queue."""
    def __init__(self, db_path):
        """Initialize with the database path."""
        self.db_path = db_path
        self.db = DatabaseUtils(self.db_path)

    def add_url(self, media_url):
        """Add a media URL to the downloads queue."""
        success, message = self.db.add_url(media_url)
        print(message)

    def queue_length(self):
        """Return the number of items in the queue."""
        return self.db.queue_length()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_to_queue.py <media_url>")
        sys.exit(1)
    input_url = sys.argv[1]
    adder = AddToQueue(DB_PATH)
    adder.add_url(input_url)
