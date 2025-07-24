import os
import time
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'yt_dl_manager.db')
POLL_INTERVAL = 10  # seconds

class YTDLManagerDaemon:
    def __init__(self, db_path):
        self.db_path = db_path
        self.running = True

    def poll_pending(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, url, retries FROM downloads WHERE status = 'pending'")
        rows = cur.fetchall()
        conn.close()
        return rows

    def mark_downloading(self, id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET status = 'downloading' WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def mark_downloaded(self, id, filename, extractor):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE downloads SET status = 'downloaded', timestamp_downloaded = datetime('now'), final_filename = ?, extractor = ? WHERE id = ?",
            (filename, extractor, id)
        )
        conn.commit()
        conn.close()

    def mark_failed(self, id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET status = 'failed' WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def increment_retries(self, id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE downloads SET retries = retries + 1 WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def download_media(self, id, url, retries):
        import yt_dlp
        target_folder = os.getenv('TARGET_FOLDER', 'downloads')
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{target_folder}/%(extractor)s/%(title)s.%(ext)s',
            'writemetadata': True,
            'embedmetadata': True,
            'quiet': True,
        }
        self.mark_downloading(id)
        MAX_RETRIES = 3
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                extractor = info.get('extractor', 'unknown')
                filename = ydl.prepare_filename(info)
            self.mark_downloaded(id, filename, extractor)
            print(f"Downloaded: {filename}")
        except Exception as e:
            self.increment_retries(id)
            if retries + 1 >= MAX_RETRIES:
                self.mark_failed(id)
                print(f"Download failed for {url} after {MAX_RETRIES} attempts: {e}")
            else:
                # Set status back to pending for retry
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("UPDATE downloads SET status = 'pending' WHERE id = ?", (id,))
                conn.commit()
                conn.close()
                print(f"Download failed for {url}, will retry (attempt {retries+1}/{MAX_RETRIES}): {e}")

    def run(self):
        print('Daemon started. Polling for pending downloads...')
        try:
            while self.running:
                pending = self.poll_pending()
                if pending:
                    print(f'Found {len(pending)} pending downloads.')
                    for id, url, retries in pending:
                        self.download_media(id, url, retries)
                else:
                    print('No pending downloads.')
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print('Daemon stopped.')

if __name__ == '__main__':
    daemon = YTDLManagerDaemon(DB_PATH)
    daemon.run()
