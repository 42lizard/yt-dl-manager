# yt-dl-manager

[![Tests](https://github.com/42lizard/yt-dl-manager/workflows/Tests/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/test.yml)
[![Pylint](https://github.com/42lizard/yt-dl-manager/workflows/Pylint/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/pylint.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

A simple Python daemon for managing media downloads using yt-dlp, with SQLite3 queueing
## ✨ Features

- 🎯 **Queue-based downloads** - SQLite3 database for reliable URL management
- 🏆 **Best quality downloads** - Automatically selects best video+audio quality
- 📁 **Smart organization** - Files organized by extractor (youtube, vimeo, etc.)
- 🔄 **Retry logic** - Up to 3 attempts for failed downloads with backoff
- 📝 **Metadata embedding** - Embeds metadata directly in downloaded files
- 🎛️ **Environment configuration** - Easy setup via `.env` files
- 🛠️ **Auto-initialization** - Database schema created automatically on first use
- 🧪 **Comprehensive testing** - 21 unit tests with 100% pass rate
- 📊 **Code quality** - 10/10 pylint score across all modules
- 🚀 **CI/CD ready** - GitHub Actions workflow included

## 🚀 Quick Start

### Installation

1. **Clone the repository and set up the environment**:
   ```bash
   git clone https://github.com/42lizard/yt-dl-manager.git
   cd yt-dl-manager
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   # macOS
   brew install ffmpeg
   # Arch Linux
   sudo pacman -S ffmpeg
   ```

3. **Configure**:
   ```bash
   cp .env.example .env
   # Edit .env to set TARGET_FOLDER and DATABASE_PATH
   ```

### Basic Usage

```bash
# Add URLs to download queue (database auto-created on first use)
python add_to_queue.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python add_to_queue.py "https://vimeo.com/123456789"

# Start the daemon (runs continuously)
python daemon.py
```

## 📋 Detailed Usage

### Adding Downloads

The `add_to_queue.py` script provides intelligent duplicate handling:

```bash
# Add a new URL
python add_to_queue.py "https://www.youtube.com/watch?v=example"
# Output: URL added to queue: https://www.youtube.com/watch?v=example

# Try to add the same URL again
python add_to_queue.py "https://www.youtube.com/watch?v=example"
# Output: URL already exists in queue: https://www.youtube.com/watch?v=example
#         Status: pending

# Check queue length
python add_to_queue.py --help  # Shows current queue length
```

### Running the Daemon

The daemon polls the database every 10 seconds and processes pending downloads:

```bash
python daemon.py
# Output: Daemon started. Polling for pending downloads...
#         Found 2 pending downloads.
#         Downloaded: downloads/youtube/Rick Astley - Never Gonna Give You Up.mp4
```

### File Organization

Downloads are automatically organized by extractor:

```
downloads/
├── youtube/
│   ├── Video Title 1.mp4
│   └── Video Title 2.webm
├── vimeo/
│   └── Another Video.mp4
└── soundcloud/
    └── Audio Track.m4a
```

## 🔧 Configuration

Edit `.env` to customize behavior:

```bash
# Required settings
TARGET_FOLDER=downloads
DATABASE_PATH=yt_dl_manager.db

# Optional settings (defaults shown)
POLL_INTERVAL=10
MAX_RETRIES=3
```

## 🧪 Development & Testing

### Running Tests

```bash
# Run all unit tests
python -m unittest tests.test_add_to_queue tests.test_daemon -v

# Check code quality
pylint daemon.py add_to_queue.py db_utils.py

# Run tests in specific file
python -m unittest tests.test_daemon -v
```

```
## Project Structure
yt-dl-manager/
├── daemon.py              # Main daemon service
├── add_to_queue.py        # CLI tool for adding URLs  
├── db_utils.py            # Database schema utilities
├── migrate_db.py          # Database schema setup (optional - auto-migration included)
├── tests/                 # Unit test suite
│   ├── test_daemon.py     # Daemon tests (13 test cases)
│   ├── test_add_to_queue.py # CLI tool tests (8 test cases)
│   └── test_utils.py      # Test helpers
├── .env.example           # Configuration template
├── requirements.txt       # Dependencies
├── LICENSE                # ISC license
└── README.md              # Documentation
```

### Test Coverage

- **Daemon Tests (13 cases)**: Database operations, download logic, retry handling, daemon loop, error scenarios
- **CLI Tests (8 cases)**: URL addition, duplicate detection, queue management, edge cases
- **Quality Metrics**: 100% test pass rate, 10/10 pylint score, CI/CD pipeline

## Database Schema
Table: `downloads`
- `id` (INTEGER PRIMARY KEY)
- `url` (TEXT, unique)
- `status` (TEXT: pending, downloading, downloaded, failed)
- `timestamp_requested` (DATETIME)
- `timestamp_downloaded` (DATETIME, nullable)
- `final_filename` (TEXT, nullable)
- `extractor` (TEXT, nullable)
- `retries` (INTEGER DEFAULT 0)
```

## 🛠️ Advanced Usage

### Custom yt-dlp Options

Edit `daemon.py` to customize download options:

```python
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': f'{target_folder}/%(extractor)s/%(title)s.%(ext)s',
    'writemetadata': True,
    'embedmetadata': True,
    'writesubtitles': True,  # Add this for subtitles
    'writeautomaticsub': True,  # Add this for auto-generated subs
}
```

### Monitoring Downloads

Query the database directly:

```bash
sqlite3 yt_dl_manager.db "SELECT url, status, timestamp_requested FROM downloads ORDER BY timestamp_requested DESC LIMIT 10;"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Ensure tests pass: `python -m unittest tests.test_add_to_queue tests.test_daemon -v`
5. Check code quality: `pylint daemon.py add_to_queue.py db_utils.py`
6. Commit and push: `git commit -am 'Add feature' && git push origin feature-name`
7. Create a Pull Request

## 📄 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful media downloader that powers this project
- [FFmpeg](https://ffmpeg.org/) - Essential for media processing and metadata embedding
