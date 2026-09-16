"""Download lifecycle management."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yt_dlp

from .config import config


logger = logging.getLogger(__name__)


class DownloadOutcomeKind(Enum):
    """Observable results of a Download attempt."""

    COMPLETED = 'completed'
    RETRY_SCHEDULED = 'retry_scheduled'
    FAILED = 'failed'
    NOT_AVAILABLE = 'not_available'


@dataclass(frozen=True)
class DownloadOutcome:
    """Result returned to an adapter after a Download attempt."""

    download_id: int
    kind: DownloadOutcomeKind
    filename: Optional[str] = None
    error: Optional[str] = None
    status: Optional[str] = None
    attempts: Optional[int] = None


class DownloadLifecycle:
    """Own claiming, execution, and state transitions for Downloads."""

    def __init__(self, queue, max_attempts=3):
        if not isinstance(max_attempts, int) or max_attempts <= 0:
            raise ValueError("max_attempts must be a positive integer")
        self.queue = queue
        self.max_attempts = max_attempts

    def execute(self, download_id):
        """Execute one Download attempt and return its observable outcome."""
        if not isinstance(download_id, int) or download_id <= 0:
            raise ValueError("download_id must be a positive integer")

        claimed, download = self.queue.claim_pending_for_download(download_id)
        if not claimed:
            status = download['status'] if download else None
            return DownloadOutcome(
                download_id,
                DownloadOutcomeKind.NOT_AVAILABLE,
                status=status,
            )

        target_folder = config['DEFAULT']['target_folder']
        options = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{target_folder}/%(extractor)s/%(title)s.%(ext)s',
            'writemetadata': True,
            'embedmetadata': True,
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(download['url'], download=True)
                extractor = info.get('extractor', 'unknown')
                filename = ydl.prepare_filename(info)
            self.queue.complete_download(download_id, filename, extractor)
            logger.info("Downloaded: %s", filename)
            return DownloadOutcome(
                download_id,
                DownloadOutcomeKind.COMPLETED,
                filename=filename,
            )
        except yt_dlp.utils.DownloadError as error:
            logger.warning(
                "Download attempt failed for %s",
                download_id,
                exc_info=True,
            )
            transition = self.queue.record_failed_attempt(
                download_id,
                self.max_attempts,
            )
            if transition is None:
                raise RuntimeError(
                    f"Download {download_id} is no longer in progress"
                ) from error

            kind = (
                DownloadOutcomeKind.FAILED
                if transition['status'] == 'failed'
                else DownloadOutcomeKind.RETRY_SCHEDULED
            )
            return DownloadOutcome(
                download_id,
                kind,
                error=str(error),
                status=transition['status'],
                attempts=transition['retries'],
            )
