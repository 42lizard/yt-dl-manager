
"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import os
import time
import sqlite3
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')
POLL_INTERVAL = 10  # seconds
MAX_RETRIES = 3

class YTDLManagerDaemon:
    """Daemon for managing yt-dlp downloads from an SQLite queue."""
    def __init__(self, db_path):
        """Initialize the daemon with the database path."""
        self.db_path = db_path
        self.running = True
        self._ensure_database_schema()

    def _ensure_database_schema(self):
        """Create or verify the downloads table schema."""
        schema = '''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            status TEXT,
            timestamp_requested DATETIME,
            timestamp_downloaded DATETIME,
            final_filename TEXT,
            extractor TEXT,
            retries INTEGER DEFAULT 0
        );
        '''
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(schema)
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            # If we can't connect to the database during initialization,
            # we'll let the error happen later during actual operations
            pass

    def poll_pending(self):
        """Fetch all pending downloads from the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, url, retries FROM downloads WHERE status = 'pending'")
        rows = cur.fetchall()
        conn.close()
        return rows

    def mark_downloading(self, row_id):
        """Mark a download as 'downloading' in the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET status = 'downloading' WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()

    def mark_downloaded(self, row_id, filename, extractor):
        """Mark a download as 'downloaded' and store metadata in the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = 'downloaded', "
            "timestamp_downloaded = datetime('now'), "
            "final_filename = ?, extractor = ? WHERE id = ?",
            (filename, extractor, row_id)
        )
        conn.commit()
        conn.close()

    def mark_failed(self, row_id):
        """Mark a download as 'failed' in the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET status = 'failed' WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()

    def increment_retries(self, row_id):
        """Increment the retry counter for a download in the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET retries = retries + 1 WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()

    def download_media(self, row_id, url, retries):
        """Download media using yt-dlp, update database, and handle retries."""
        target_folder = os.getenv('TARGET_FOLDER', 'downloads')
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': (
                f'{target_folder}/%(extractor)s/%(title)s.%(ext)s'
            ),
            'writemetadata': True,
            'embedmetadata': True,
            'quiet': True,
        }
        self.mark_downloading(row_id)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                extractor = info.get('extractor', 'unknown')
                filename = ydl.prepare_filename(info)
            self.mark_downloaded(row_id, filename, extractor)
            print(f"Downloaded: {filename}")
        except yt_dlp.utils.DownloadError as err:
            self.increment_retries(row_id)
            if retries + 1 >= MAX_RETRIES:
                self.mark_failed(row_id)
                print(
                    f"Download failed for {url} after {MAX_RETRIES} attempts: {err}"
                )
            else:
                # Set status back to pending for retry
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("UPDATE downloads SET status = 'pending' WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()
                print(
                    f"Download failed for {url}, will retry "
                    f"(attempt {retries+1}/{MAX_RETRIES}): {err}"
                )

    def run(self):
        """Main loop for polling and processing downloads."""
        print('Daemon started. Polling for pending downloads...')
        try:
            while self.running:
                pending = self.poll_pending()
                if pending:
                    print(f'Found {len(pending)} pending downloads.')
                    for row_id, url, retries in pending:
                        self.download_media(row_id, url, retries)
                else:
                    print('No pending downloads.')
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print('Daemon stopped.')

if __name__ == '__main__':
    daemon = YTDLManagerDaemon(DB_PATH)
    daemon.run()
