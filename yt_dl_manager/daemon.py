"""yt-dl-manager daemon: manages yt-dlp downloads from an SQLite queue."""

import os
import time
import logging
from dotenv import load_dotenv
import yt_dlp
from .queue import Queue

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
        self.queue = Queue(self.db_path)
        self.logger = logging.getLogger(__name__)

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
        self.logger.info("Starting download for row_id %d, URL: %s, retry attempt: %d",
                         row_id, url, retries)
        self.mark_downloading(row_id)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.debug("Calling yt-dlp extract_info for URL: %s", url)
                info = ydl.extract_info(url, download=True)
                extractor = info.get('extractor', 'unknown')
                self.logger.debug("Extract_info completed. Extractor: %s, Info keys: %s",
                                  extractor, list(info.keys()) if info else 'None')

                self.logger.debug("Calling yt-dlp prepare_filename")
                filename = ydl.prepare_filename(info)
                self.logger.debug("Prepare_filename completed. Filename: %s", filename)
            self.mark_downloaded(row_id, filename, extractor)
            self.logger.info("Downloaded successfully: %s", filename)
        except yt_dlp.utils.DownloadError as err:
            self.logger.debug("DownloadError occurred: %s", str(err))
            self.increment_retries(row_id)
            if retries + 1 >= MAX_RETRIES:
                self.mark_failed(row_id)
                self.logger.error(
                    "Download failed for %s after %d attempts: %s", 
                    url, MAX_RETRIES, str(err)
                )
            else:
                # Set status back to pending for retry
                self.queue.set_status_to_pending(row_id)
                self.logger.warning(
                    "Download failed for %s, will retry (attempt %d/%d): %s", 
                    url, retries+1, MAX_RETRIES, str(err)
                )

    def run(self):
        """Main loop for polling and processing downloads."""
        self.logger.info('Daemon started. Polling for pending downloads...')
        try:
            while self.running:
                pending = self.poll_pending()
                if pending:
                    self.logger.info('Found %d pending downloads.', len(pending))
                    for row_id, url, retries in pending:
                        self.download_media(row_id, url, retries)
                else:
                    self.logger.debug('No pending downloads.')
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            self.logger.info('Daemon stopped.')

if __name__ == '__main__':
    daemon = YTDLManagerDaemon(DB_PATH)
    daemon.run()
