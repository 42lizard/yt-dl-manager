
"""Add URLs to the yt-dl-manager SQLite queue and optionally download immediately."""

from .config import load_paths
from .download_store import DownloadStore
from .download import DownloadLifecycle, DownloadOutcomeKind

class AddToQueue:
    """Class to manage adding URLs to the yt-dl-manager queue."""

    def __init__(self, store):
        """Initialize with a provided Download store."""
        self.store = store

    def add_url(self, media_url):
        """Add a media URL to the downloads queue."""
        success, message, row_id = self.store.add_url(media_url)
        print(message)  # Keep as print for CLI user feedback
        return success, row_id


def main(args):
    """Main function for adding a URL to the queue."""
    names = ('database_path', 'target_folder') if getattr(args, 'download', False) else ('database_path',)
    paths = load_paths(*names)
    queue_adder = AddToQueue(DownloadStore(paths['database_path']))
    success, row_id = queue_adder.add_url(args.url)
    if getattr(args, 'download', False) and success and row_id:
        outcome = DownloadLifecycle(queue_adder.store, paths['target_folder']).execute(row_id)
        if outcome.kind is DownloadOutcomeKind.COMPLETED:
            print(f"Downloaded: {outcome.filename}")
        elif outcome.kind is DownloadOutcomeKind.RETRY_SCHEDULED:
            print(
                f"Download {row_id} failed; retry scheduled "
                f"(attempt {outcome.attempts}): {outcome.error}"
            )
        elif outcome.kind is DownloadOutcomeKind.FAILED:
            print(
                f"Download {row_id} failed after {outcome.attempts} attempts: "
                f"{outcome.error}"
            )
        else:
            print(
                f"Download {row_id} is not available "
                f"(status: {outcome.status or 'missing'})."
            )
