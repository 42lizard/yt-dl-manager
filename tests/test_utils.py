"""Test utilities."""
from yt_dl_manager.download_store import DownloadStore


def create_test_schema(db_path):
    """Create the downloads table schema in the test database.

    Args:
        db_path (str): Path to the test database file.
    """
    DownloadStore(db_path)
