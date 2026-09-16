"""Configuration is read on demand before Download state can change."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from yt_dl_manager import add_to_queue
from yt_dl_manager.__main__ import main
from yt_dl_manager.config import (
    ConfigurationError, get_language_preference, load_paths, set_language_preference,
)
from yt_dl_manager.download_store import DownloadQuery, DownloadStatus, DownloadStore


def test_config_is_lazy_and_language_needs_no_paths(tmp_path):
    """Missing settings don't prevent language operations; changes are reloaded."""
    config_path = tmp_path / 'config.ini'
    with patch('yt_dl_manager.config.get_config_path', return_value=config_path):
        assert get_language_preference() is None
        with pytest.raises(ConfigurationError, match='init'):
            load_paths('database_path')
        set_language_preference('de')
        assert get_language_preference() == 'de'
        config_path.write_text('[DEFAULT]\ndatabase_path = first.db\n', encoding='utf-8')
        assert load_paths('database_path')['database_path'] == Path('first.db')
        config_path.write_text('[DEFAULT]\ndatabase_path = second.db\n', encoding='utf-8')
        assert load_paths('database_path')['database_path'] == Path('second.db')


@pytest.mark.parametrize('target', ['', 'target_folder =   ', 'target_folder = %(missing)s'])
def test_invalid_download_config_leaves_pending_download_untouched(tmp_path, target):
    """Immediate downloads validate before insertion, claim, or yt-dlp use."""
    database_path = tmp_path / 'downloads.db'
    store = DownloadStore(database_path)
    _, _, download_id = store.add_url('https://example.com/existing')
    config_path = tmp_path / 'config.ini'
    config_path.write_text(
        f'[DEFAULT]\ndatabase_path = {database_path}\n{target}\n', encoding='utf-8',
    )
    with (
        patch('yt_dl_manager.config.get_config_path', return_value=config_path),
        patch('yt_dl_manager.download.yt_dlp.YoutubeDL') as downloader,
    ):
        with pytest.raises(ConfigurationError):
            add_to_queue.main(SimpleNamespace(url='https://example.com/new', download=True))
        downloader.assert_not_called()
    pending = store.list_downloads(DownloadQuery(DownloadStatus.PENDING))
    assert [download.id for download in pending] == [download_id]


def test_malformed_config_has_actionable_error(tmp_path):
    """Parser errors are configuration errors rather than tracebacks."""
    config_path = tmp_path / 'config.ini'
    config_path.write_text('not an ini file', encoding='utf-8')
    with patch('yt_dl_manager.config.get_config_path', return_value=config_path):
        assert get_language_preference() is None
        with pytest.raises(ConfigurationError, match='Cannot read configuration'):
            load_paths('database_path')


@pytest.mark.parametrize('command', ['daemon', 'tui', 'status', 'add'])
def test_cli_reports_missing_configuration(tmp_path, capsys, command):
    """All entry points report missing configuration without a traceback."""
    arguments = ['yt-dl-manager', command]
    if command == 'add':
        arguments.append('https://example.com/video')
    with (
        patch('yt_dl_manager.config.get_config_path', return_value=tmp_path / 'missing.ini'),
        patch('yt_dl_manager.__main__.setup_logging'),
        patch('sys.argv', arguments),
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    assert 'init' in capsys.readouterr().err
