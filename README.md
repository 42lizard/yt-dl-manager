# yt-dl-manager

[![Tests](https://github.com/42lizard/yt-dl-manager/workflows/Tests/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/test.yml)
[![Pylint](https://github.com/42lizard/yt-dl-manager/workflows/Pylint/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/pylint.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

A simple Python daemon for managing media downloads using yt-dlp, with SQLite3 queueing and a user-friendly CLI
## ✨ Features

- 🎯 **Queue-based downloads** - SQLite3 database for reliable URL management
- 🏆 **Best quality downloads** - Automatically selects best video+audio quality
- 📁 **Smart organization** - Files organized by extractor (youtube, vimeo, etc.)
- 🔄 **Retry logic** - Up to 3 attempts for failed downloads with backoff
- 📝 **Metadata embedding** - Embeds metadata directly in downloaded files
- 🎛️ **User-friendly config** - Automatic configuration in user directories with `init` command
- 🛠️ **Auto-initialization** - Database schema created automatically on first use
- 🏗️ **Centralized queue management** - Clean architecture with dedicated Queue class
- 🧪 **Comprehensive testing** - 63 unit tests with 100% pass rate
- 📊 **Code quality** - 10/10 pylint score across all modules
- 🚀 **CI/CD ready** - GitHub Actions workflow included
- ⚙️ **Command-line interface** - Simple subcommands for all operations

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

3. **Initialize configuration**:
   ```bash
   # Create default configuration file
   python -m yt_dl_manager init
   
   # Or force overwrite existing config
   python -m yt_dl_manager init --force
   ```

### Basic Usage

```bash
# Show help
python -m yt_dl_manager
# Add URLs to download queue
python -m yt_dl_manager add "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python -m yt_dl_manager add "https://vimeo.com/123456789"

# Start the daemon (runs continuously)
python -m yt_dl_manager daemon
```

## 📋 Detailed Usage

### Adding Downloads

The `add` command provides intelligent duplicate handling:

```bash
# Add a new URL
python -m yt_dl_manager add "https://www.youtube.com/watch?v=example"
# Output: URL added to queue: https://www.youtube.com/watch?v=example

# Try to add the same URL again
python -m yt_dl_manager add "https://www.youtube.com/watch?v=example"
# Output: URL already exists in queue: https://www.youtube.com/watch?v=example
#         Status: pending
```

### Running the Daemon

The daemon polls the database every 10 seconds and processes pending downloads:

```bash
python -m yt_dl_manager daemon
# Output: Daemon started. Polling for pending downloads...
#         Found 2 pending downloads.
#         Downloaded: downloads/youtube/Rick Astley - Never Gonna Give You Up.mp4
```

### Configuration Management

Initialize or manage configuration:

```bash
# Create default configuration file
python -m yt_dl_manager init

# Force overwrite existing config
python -m yt_dl_manager init --force

# Show help for all commands
python -m yt_dl_manager --help
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

The application automatically creates configuration files in user directories:

**Default Configuration Locations:**
- **macOS**: `~/Library/Application Support/yt-dl-manager/config.ini`
- **Linux**: `~/.config/yt-dl-manager/config.ini`
- **Windows**: `%APPDATA%\yt-dl-manager\config.ini`

**Default Settings (example for macOS):**
```ini
[DEFAULT]
TARGET_FOLDER = /Users/username/Downloads/yt-dl-manager
DATABASE_PATH = /Users/username/Library/Application Support/yt-dl-manager/yt_dl_manager.db
```

*Note: Actual paths will vary by operating system. The application uses `platformdirs` to automatically determine the appropriate user directories for your OS.*

To customize, edit the config file or create a new default configuration:
```bash
python -m yt_dl_manager init
```

## 🧪 Development & Testing

### Running Tests

```bash
# Run all unit tests
python -m pytest tests/ -v

# Check code quality
pylint yt_dl_manager

# Run tests in specific file
python -m pytest tests/test_daemon.py -v
```

## Project Structure

```
yt-dl-manager/
├── yt_dl_manager/         # Main package directory
│   ├── __init__.py
│   ├── __main__.py        # CLI entry point with subcommands (init, daemon, add)
│   ├── daemon.py          # Main daemon service
│   ├── add_to_queue.py    # URL addition logic
│   ├── queue.py           # Centralized queue management class
│   ├── db_utils.py        # Database schema utilities with DownloadStatus enum
│   ├── config.py          # Configuration management with platformdirs
│   └── create_config.py   # Default configuration creation utility
├── tests/                 # Unit test suite
│   ├── test_daemon.py     # Daemon tests (13 test cases)
│   ├── test_add_to_queue.py # CLI tool tests (8 test cases)
│   ├── test_queue.py      # Queue class tests (26 test cases)
│   ├── test_db_utils.py   # Database utilities tests (15 test cases)
│   ├── test_create_config.py # Configuration tests (3 test cases)
│   └── test_utils.py      # Test helpers
├── requirements.txt       # Dependencies
├── LICENSE                # ISC license
└── README.md              # Documentation
```

### Test Coverage

- **Daemon Tests (13 cases)**: Database operations, download logic, retry handling, daemon loop, error scenarios
- **CLI Tests (8 cases)**: URL addition, duplicate detection, queue management, edge cases
- **Queue Tests (26 cases)**: Centralized queue operations, status management, queue statistics
- **Database Tests (15 cases)**: Low-level database operations, schema management, data integrity
- **Configuration Tests (3 cases)**: Config file creation, force overwrite, error handling
- **Quality Metrics**: 100% test pass rate (63/63), 10/10 pylint score, CI/CD pipeline

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

Edit `yt_dl_manager/daemon.py` to customize download options:

```python
# In the download_media method, modify the ydl_opts dictionary:
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': f'{target_folder}/%(extractor)s/%(title)s.%(ext)s',
    'writemetadata': True,
    'embedmetadata': True,
    'quiet': True,
    'writesubtitles': True,  # Add this for subtitles
    'writeautomaticsub': True,  # Add this for auto-generated subs
}
```

### Monitoring Downloads

Query the database directly (check config for actual database path):

```bash
# Default paths:
# macOS: ~/Library/Application\ Support/yt-dl-manager/yt_dl_manager.db
# Linux: ~/.local/share/yt-dl-manager/yt_dl_manager.db

sqlite3 ~/Library/Application\ Support/yt-dl-manager/yt_dl_manager.db \
  "SELECT url, status, timestamp_requested FROM downloads ORDER BY timestamp_requested DESC LIMIT 10;"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Ensure tests pass: `python -m pytest tests/ -v`
5. Check code quality: `pylint yt_dl_manager`
6. Commit and push: `git commit -am 'Add feature' && git push origin feature-name`
7. Create a Pull Request

## 📄 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful media downloader that powers this project
- [FFmpeg](https://ffmpeg.org/) - Essential for media processing and metadata embedding
