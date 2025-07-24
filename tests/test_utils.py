"""Test utilities."""
import sqlite3


def create_test_schema(db_path):
    """Create the downloads table schema in the test database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            status TEXT,
            timestamp_requested DATETIME,
            timestamp_downloaded DATETIME,
            final_filename TEXT,
            extractor TEXT,
            retries INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
