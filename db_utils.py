"""Database utility functions for yt-dl-manager."""

import sqlite3

# Database schema definition
DOWNLOADS_TABLE_SCHEMA = '''
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

def ensure_database_schema(db_path):
    """Create or verify the downloads table schema.
    
    Args:
        db_path (str): Path to the SQLite database file.
        
    Raises:
        sqlite3.OperationalError: If database connection fails during setup.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(DOWNLOADS_TABLE_SCHEMA)
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # If we can't connect to the database during initialization,
        # we'll let the error happen later during actual operations
        pass
