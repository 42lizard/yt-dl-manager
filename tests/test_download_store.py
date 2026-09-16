"""Behavior tests for the Download persistence interface."""

import csv
import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from yt_dl_manager.download_store import (
    Download,
    DownloadQuery,
    DownloadSort,
    DownloadStatus,
    DownloadStore,
)


class TestDownloadStore(unittest.TestCase):
    """Exercise persisted Download behavior through one interface."""

    def setUp(self):
        file_descriptor, self.db_path = tempfile.mkstemp()
        os.close(file_descriptor)
        self.addCleanup(os.unlink, self.db_path)
        self.store = DownloadStore(self.db_path)

    def _add(self, suffix='video'):
        success, _, download_id = self.store.add_url(
            f'https://example.com/{suffix}'
        )
        self.assertTrue(success)
        return download_id

    def _fail(self, download_id):
        claimed, _ = self.store.claim_pending_for_download(download_id)
        self.assertTrue(claimed)
        return self.store.record_failed_attempt(download_id, 1)

    def test_add_and_list_returns_download_values(self):
        """Persisted rows become immutable domain values."""
        download_id = self._add()

        downloads = self.store.list_downloads(
            DownloadQuery(DownloadStatus.PENDING)
        )

        self.assertEqual(len(downloads), 1)
        self.assertIsInstance(downloads[0], Download)
        self.assertEqual(downloads[0].id, download_id)
        self.assertIsInstance(downloads[0].requested_at, datetime)
        with self.assertRaises(AttributeError):
            downloads[0].url = 'https://example.com/changed'

    def test_invalid_and_duplicate_urls_are_rejected(self):
        """URL validation and uniqueness remain inside the store."""
        success, message, download_id = self.store.add_url('not-a-url')
        self.assertFalse(success)
        self.assertIn('Invalid URL', message)
        self.assertIsNone(download_id)

        existing_id = self._add()
        success, message, duplicate_id = self.store.add_url(
            'https://example.com/video'
        )
        self.assertFalse(success)
        self.assertIn('already exists', message)
        self.assertEqual(duplicate_id, existing_id)

    def test_claim_is_atomic_and_reports_current_download(self):
        """Only a pending Download can be claimed."""
        download_id = self._add()

        claimed, download = self.store.claim_pending_for_download(download_id)
        claimed_again, current = self.store.claim_pending_for_download(
            download_id
        )

        self.assertTrue(claimed)
        self.assertEqual(download.status, DownloadStatus.DOWNLOADING)
        self.assertFalse(claimed_again)
        self.assertEqual(current.status, DownloadStatus.DOWNLOADING)

    def test_failed_attempt_retries_then_fails(self):
        """Attempt counting and status selection are one transition."""
        download_id = self._add()

        self.store.claim_pending_for_download(download_id)
        retry = self.store.record_failed_attempt(download_id, 2)
        self.store.claim_pending_for_download(download_id)
        failed = self.store.record_failed_attempt(download_id, 2)

        self.assertEqual(retry.status, DownloadStatus.PENDING)
        self.assertEqual(retry.retries, 1)
        self.assertEqual(failed.status, DownloadStatus.FAILED)
        self.assertEqual(failed.retries, 2)

    def test_completion_normalizes_filename_and_timestamp(self):
        """Completion facts have stable Python types."""
        download_id = self._add()
        self.store.mark_downloaded(download_id, '/tmp/video.mp4', 'generic')

        download = self.store.list_downloads(
            DownloadQuery(DownloadStatus.DOWNLOADED)
        )[0]

        self.assertEqual(download.filename, Path('/tmp/video.mp4'))
        self.assertIsInstance(download.completed_at, datetime)
        self.assertEqual(download.extractor, 'generic')

    def test_status_counts_include_empty_states(self):
        """Every lifecycle state has a count."""
        downloading_id = self._add('downloading')
        failed_id = self._add('failed')
        self._fail(failed_id)
        self.store.claim_pending_for_download(downloading_id)

        counts = self.store.status_counts()

        self.assertEqual(counts[DownloadStatus.DOWNLOADING], 1)
        self.assertEqual(counts[DownloadStatus.FAILED], 1)
        self.assertEqual(counts[DownloadStatus.PENDING], 0)
        self.assertEqual(counts[DownloadStatus.DOWNLOADED], 0)

    def test_list_filters_and_sorts_with_domain_choices(self):
        """Callers do not pass SQLite column names."""
        first = self._add('first')
        second = self._add('second')
        self.store.claim_pending_for_download(first)
        self.store.record_failed_attempt(first, 3)

        downloads = self.store.list_downloads(DownloadQuery(
            status=DownloadStatus.PENDING,
            sort=DownloadSort.RETRIES,
            retries=1,
            descending=False,
        ))

        self.assertEqual([download.id for download in downloads], [first])
        self.assertNotEqual(first, second)

    def test_remove_by_status_supports_dry_run(self):
        """Dry runs count without deleting Downloads."""
        download_id = self._add()
        self._fail(download_id)

        preview = self.store.remove_by_status(
            DownloadStatus.FAILED,
            dry_run=True,
        )
        removed = self.store.remove_by_status(DownloadStatus.FAILED)

        self.assertEqual(preview, 1)
        self.assertEqual(removed, 1)
        self.assertEqual(
            self.store.list_downloads(DownloadQuery(DownloadStatus.FAILED)),
            [],
        )

    def test_remove_by_identity_and_url(self):
        """Both maintenance selection forms remove matching Downloads."""
        first = self._add('first')
        self._add('second')

        self.assertEqual(self.store.remove([first]), 1)
        self.assertEqual(self.store.remove_by_url('second'), 1)
        self.assertEqual(self.store.status_counts()[DownloadStatus.PENDING], 0)

    def test_reset_clears_completion_facts(self):
        """Redownload resets state and stored media facts."""
        download_id = self._add()
        self.store.mark_downloaded(download_id, '/tmp/video.mp4', 'generic')

        count = self.store.reset([download_id])
        download = self.store.list_downloads(
            DownloadQuery(DownloadStatus.PENDING)
        )[0]

        self.assertEqual(count, 1)
        self.assertIsNone(download.completed_at)
        self.assertIsNone(download.filename)
        self.assertEqual(download.retries, 0)

    def test_find_by_url_returns_downloads(self):
        """URL searches return the same Download representation."""
        self._add('needle')
        self._add('other')

        matches = self.store.find_by_url('needle')

        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0], Download)

    def test_cleanup_supports_preview_and_vacuum(self):
        """Database cleanup remains available through the store."""
        preview = self.store.cleanup_database(dry_run=True)
        result = self.store.cleanup_database()

        self.assertFalse(preview['vacuum_performed'])
        self.assertTrue(result['vacuum_performed'])

    def test_export_preserves_json_and_csv_formats(self):
        """Exports retain their documented serialized shapes."""
        self._add()

        json_data = json.loads(self.store.export_data('json'))
        csv_data = list(csv.DictReader(io.StringIO(
            self.store.export_data('csv')
        )))

        self.assertEqual(json_data[0]['status'], 'pending')
        self.assertEqual(csv_data[0]['status'], 'pending')

    def test_export_rejects_unknown_format(self):
        """Unsupported serialization remains a caller error."""
        with self.assertRaisesRegex(ValueError, 'json.*csv'):
            self.store.export_data('xml')


if __name__ == '__main__':
    unittest.main()
