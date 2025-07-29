"""Tests for TUI module."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from yt_dl_manager.tui import TUIApp, URLInputModal


class TestTUIApp(unittest.TestCase):
    """Test cases for TUI application."""

    def setUp(self):
        """Set up test environment with temporary database."""
        # Using context manager for resource allocation
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            self.db_path = temp_file.name

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @patch('yt_dl_manager.tui.Queue')
    def test_app_initialization(self, mock_queue_class):
        """Test TUI app initialization."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue

        app = TUIApp(recent_limit=5)
        self.assertEqual(app.recent_limit, 5)
        self.assertIsNotNone(app.queue)
        self.assertIsNotNone(app.logger)

    @patch('yt_dl_manager.tui.Queue')
    def test_app_initialization_default_limit(self, mock_queue_class):
        """Test TUI app initialization with default recent limit."""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue

        app = TUIApp()
        self.assertEqual(app.recent_limit, 10)

    @patch('yt_dl_manager.tui.Queue')
    def test_refresh_pending_downloads_empty(self, mock_queue_class):
        """Test refreshing pending downloads when queue is empty."""
        mock_queue = Mock()
        mock_db = Mock()
        mock_db.get_downloads_by_status.return_value = []
        mock_queue.db = mock_db
        mock_queue_class.return_value = mock_queue

        app = TUIApp()
        # Mock the query_one method to return a mock table
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)

        # Test the method without async context
        async def test_refresh():
            await app.refresh_pending_downloads()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_refresh())
        finally:
            loop.close()

        mock_table.clear.assert_called_once()
        mock_db.get_downloads_by_status.assert_called_once_with(
            'pending',
            sort_by='timestamp_requested',
            order='DESC'
        )

    @patch('yt_dl_manager.tui.Queue')
    def test_refresh_pending_downloads_with_data(self, mock_queue_class):
        """Test refreshing pending downloads with data."""
        mock_queue = Mock()
        mock_db = Mock()
        test_download = {
            'id': 1,
            'url': 'https://example.com/video',
            'status': 'pending',
            'timestamp_requested': '2023-01-01T12:00:00',
            'retries': 0
        }
        mock_db.get_downloads_by_status.return_value = [test_download]
        mock_queue.db = mock_db
        mock_queue_class.return_value = mock_queue

        app = TUIApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)

        async def test_refresh():
            await app.refresh_pending_downloads()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_refresh())
        finally:
            loop.close()

        mock_table.clear.assert_called_once()
        mock_table.add_row.assert_called_once()
        # Verify the row data contains expected values
        call_args = mock_table.add_row.call_args[0]
        self.assertEqual(call_args[0], '1')  # ID
        self.assertEqual(call_args[1], 'https://example.com/video')  # URL
        self.assertEqual(call_args[2], 'pending')  # Status

    @patch('yt_dl_manager.tui.Queue')
    def test_refresh_completed_downloads_empty(self, mock_queue_class):
        """Test refreshing completed downloads when empty."""
        mock_queue = Mock()
        mock_db = Mock()
        mock_db.get_downloads_by_status.return_value = []
        mock_queue.db = mock_db
        mock_queue_class.return_value = mock_queue

        app = TUIApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)

        async def test_refresh():
            await app.refresh_completed_downloads()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_refresh())
        finally:
            loop.close()

        mock_table.clear.assert_called_once()
        mock_db.get_downloads_by_status.assert_called_once_with(
            'downloaded',
            limit=10,
            sort_by='timestamp_downloaded',
            sort_order='DESC'
        )

    def test_status_update_message(self):
        """Test StatusUpdate message creation."""
        message = TUIApp.StatusUpdate("Test message")
        self.assertEqual(message.message, "Test message")

    def test_refresh_data_message(self):
        """Test RefreshData message creation."""
        message = TUIApp.RefreshData()
        self.assertIsNotNone(message)


class TestURLInputModal(unittest.TestCase):
    """Test cases for URL input modal."""

    def setUp(self):
        """Set up test environment."""
        self.mock_app = Mock()
        self.mock_app.queue = Mock()

    def test_modal_initialization(self):
        """Test modal initialization."""
        modal = URLInputModal(self.mock_app)
        self.assertEqual(modal.app_ref, self.mock_app)

    @patch('yt_dl_manager.tui.Queue')
    def test_add_url_success(self, _):
        """Test successful URL addition."""
        mock_queue = Mock()
        mock_queue.add_url.return_value = (True, "URL added", 1)
        self.mock_app.queue = mock_queue

        modal = URLInputModal(self.mock_app)

        async def test_add():
            await modal.add_url_to_queue("https://example.com/video")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_add())
        finally:
            loop.close()

        mock_queue.add_url.assert_called_once_with("https://example.com/video")
        # Verify messages were posted
        self.assertEqual(self.mock_app.post_message.call_count, 2)

    @patch('yt_dl_manager.tui.Queue')
    def test_add_url_failure(self, _):
        """Test URL addition failure."""
        mock_queue = Mock()
        mock_queue.add_url.return_value = (False, "URL already exists", None)
        self.mock_app.queue = mock_queue

        modal = URLInputModal(self.mock_app)

        async def test_add():
            await modal.add_url_to_queue("https://example.com/duplicate")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_add())
        finally:
            loop.close()

        mock_queue.add_url.assert_called_once_with(
            "https://example.com/duplicate")
        # Should post warning message and refresh
        self.assertEqual(self.mock_app.post_message.call_count, 2)

    def test_add_url_exception(self):
        """Test URL addition with exception."""
        mock_queue = Mock()
        mock_queue.add_url.side_effect = ValueError("Invalid URL")
        self.mock_app.queue = mock_queue

        modal = URLInputModal(self.mock_app)

        async def test_add():
            await modal.add_url_to_queue("invalid-url")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_add())
        finally:
            loop.close()

        mock_queue.add_url.assert_called_once_with("invalid-url")
        # Should post error message
        self.mock_app.post_message.assert_called_once()


if __name__ == '__main__':
    unittest.main()
