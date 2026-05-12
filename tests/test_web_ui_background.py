"""Tests for web UI background download submission."""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from yt_dl_manager.web_ui import create_app, download_media
from yt_dl_manager.queue import Queue
from tests.test_utils import create_test_schema


class TestWebUIBackground(unittest.TestCase):
    """Test cases for background download handling."""

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

    def test_download_submitted_to_executor(self):
        """Test that download is submitted to the executor."""
        queue = Queue(self.test_db_path)
        queue.add_url("https://example.com/video")
        with patch.object(self.app, 'executor') as mock_executor:
            response = self._csrf_post('/download/1')
            self.assertEqual(response.status_code, 200)
            mock_executor.submit.assert_called_once()
            args = mock_executor.submit.call_args[0]
            self.assertEqual(args[0], download_media)
            self.assertEqual(args[2], 1)
            self.assertEqual(args[3], "https://example.com/video")
            self.assertEqual(args[4], 0)


if __name__ == '__main__':
    unittest.main()
