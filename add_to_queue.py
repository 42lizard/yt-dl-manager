import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')

class AddToQueue:
    def __init__(self, db_path):
        self.db_path = db_path

    def add_url(self, url):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO downloads (url, status, timestamp_requested) VALUES (?, 'pending', ?)",
                (url, datetime.utcnow().isoformat())
            )
            conn.commit()
            print(f"URL added to queue: {url}")
        except sqlite3.IntegrityError:
            cur.execute("SELECT final_filename, status FROM downloads WHERE url = ?", (url,))
            row = cur.fetchone()
            if row:
                filename, status = row
                if filename:
                    print(f"URL already exists in queue: {url}\nStatus: {status}\nDownloaded file: {filename}")
                else:
                    print(f"URL already exists in queue: {url}\nStatus: {status}")
            else:
                print(f"URL already exists in queue: {url}")
        finally:
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_to_queue.py <media_url>")
        sys.exit(1)
    url = sys.argv[1]
    adder = AddToQueue(DB_PATH)
    adder.add_url(url)
