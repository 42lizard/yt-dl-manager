"""Test utilities."""
from db_utils import DatabaseUtils


def create_test_schema(db_path):
    """Create the downloads table schema in the test database.

    Args:
        db_path (str): Path to the test database file.
    """
    # Use DatabaseUtils to ensure consistent schema creation
    DatabaseUtils(db_path)
