# yt-dl-manager

[![Tests](https://github.com/42lizard/yt-dl-manager/workflows/Tests/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/test.yml)
[![Pylint](https://github.com/42lizard/yt-dl-manager/workflows/Pylint/badge.svg)](https://github.com/42lizard/yt-dl-manager/actions/workflows/pylint.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

A simple Python daemon for managing media downloads using yt-dlp, with SQLite3 queueing and a user-friendly CLI
## ✨ Features

- 🎯 **Queue-based downloads** - SQLite3 database for reliable URL management
- 🏆 **Best quality downloads** - Automatically selects best video+audio quality
- 📁 **Smart organization** - Files organized by extractor (youtube, vimeo, etc.)
- 🔄 **Retry logic** - Up to 3 attempts for failed downloads with backoff
- 📝 **Metadata embedding** - Embeds metadata directly in downloaded files
- 📋 **Production logging** - Comprehensive logging with file and console output
- 🔒 **Security hardened** - Protected against SQL injection attacks
- 🎛️ **User-friendly config** - Automatic configuration in user directories with `init` command
- 🛠️ **Auto-initialization** - Database schema created automatically on first use
- 🏗️ **Centralized queue management** - Clean architecture with dedicated Queue class
- 🗃️ **Database maintenance** - Comprehensive commands for queue and file management
- 🧪 **Comprehensive testing** - 144 unit tests with 100% pass rate
- 📊 **Code quality** - 10/10 pylint score across all modules
- 🚀 **CI/CD ready** - GitHub Actions workflow included
- ⚙️ **Command-line interface** - Modern subcommands for all operations
- 🖥️ **Terminal User Interface (TUI)** - Interactive keyboard-driven interface for queue management
- 🌐 **Web User Interface (Web UI)** - Responsive browser-based dashboard with HTMX
- 🌍 **Internationalization** - Full i18n support with English and German languages

## 🚀 Quick Start

### Installation

#### Option 1: Install from PyPI (coming soon)

```bash
pip install yt-dl-manager
```

#### Option 2: Install from Source (Recommended for now)
1. **Clone the repository and set up the environment**:
   ```bash
   git clone https://github.com/42lizard/yt-dl-manager.git
   cd yt-dl-manager
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

#### System Dependencies
2. **Install required system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   # macOS
   brew install ffmpeg
   # Arch Linux
   sudo pacman -S ffmpeg
   ```

### Getting Started

1. **Initialize configuration**:
   ```bash
   # Create default configuration file
   yt-dl-manager init
   
   # Or force overwrite existing config
   yt-dl-manager init --force
   ```

### Basic Usage

```bash
# Show help
yt-dl-manager --help

# Add URLs to download queue
yt-dl-manager add "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
yt-dl-manager add "https://vimeo.com/123456789"

# Start the daemon (runs continuously)
yt-dl-manager daemon

# Launch the Terminal User Interface (TUI)
yt-dl-manager tui

# Launch the Web User Interface (Web UI)
yt-dl-manager webui
```

## 🖥️ Terminal User Interface (TUI)

yt-dl-manager includes a modern Terminal User Interface built with Textual, providing an interactive way to manage your download queue directly from the terminal.

### Launching the TUI

```bash
# Launch TUI with default settings (shows 10 recent downloads)
yt-dl-manager tui

# Launch TUI with custom recent downloads limit
yt-dl-manager tui --recent-limit 20
```

### TUI Features

- **📋 Dual-Panel Layout**: 
  - **Pending Downloads Panel**: Shows all queued downloads with ID, URL, status, timestamp, and retry count
  - **Recent Completed Downloads Panel**: Displays recent completed downloads with full file paths

- **⌨️ Keyboard Shortcuts**:
  - Press **`a`** to open a modal dialog for entering new video URLs
  - Press **`r`** to manually refresh the data tables
  - Press **`q`** to quit the application
  - **Enter** key submits URLs in the input modal
  - **Escape** key cancels the modal

- **🎯 Smart Display**:
  - URLs are truncated for readability while maintaining essential information
  - Timestamps formatted as YYYY-MM-DD HH:MM for easy reading
  - Full file paths shown in completed downloads for better file management
  - Responsive design that adapts to terminal size

- **🔄 Real-time Integration**:
  - Connects directly to your existing SQLite database
  - Added URLs are immediately available to the daemon process
  - No need to restart the daemon when adding URLs via TUI

### TUI Command Options

```bash
# Basic usage
yt-dl-manager tui

# Control recent downloads display
yt-dl-manager tui --recent-limit 25    # Show 25 recent downloads
yt-dl-manager tui --recent-limit 5     # Show only 5 recent downloads
```

The TUI provides a modern, efficient way to monitor download queues and add new URLs without switching between terminal commands, significantly improving the user experience for interactive queue management.

## 🌐 Web User Interface (Web UI)

yt-dl-manager includes a responsive Web User Interface built with Flask and HTMX, providing a browser-based dashboard for managing your download queue from any device.

### Launching the Web UI

```bash
# Launch Web UI with default settings (127.0.0.1:5000)
yt-dl-manager webui

# Launch Web UI with custom host and port
yt-dl-manager webui --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:5000` in your browser after launching.

### Web UI Features

- **📊 Live Dashboard**:
  - **Status Bar**: Real-time counts of pending, downloading, completed, and failed downloads
  - **Pending Downloads Panel**: Shows all queued downloads with ID, URL, status, timestamp, and retry count
  - **In-Progress Panel**: Displays currently downloading items
  - **Completed Downloads Panel**: Shows recent completed downloads with file paths

- **⚡ HTMX-Powered Interactions**:
  - Auto-refreshing sections update every 2 seconds without page reloads
  - Add URLs via form submission with instant toast notifications
  - Download, retry, and remove actions with immediate visual feedback
  - All interactions use server-rendered HTML fragments for zero client-side JavaScript

- **📱 Responsive Design**:
  - Mobile-first CSS that adapts from phones to desktops
  - Touch-friendly buttons and form inputs
  - Optimized table layouts for small screens

- **🔄 Real-time Integration**:
  - Connects directly to your existing SQLite database
  - Safe concurrent operation with the daemon via atomic job claiming
  - Added URLs are immediately available to the daemon process
  - No need to restart the daemon when adding URLs via Web UI

### Web UI Command Options

```bash
# Basic usage
yt-dl-manager webui

# Custom bind address
yt-dl-manager webui --host 0.0.0.0       # Listen on all interfaces
yt-dl-manager webui --port 8080         # Use port 8080
yt-dl-manager webui --host 0.0.0.0 --port 8080
```

The Web UI provides a modern, accessible way to monitor download queues and manage URLs from any browser, complementing the TUI and CLI interfaces for maximum flexibility.

## 🔧 Database Maintenance Commands

yt-dl-manager includes comprehensive database maintenance commands for managing your download queue:

### Queue Viewing Commands
```bash
# Show queue status dashboard
yt-dl-manager status

# List pending downloads with optional filters
yt-dl-manager list pending --limit 10 --sort-by date

# List failed downloads
yt-dl-manager list failed

# List downloaded items
yt-dl-manager list downloaded --extractor youtube
```

### Queue Management Commands
```bash
# Remove all failed downloads older than 30 days
yt-dl-manager remove failed --older-than 30

# Remove specific items by ID or URL pattern
yt-dl-manager remove items 123 456
yt-dl-manager remove items "youtube.com/watch?v=example"

# Retry failed downloads
yt-dl-manager retry --failed
yt-dl-manager retry 123 456
```

### File System Integrity Commands
```bash
# Check for missing files
yt-dl-manager verify

# Check and automatically fix missing files
yt-dl-manager verify --fix

# Mark items for redownload
yt-dl-manager redownload 123 456
```

### Database Maintenance Commands
```bash
# Clean up database and optimize
yt-dl-manager cleanup --dry-run
yt-dl-manager cleanup

# Export queue data
yt-dl-manager export --format json --output queue.json
yt-dl-manager export --format csv --status pending
```

## 📋 Detailed Usage

### Adding Downloads

The `add` command provides intelligent duplicate handling:


```bash
# Add a new URL to the queue
yt-dl-manager add "https://www.youtube.com/watch?v=example"
# Output: URL added to queue: https://www.youtube.com/watch?v=example

# Add a new URL and immediately start the download
yt-dl-manager add "https://www.youtube.com/watch?v=example" --download
# or using the short flag
yt-dl-manager add "https://www.youtube.com/watch?v=example" -d
# Output:
# URL added to queue: https://www.youtube.com/watch?v=example
# Downloaded: downloads/youtube/Example Video.mp4

# Try to add the same URL again
yt-dl-manager add "https://www.youtube.com/watch?v=example"
# Output: URL already exists in queue: https://www.youtube.com/watch?v=example
#         Status: pending
```

### Running the Daemon

The daemon polls the database every 10 seconds and processes pending downloads:

```bash
yt-dl-manager daemon
# Output: Daemon started. Polling for pending downloads...
#         Found 2 pending downloads.
#         Downloaded: downloads/youtube/Rick Astley - Never Gonna Give You Up.mp4
```

### Configuration Management

Initialize or manage configuration:

```bash
# Create default configuration file
yt-dl-manager init

# Force overwrite existing config
yt-dl-manager init --force

# Show help for all commands
yt-dl-manager --help
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
target_folder = /Users/username/Downloads/yt-dl-manager
database_path = /Users/username/Library/Application Support/yt-dl-manager/yt_dl_manager.db
language = en
```

*Note: Actual paths will vary by operating system. The application uses `platformdirs` to automatically determine the appropriate user directories for your OS.*

To customize, edit the config file or create a new default configuration:
```bash
yt-dl-manager init
```

### Language Settings

yt-dl-manager supports multiple languages with automatic detection and manual override:

**Available Languages:**
- **English** (`en`) - Default
- **German** (`de`) - Deutsch

**Language Commands:**
```bash
# Show current language setting
yt-dl-manager language show

# Set language to German
yt-dl-manager language set de

# Set language to English
yt-dl-manager language set en

# Use automatic detection based on system locale
yt-dl-manager language set auto
```

**Automatic Detection:**
The application automatically detects your system locale and uses the appropriate language if supported. If your system language is not supported, it defaults to English.

**Manual Override:**
Language preferences are stored in your configuration file and persist across application restarts.

### Logging Configuration

The application includes comprehensive logging for production use:

- **Log files**: Stored in user log directory (e.g., `~/.local/share/yt-dl-manager/logs/yt-dl-manager.log`)
- **Console output**: Warnings and errors displayed on stderr
- **CLI feedback**: User-visible messages shown during interactive use
- **Log levels**: Configurable via `YT_DL_MANAGER_LOG_LEVEL` environment variable

```bash
# Set debug logging level
export YT_DL_MANAGER_LOG_LEVEL=DEBUG
yt-dl-manager daemon

# Default level is INFO
yt-dl-manager daemon
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
│   ├── __main__.py        # CLI entry point with comprehensive subcommands
│   ├── daemon.py          # Main daemon service
│   ├── add_to_queue.py    # URL addition logic
│   ├── queue.py           # Centralized queue management class
│   ├── db_utils.py        # Database schema utilities with DownloadStatus enum
│   ├── maintenance.py     # Database maintenance commands
│   ├── config.py          # Configuration management with platformdirs
│   ├── create_config.py   # Default configuration creation utility
│   ├── download_utils.py  # Shared download logic with yt-dlp integration
│   ├── logging_config.py  # Centralized logging configuration
│   ├── i18n.py            # Internationalization utilities with gettext
│   ├── tui.py             # Terminal User Interface with Textual
│   ├── web_ui.py          # Web User Interface with Flask and HTMX
│   ├── templates/         # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── partials/
│   └── static/            # Static assets (CSS)
│       └── css/
│           └── style.css
│   └── locale/            # Translation files
│       └── de/            # German translations
│           └── LC_MESSAGES/
│               ├── yt-dl-manager.po  # German translation source
│               └── yt-dl-manager.mo  # Compiled German translations
├── tests/                 # Unit test suite
│   ├── test_daemon.py     # Daemon tests (13 test cases)
│   ├── test_add_to_queue.py # CLI tool tests (7 test cases)
│   ├── test_queue.py      # Queue class tests (22 test cases)
│   ├── test_db_utils.py   # Database utilities tests (28 test cases)
│   ├── test_maintenance.py # Maintenance commands tests (19 test cases)
│   ├── test_create_config.py # Configuration tests (3 test cases)
│   ├── test_tui.py        # TUI tests (11 test cases)
│   ├── test_web_ui.py     # Web UI tests (11 test cases)
│   ├── test_web_ui_background.py # Web UI background tests (1 test case)
│   ├── test_i18n.py       # Internationalization tests (8 test cases)
│   └── test_utils.py      # Test helpers
├── LICENSE                # ISC license
└── README.md              # Documentation
```

### Test Coverage

- **Daemon Tests (13 cases)**: Database operations, download logic, retry handling, daemon loop, error scenarios
- **CLI Tests (7 cases)**: URL addition, duplicate detection, queue management, edge cases, immediate downloads
- **Queue Tests (22 cases)**: Centralized queue operations, status management, queue statistics
- **Database Tests (28 cases)**: Extended database operations, maintenance functions, data integrity
- **Maintenance Tests (19 cases)**: All maintenance commands, file verification, data export/import
- **Configuration Tests (3 cases)**: Config file creation, force overwrite, error handling
- **TUI Tests (11 cases)**: Terminal User Interface functionality, modal dialogs, keyboard shortcuts
- **Web UI Tests (11 cases)**: Flask route handlers, fragment rendering, form validation
- **Web UI Background Tests (1 case)**: ThreadPoolExecutor integration for non-blocking downloads
- **I18n Tests (8 cases)**: Translation functionality, locale detection, language switching
- **Quality Metrics**: 100% test pass rate (144/144), 10/10 pylint score, CI/CD pipeline

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
