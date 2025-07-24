
"""Script to add media URLs to the yt-dl-manager SQLite queue."""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')

class AddToQueue:
    """Class to manage adding URLs to the yt-dl-manager queue."""
    def __init__(self, db_path):
        """Initialize with the database path."""
        self.db_path = db_path

    def add_url(self, media_url):
        """Add a media URL to the downloads queue."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, 'pending', ?)",
                (media_url, datetime.utcnow().isoformat())
            )
            conn.commit()
            print(f"URL added to queue: {media_url}")
        except sqlite3.IntegrityError:
            cur.execute("SELECT final_filename, status FROM downloads WHERE url = ?", (media_url,))
            row = cur.fetchone()
            if row:
                filename, status = row
                if filename:
                    print(
                        f"URL already exists in queue: {media_url}\n"
                        f"Status: {status}\nDownloaded file: {filename}"
                    )
                else:
                    print(f"URL already exists in queue: {media_url}\nStatus: {status}")
            else:
                print(f"URL already exists in queue: {media_url}")
        finally:
            conn.close()

    def queue_length(self):
        """Return the number of items in the queue."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM downloads")
        count = cur.fetchone()[0]
        conn.close()
        return count

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_to_queue.py <media_url>")
        sys.exit(1)
    input_url = sys.argv[1]
    adder = AddToQueue(DB_PATH)
    adder.add_url(input_url)
