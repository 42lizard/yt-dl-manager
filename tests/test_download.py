"""Tests for the Download lifecycle interface."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yt_dlp

from yt_dl_manager.download import DownloadLifecycle, DownloadOutcomeKind
from yt_dl_manager.download_store import DownloadStore


class TestDownloadLifecycle(unittest.TestCase):
    """Exercise lifecycle behavior through its public interface."""

    def setUp(self):
        file_descriptor, self.db_path = tempfile.mkstemp()
        os.close(file_descriptor)
        self.addCleanup(os.unlink, self.db_path)
        self.store = DownloadStore(self.db_path)
        self.downloads = DownloadLifecycle(self.store)

    def _add_download(self):
        success, _, download_id = self.store.add_url(
            'https://example.com/video'
        )
        self.assertTrue(success)
        return download_id

    @patch('yt_dl_manager.download.yt_dlp.YoutubeDL')
    def test_completed_download(self, mock_ytdl_class):
        """A successful attempt completes the Download."""
        download_id = self._add_download()
        ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = ytdl
        info = {'extractor': 'example', 'title': 'Video'}
        ytdl.extract_info.return_value = info
        ytdl.prepare_filename.return_value = '/tmp/video.mp4'

        with patch('yt_dl_manager.download.config') as mock_config:
            mock_config['DEFAULT']['target_folder'] = '/tmp'
            outcome = self.downloads.execute(download_id)

        self.assertEqual(outcome.kind, DownloadOutcomeKind.COMPLETED)
        self.assertEqual(outcome.filename, '/tmp/video.mp4')
        records = self.store.get_downloads_by_status('downloaded')
        self.assertEqual(records[0]['final_filename'], '/tmp/video.mp4')
        ytdl.extract_info.assert_called_once_with(
            'https://example.com/video',
            download=True,
        )

    @patch('yt_dl_manager.download.yt_dlp.YoutubeDL')
    def test_failed_attempts_retry_then_fail(self, mock_ytdl_class):
        """Failure counting and status selection are one persisted transition."""
        download_id = self._add_download()
        ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = ytdl
        ytdl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            'Network error'
        )

        first = self.downloads.execute(download_id)
        second = self.downloads.execute(download_id)
        third = self.downloads.execute(download_id)

        self.assertEqual(first.kind, DownloadOutcomeKind.RETRY_SCHEDULED)
        self.assertEqual(first.attempts, 1)
        self.assertEqual(second.kind, DownloadOutcomeKind.RETRY_SCHEDULED)
        self.assertEqual(second.attempts, 2)
        self.assertEqual(third.kind, DownloadOutcomeKind.FAILED)
        self.assertEqual(third.attempts, 3)
        records = self.store.get_downloads_by_status('failed')
        self.assertEqual(records[0]['retries'], 3)

    def test_not_available_reports_current_status(self):
        """A competing claim produces a non-mutating outcome."""
        download_id = self._add_download()
        claimed, _ = self.store.claim_pending_for_download(download_id)
        self.assertTrue(claimed)

        outcome = self.downloads.execute(download_id)

        self.assertEqual(outcome.kind, DownloadOutcomeKind.NOT_AVAILABLE)
        self.assertEqual(outcome.status, 'downloading')

    @patch('yt_dl_manager.download.yt_dlp.YoutubeDL')
    def test_unexpected_error_leaves_download_claimed(self, mock_ytdl_class):
        """Unexpected errors propagate without risking duplicate media."""
        download_id = self._add_download()
        ytdl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = ytdl
        ytdl.extract_info.side_effect = RuntimeError('unexpected')

        with self.assertRaisesRegex(RuntimeError, 'unexpected'):
            self.downloads.execute(download_id)

        records = self.store.get_downloads_by_status('downloading')
        self.assertEqual(records[0]['id'], download_id)

    def test_invalid_identity_is_rejected(self):
        """Invalid identities are programmer errors, not outcomes."""
        with self.assertRaisesRegex(ValueError, 'positive integer'):
            self.downloads.execute(0)


if __name__ == '__main__':
    unittest.main()
