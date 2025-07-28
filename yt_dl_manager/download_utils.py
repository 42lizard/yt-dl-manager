"""Shared download logic for yt-dl-manager to avoid code duplication."""

import yt_dlp
from .config import config


def download_media(queue, row_id, url, retries, max_retries=3):
    """Download media using yt-dlp, update database, and handle retries."""
    target_folder = config['DEFAULT']['target_folder']
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{target_folder}/%(extractor)s/%(title)s.%(ext)s',
        'writemetadata': True,
        'embedmetadata': True,
        'quiet': True,
    }
    # Atomically claim the job for download
    if not queue.claim_pending_for_download(row_id):
        print(f"Skipping download for row {row_id}: already being processed.")
        return
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            extractor = info.get('extractor', 'unknown')
            filename = ydl.prepare_filename(info)
        queue.complete_download(row_id, filename, extractor)
        print(f"Downloaded: {filename}")
    except yt_dlp.utils.DownloadError as err:
        queue.increment_retries(row_id)
        if retries + 1 >= max_retries:
            queue.fail_download(row_id)
            print(
                f"Download failed for {url} after {max_retries} attempts: {err}"
            )
        else:
            queue.set_status_to_pending(row_id)
            print(
                f"Download failed for {url}, will retry (attempt {retries+1}/{max_retries}): {err}"
            )
