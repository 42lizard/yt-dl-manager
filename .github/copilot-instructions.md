# Copilot Instructions for yt-dl-manager

## Build, Test, and Lint

Use the virtualenv at `.venv` for all Python commands.

```bash
# Run full test suite
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_daemon.py -v

# Run a single test method
python -m pytest tests/test_daemon.py::TestYTDLManagerDaemon::test_poll_pending -v

# Lint application code (must score 10/10)
pylint --rcfile=yt_dl_manager/.pylintrc $(git ls-files 'yt_dl_manager/*.py')

# Lint test code (duplicate-code is disabled here)
pylint --rcfile=tests/.pylintrc $(git ls-files 'tests/*.py')

# Auto-format edited files
autopep8 --in-place <file>
```

## Architecture

CLI entry point (`__main__.py`) uses argparse subcommands that dispatch to handler functions. The layered architecture flows as:

**CLI** (`__main__.py`) → **Services** (`daemon.py`, `add_to_queue.py`, `maintenance.py`) → **Queue** (`queue.py`) → **Database** (`db_utils.py`)

- `Queue` is the central facade for all download queue operations. Services use `Queue`, never `DatabaseUtils` directly.
- `DatabaseUtils` manages the SQLite database with a single `downloads` table. Status transitions use the `DownloadStatus` enum (pending → downloading → downloaded/failed).
- `config.py` uses `configparser` + `platformdirs` for OS-specific paths. A module-level `config` singleton is imported throughout.
- `i18n.py` provides a `_()` gettext function. All user-facing CLI strings must be wrapped in `_()`.
- `tui.py` uses the Textual library for the terminal UI.
- `download_utils.py` contains shared yt-dlp integration logic used by both daemon and add commands.
- `logging_config.py` sets up file + stderr handlers. Use `logging.getLogger(__name__)` in each module.

## Key Conventions

### Python compatibility
- Must work on Python 3.11, 3.12, 3.13, and 3.14.

### Code quality
- Pylint must score **10/10** for application code. Do not add `# pylint: disable` comments to achieve this — fix the code instead.
- Application and test code have separate `.pylintrc` files (`yt_dl_manager/.pylintrc` and `tests/.pylintrc`).
- Format with PEP 8. Run `autopep8 --in-place` on edited files.

### Test-driven development
- Write unit tests **before** implementing new features.
- Tests use `unittest.TestCase` with `tempfile` for database fixtures and `unittest.mock` for mocking.
- Use `tests/test_utils.create_test_schema(db_path)` to set up test databases.
- The full test suite must always pass before considering work done.

### Security
- **Never** use f-strings or string interpolation in SQL queries. Always use parameterized queries (`?` placeholders).
- Validate and sanitize user input, especially URLs (`db_utils.is_valid_url`) and filenames (`db_utils.sanitize_filename`).

### Git workflow
- Do not automatically stage or commit to the main branch.
- If you `cd` into a directory, always `cd` back when done.

### Documentation
- Keep `plan.md` and `README.md` up to date when making relevant changes. All docs in English.