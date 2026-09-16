"""Adapter tests for daemon.py."""

import unittest
from unittest.mock import MagicMock, patch

from yt_dl_manager.daemon import YTDLManagerDaemon
from yt_dl_manager.download import DownloadOutcome, DownloadOutcomeKind
from yt_dl_manager.download_store import Download


class TestYTDLManagerDaemon(unittest.TestCase):
    """Test daemon polling and presentation around the lifecycle module."""

    def setUp(self):
        self.store = MagicMock()
        self.downloads = MagicMock()
        with (
            patch('yt_dl_manager.daemon.load_paths', return_value={
                'database_path': ':memory:', 'target_folder': '/tmp',
            }),
            patch('yt_dl_manager.daemon.DownloadStore', return_value=self.store),
            patch(
                'yt_dl_manager.daemon.DownloadLifecycle',
                return_value=self.downloads,
            ),
        ):
            self.daemon = YTDLManagerDaemon()

    @patch('yt_dl_manager.daemon.time.sleep')
    @patch('builtins.print')
    def test_run_no_pending_downloads(self, mock_print, mock_sleep):
        """The daemon polls and sleeps when no Download is pending."""
        self.store.list_downloads.return_value = []
        mock_sleep.side_effect = lambda *_: setattr(
            self.daemon, 'running', False
        )

        self.daemon.run()

        mock_print.assert_any_call(
            'Daemon started. Polling for pending downloads...'
        )
        mock_sleep.assert_called_once_with(10)
        self.downloads.execute.assert_not_called()

    @patch('yt_dl_manager.daemon.time.sleep')
    @patch('builtins.print')
    def test_run_executes_pending_download(self, mock_print, mock_sleep):
        """The daemon passes only the Download identity to the lifecycle."""
        pending = MagicMock(spec=Download)
        pending.id = 7
        self.store.list_downloads.return_value = [pending]
        self.downloads.execute.return_value = DownloadOutcome(
            7,
            DownloadOutcomeKind.COMPLETED,
            filename='/tmp/video.mp4',
        )
        mock_sleep.side_effect = lambda *_: setattr(
            self.daemon, 'running', False
        )

        self.daemon.run()

        self.downloads.execute.assert_called_once_with(7)
        mock_print.assert_any_call('Downloaded: /tmp/video.mp4')

    @patch('yt_dl_manager.daemon.time.sleep')
    @patch('builtins.print')
    def test_run_keyboard_interrupt(self, mock_print, mock_sleep):
        """The daemon reports a graceful shutdown."""
        self.store.list_downloads.return_value = []
        mock_sleep.side_effect = KeyboardInterrupt()

        self.daemon.run()

        mock_print.assert_any_call('Daemon stopped.')


if __name__ == '__main__':
    unittest.main()
