"""Tests for the web UI."""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from yt_dl_manager.web_ui import create_app, _format_timestamp, _truncate
from yt_dl_manager.queue import Queue
from tests.test_utils import create_test_schema


class TestWebUI(unittest.TestCase):
    """Test cases for the web UI."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        create_test_schema(self.test_db_path)

        self.config_patcher = patch('yt_dl_manager.queue.config')
        self.mock_config = self.config_patcher.start()
        mock_default_section = MagicMock()
        mock_default_section.__getitem__.return_value = self.test_db_path
        self.mock_config.__getitem__.return_value = mock_default_section

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up test fixtures."""
        self.config_patcher.stop()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def _csrf_post(self, url, data=None, **kwargs):
        """Send a POST request with CSRF token."""
        with self.client.session_transaction() as sess:
            sess['csrf_token'] = 'test-csrf-token'
        headers = kwargs.pop('headers', {})
        headers['X-CSRF-Token'] = 'test-csrf-token'
        return self.client.post(url, data=data, headers=headers, **kwargs)

    def _csrf_delete(self, url, **kwargs):
        """Send a DELETE request with CSRF token."""
        with self.client.session_transaction() as sess:
            sess['csrf_token'] = 'test-csrf-token'
        headers = kwargs.pop('headers', {})
        headers['X-CSRF-Token'] = 'test-csrf-token'
        return self.client.delete(url, headers=headers, **kwargs)

    def test_dashboard_loads(self):
        """Test that the dashboard loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

    def test_csrf_protection(self):
        """Test that POST requests without CSRF token are rejected."""
        response = self.client.post('/add', data={'url': 'https://example.com'})
        self.assertEqual(response.status_code, 403)

    def test_partial_pending_empty(self):
        """Test pending partial with no data."""
        response = self.client.get('/partials/pending')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No pending downloads', response.data)

    def test_partial_pending_with_data(self):
        """Test pending partial with data."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        response = self.client.get('/partials/pending')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'example.com', response.data)
        self.assertIn(b'Remove', response.data)

    def test_add_url(self):
        """Test adding a URL via POST."""
        response = self._csrf_post(
            '/add', data={'url': 'https://example.com/video'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'URL added to queue', response.data)
        queue = Queue(self.test_db_path)
        pending = queue.get_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0][1], 'https://example.com/video')

    def test_add_invalid_url(self):
        """Test adding an empty URL."""
        response = self._csrf_post('/add', data={'url': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'URL cannot be empty', response.data)

    def test_add_duplicate_url(self):
        """Test adding a duplicate URL shows appropriate message."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        response = self._csrf_post(
            '/add', data={'url': 'https://example.com/video'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'URL already exists in queue', response.data)

    def test_add_invalid_url_format(self):
        """Test adding an invalid URL format shows failure message."""
        response = self._csrf_post('/add', data={'url': 'ftp://example.com/file'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid URL', response.data)

    def test_start_download(self):
        """Test starting a download."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        with patch('yt_dl_manager.web_ui.download_media') as mock_download:
            with patch.object(self.app, 'executor') as mock_executor:
                response = self._csrf_post('/download/1')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Starting download', response.data)
                mock_executor.submit.assert_called_once()
                args = mock_executor.submit.call_args[0]
                self.assertEqual(args[0], mock_download)
                self.assertEqual(args[2], 1)
                self.assertEqual(args[3], "https://example.com/video")
                self.assertEqual(args[4], 0)
                # Status should still be pending because download_media is mocked
                pending = queue.get_pending()
                self.assertEqual(len(pending), 1)

    def test_start_download_not_pending(self):
        """Test starting a download that does not exist."""
        response = self._csrf_post('/download/999')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Download not found or not pending', response.data)

    def test_remove_download(self):
        """Test removing a download."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        response = self._csrf_delete('/remove/1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'')
        pending = queue.get_pending()
        self.assertEqual(len(pending), 0)

    def test_remove_nonexistent_download(self):
        """Test removing a download that does not exist."""
        response = self._csrf_delete('/remove/999')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Download not found', response.data)

    def test_remove_in_progress_download(self):
        """Test removing a download that is in progress."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        queue.start_download(1)
        response = self._csrf_delete('/remove/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'in progress', response.data)

    def test_retry_download(self):
        """Test retrying a download."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        queue.start_download(1)
        queue.complete_download(1, "/path/to/file.mp4", "youtube")
        response = self._csrf_post('/retry/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Download marked for retry', response.data)
        pending = queue.get_pending()
        self.assertEqual(len(pending), 1)

    def test_retry_nonexistent_download(self):
        """Test retrying a download that does not exist."""
        response = self._csrf_post('/retry/999')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Download not found', response.data)

    def test_partial_status(self):
        """Test status partial returns counts."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video1")
        queue.add_url("https://example.com/video2")
        response = self.client.get('/partials/status')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pending', response.data)
        self.assertIn(b'2', response.data)

    def test_partial_in_progress_empty(self):
        """Test in-progress partial with no data."""
        response = self.client.get('/partials/in-progress')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No downloads in progress', response.data)

    def test_partial_completed_empty(self):
        """Test completed partial with no data."""
        response = self.client.get('/partials/completed')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No completed downloads', response.data)

    def test_format_timestamp(self):
        """Test timestamp formatting helper."""
        self.assertEqual(
            _format_timestamp("2024-01-15T10:30:00+00:00"),
            "2024-01-15 10:30")
        self.assertEqual(_format_timestamp(""), "")
        self.assertEqual(_format_timestamp(None), "")
        self.assertEqual(_format_timestamp("invalid"), "invalid")

    def test_truncate(self):
        """Test text truncation helper."""
        self.assertEqual(_truncate("hello", 10), "hello")
        self.assertEqual(_truncate("hello world", 8), "hello...")
        self.assertEqual(_truncate("", 10), "")
        self.assertEqual(_truncate(None, 10), "")


if __name__ == '__main__':
    unittest.main()
