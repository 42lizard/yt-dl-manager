# yt-dl-manager

A simple Python daemon for managing media downloads using yt-dlp, with queueing via SQLite and configuration via .env files.

## Features
- Daemonized download manager using yt-dlp
- SQLite3 database for queueing URLs
- Downloads in best available quality
- Organizes files by extractor (e.g., youtube, vimeo)
- Embeds metadata in final files
- Retry logic for failed downloads
- Configurable via `.env` file

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/42lizard/yt-dl-manager.git
   cd yt-dl-manager
   ```
2. Create and activate a Python 3.8+ virtual environment:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Install ffmpeg (required for merging and metadata):
   ```sh
   sudo apt install ffmpeg
   ```
5. Copy and edit the example config:
   ```sh
   cp .env.example .env
   # Edit .env to set TARGET_FOLDER and DATABASE_PATH as needed
   ```
6. Initialize the database:
   ```sh
   python migrate_db.py
   ```

## Usage

- **Add a URL to the queue:**
  ```sh
  python add_to_queue.py <media_url>
  ```
- **Start the daemon:**
  ```sh
  python daemon.py
  ```
- Downloaded files will appear in the folder specified by `TARGET_FOLDER`, organized by extractor.

## Notes
- The `.env` file is not tracked in git; use `.env.example` as a template.
- The daemon retries failed downloads up to 3 times before marking as failed.
- For advanced yt-dlp options, edit the `daemon.py` configuration.

## License
This project is licensed under the ISC license. See LICENSE for details.
