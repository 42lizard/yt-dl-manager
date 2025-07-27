"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import time
import yt_dlp
from .queue import Queue
from .config import config, get_config_path

POLL_INTERVAL = 10  # seconds
MAX_RETRIES = 3

class YTDLManagerDaemon:
    """Daemon for managing yt-dlp downloads from an SQLite queue."""
    def __init__(self):
        """Initialize the daemon with the database path."""
        self.running = True
        self.queue = Queue()

    def poll_pending(self):
        """Fetch all pending downloads from the database."""
        return self.queue.get_pending()

    def mark_downloading(self, row_id):
        """Mark a download as 'downloading' in the database."""
        self.queue.start_download(row_id)

    def mark_downloaded(self, row_id, filename, extractor):
        """Mark a download as 'downloaded' and store metadata in the database."""
        self.queue.complete_download(row_id, filename, extractor)

    def mark_failed(self, row_id):
        """Mark a download as 'failed' in the database."""
        self.queue.fail_download(row_id)

    def increment_retries(self, row_id):
        """Increment the retry counter for a download in the database."""
        self.queue.increment_retries(row_id)

    def download_media(self, row_id, url, retries):
        """Download media using yt-dlp, update database, and handle retries."""
        target_folder = config['DEFAULT']['TARGET_FOLDER']
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
                self.queue.set_status_to_pending(row_id)
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

def main():
    """Main function for the daemon."""
    config_file_path = get_config_path()
    if not config_file_path.exists():
        print("Config file not found. Please run 'yt-dl-manager init' to create one.")
        return
    daemon = YTDLManagerDaemon()
    daemon.run()

if __name__ == '__main__':
    main()
