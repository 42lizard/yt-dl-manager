# yt-dl-manager — Agent Guide

## Commands

```bash
# install dev deps (uses virtualenv at .venv)
pip install -e ".[dev]"

# run full test suite
python -m pytest tests/ -v

# single test file / method
python -m pytest tests/test_daemon.py -v
python -m pytest tests/test_daemon.py::TestYTDLManagerDaemon::test_poll_pending -v

# lint — app must score 10/10 (separate .pylintrc files)
pylint --rcfile=yt_dl_manager/.pylintrc $(git ls-files 'yt_dl_manager/*.py')
pylint --rcfile=tests/.pylintrc $(git ls-files 'tests/*.py')

# auto-format
autopep8 --in-place <file>
```

## Architecture

**Layers**: `CLI (__main__.py)` → `Services (daemon.py, add_to_queue.py, maintenance.py)` → `Queue (queue.py)` → `DatabaseUtils (db_utils.py)`

- `Queue` is the central facade — services must use `Queue`, never `DatabaseUtils` directly.
- `config.py` uses `configparser` + `platformdirs`. A module-level `config` singleton is imported throughout.
- `i18n.py` provides `_()` gettext. All user-facing CLI strings must be wrapped in `_()`. Available: `en`, `de`.
- `tui.py` uses the Textual library.
- `download_utils.py` has shared yt-dlp logic used by daemon and add commands.
- `logging_config.py` sets up file + stderr handlers. Use `logging.getLogger(__name__)` in each module. Log level via `YT_DL_MANAGER_LOG_LEVEL`.

## Key conventions

- **Python >= 3.11 required.**
- **Pylint 10/10 mandatory** for app code. Do not add `# pylint: disable` — fix the code. Test `.pylintrc` disables `duplicate-code`, `too-few-public-methods`, `too-many-public-methods`.
- **Tests**: `unittest.TestCase`, `tempfile` for DB fixtures, `unittest.mock`. Use `tests.test_utils.create_test_schema(db_path)` to set up test databases.
- **SQL**: parameterized queries only (`?` placeholders). Never f-strings or string interpolation in SQL.
- **Version** in both `pyproject.toml` and `yt_dl_manager/__init__.py:__version__`.
- **Entry point**: `pyproject.toml` console_scripts → `yt_dl_manager.__main__:main`. Also runnable as `python -m yt_dl_manager`.
- Keep `plan.md` and `README.md` up to date with relevant changes.
