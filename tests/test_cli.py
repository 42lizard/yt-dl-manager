"""Tests for maintenance behavior at the CLI adapter."""

import unittest
from argparse import Namespace
from datetime import datetime
from unittest.mock import MagicMock, patch

from yt_dl_manager.__main__ import (
    _handle_remove_failed,
    _print_downloads_table,
)
from yt_dl_manager.download_store import Download, DownloadStatus


class TestMaintenanceCli(unittest.TestCase):
    """Exercise confirmation and terminal rendering."""

    @patch('yt_dl_manager.__main__._confirm_removal', return_value=False)
    @patch('builtins.print')
    def test_remove_failed_can_be_cancelled(self, mock_print, _):
        """A rejected confirmation performs only the dry run."""
        store = MagicMock()
        store.remove_by_status.return_value = 2

        _handle_remove_failed(
            store,
            Namespace(dry_run=False, older_than=None),
        )

        store.remove_by_status.assert_called_once_with(
            DownloadStatus.FAILED,
            older_than_days=None,
            dry_run=True,
        )
        mock_print.assert_any_call('Operation cancelled.')

    @patch('builtins.print')
    def test_pending_downloads_are_rendered(self, mock_print):
        """The CLI adapter renders persisted Download facts."""
        _print_downloads_table(
            [Download(
                id=7,
                url='https://example.com/video',
                status=DownloadStatus.PENDING,
                requested_at=datetime.fromisoformat(
                    '2026-09-16T20:00:00+00:00'
                ),
                completed_at=None,
                filename=None,
                extractor=None,
                retries=1,
            )],
            'pending',
        )

        output = '\n'.join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn('PENDING DOWNLOADS (1 items)', output)
        self.assertIn('https://example.com/video', output)


if __name__ == '__main__':
    unittest.main()
