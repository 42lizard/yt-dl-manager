"""Textual-based Terminal User Interface for yt-dl-manager."""

import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Header, Footer, Input, Label, Button
from textual.screen import ModalScreen
from textual.message import Message
from textual.binding import Binding

from .queue import Queue
from .i18n import _ as gettext


class URLInputModal(ModalScreen):
    """Modal screen for entering new URLs."""

    # Static bindings - will be updated in __init__
    BINDINGS = []

    def __init__(self, app_ref):
        """Initialize the modal with reference to parent app."""
        super().__init__()
        self.app_ref = app_ref
        # Update class bindings with translations
        URLInputModal.BINDINGS = [
            Binding("escape", "dismiss", gettext("Cancel")),
        ]

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="url-input-modal"):
            yield Label(gettext("Enter URL to download:"), id="url-label")
            yield Input(placeholder="https://...", id="url-input")
            with Horizontal(id="button-row"):
                yield Button(gettext("Add to Queue"), variant="primary", id="add-button")
                yield Button(gettext("Cancel"), variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Focus the input field when modal is mounted."""
        self.query_one("#url-input").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add-button":
            url_input = self.query_one("#url-input", Input)
            url = url_input.value.strip()
            if url:
                await self.add_url_to_queue(url)
            self.dismiss()
        elif event.button.id == "cancel-button":
            self.dismiss()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        url = event.value.strip()
        if url:
            await self.add_url_to_queue(url)
        self.dismiss()

    async def add_url_to_queue(self, url: str) -> None:
        """Add URL to the download queue."""
        try:
            success, message, _ = self.app_ref.queue.add_url(url)
            if success:
                self.app_ref.post_message(
                    TUIApp.StatusUpdate(gettext("✓ Added: {}").format(url))
                )
            else:
                self.app_ref.post_message(
                    TUIApp.StatusUpdate(gettext("⚠ {}").format(message))
                )
            # Refresh the data after adding URL
            self.app_ref.post_message(TUIApp.RefreshData())
        except (ValueError, RuntimeError) as e:
            self.app_ref.post_message(
                TUIApp.StatusUpdate(gettext("✗ Error: {}").format(str(e)))
            )


class TUIApp(App):
    """Main TUI application class."""

    CSS = """
    #pending-table {
        height: 60%;
    }
    
    #completed-table {
        height: 40%;
    }
    
    #url-input-modal {
        align: center middle;
        width: 60;
        height: 10;
        background: $surface;
        border: thick $primary;
    }
    
    #url-label {
        text-align: center;
        margin: 1;
    }
    
    #url-input {
        margin: 1;
    }
    
    #button-row {
        align: center middle;
        margin: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    .status-message {
        background: $primary;
        color: $text;
        text-align: center;
        margin: 1 0;
    }
    """

    TITLE = "yt-dl-manager TUI"  # Will be overridden in __init__
    # Will be overridden in __init__
    SUB_TITLE = "Terminal User Interface for YouTube Download Manager"

    BINDINGS = [
        Binding("a", "add_url", "Add URL"),  # Will be updated in __init__
        Binding("r", "refresh", "Refresh"),  # Will be updated in __init__
        Binding("q", "quit", "Quit"),  # Will be updated in __init__
    ]

    class StatusUpdate(Message):
        """Message to update status display."""

        def __init__(self, message: str):
            self.message = message
            super().__init__()

    class RefreshData(Message):
        """Message to refresh data tables."""

    def __init__(self, recent_limit: int = 10):
        """Initialize the TUI app.

        Args:
            recent_limit: Number of recent completed downloads to show
        """
        super().__init__()
        self.recent_limit = recent_limit
        self.queue = Queue()
        self.logger = logging.getLogger(__name__)
        self.status_message = ""

        # Set translated title and subtitle
        self.title = gettext("yt-dl-manager TUI")
        self.sub_title = gettext(
            "Terminal User Interface for YouTube Download Manager")

        # Update class bindings with translations
        TUIApp.BINDINGS = [
            Binding("a", "add_url", gettext("Add URL")),
            Binding("r", "refresh", gettext("Refresh")),
            Binding("q", "quit", gettext("Quit")),
        ]

    def compose(self) -> ComposeResult:
        """Compose the main layout."""
        yield Header()

        if self.status_message:
            yield Label(self.status_message, classes="status-message")

        with Vertical():
            yield Label(gettext("📥 Pending Downloads"), id="pending-label")
            yield DataTable(id="pending-table")

            yield Label(
                gettext("✅ Recent Completed Downloads (last {})").format(
                    self.recent_limit),
                id="completed-label")
            yield DataTable(id="completed-table")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables when app is mounted."""
        await self.setup_tables()
        await self.refresh_data()

    async def setup_tables(self) -> None:
        """Set up the data tables with columns."""
        pending_table = self.query_one("#pending-table", DataTable)
        pending_table.add_columns(
            gettext("ID"), gettext("URL"), gettext("Status"),
            gettext("Requested"), gettext("Retries"))

        completed_table = self.query_one("#completed-table", DataTable)
        completed_table.add_columns(
            gettext("ID"), gettext("URL"), gettext("Downloaded"), gettext("File"))

    async def refresh_data(self) -> None:
        """Refresh data in both tables."""
        await self.refresh_pending_downloads()
        await self.refresh_completed_downloads()

    async def refresh_pending_downloads(self) -> None:
        """Refresh the pending downloads table."""
        pending_table = self.query_one("#pending-table", DataTable)
        pending_table.clear()

        try:
            # Get pending downloads with full information
            pending_downloads = self.queue.db.get_downloads_by_status(
                'pending',
                sort_by='timestamp_requested',
                order='DESC'
            )
            for download in pending_downloads:
                # Format timestamp
                requested = download.get('timestamp_requested', '')
                if requested:
                    try:
                        dt = datetime.fromisoformat(
                            requested.replace('Z', '+00:00'))
                        requested = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, AttributeError):
                        requested = str(requested)[:16]

                # Truncate long URLs for display
                url = download.get('url', '')
                display_url = url[:50] + '...' if len(url) > 50 else url

                pending_table.add_row(
                    str(download.get('id', '')),
                    display_url,
                    download.get('status', ''),
                    requested,
                    str(download.get('retries', 0))
                )
        except (ValueError, RuntimeError) as e:
            self.logger.error("Error refreshing pending downloads: %s", str(e))

    async def refresh_completed_downloads(self) -> None:
        """Refresh the completed downloads table."""
        completed_table = self.query_one("#completed-table", DataTable)
        completed_table.clear()

        try:
            # Get completed downloads using existing database methods
            downloads = self.queue.db.get_downloads_by_status(
                'downloaded',
                limit=self.recent_limit,
                sort_by='timestamp_downloaded',
                sort_order='DESC'
            )

            for download in downloads:
                # Format timestamp
                downloaded = download.get('timestamp_downloaded', '')
                if downloaded:
                    try:
                        dt = datetime.fromisoformat(
                            downloaded.replace('Z', '+00:00'))
                        downloaded = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, AttributeError):
                        downloaded = str(downloaded)[:16]

                # Truncate long URLs and filenames for display
                url = download.get('url', '')
                display_url = url[:40] + '...' if len(url) > 40 else url

                filename = download.get('final_filename', '')
                if filename:
                    # Show the full path to the file
                    display_filename = filename[:60] + \
                        '...' if len(filename) > 60 else filename
                else:
                    display_filename = 'N/A'

                completed_table.add_row(
                    str(download.get('id', '')),
                    display_url,
                    downloaded,
                    display_filename
                )
        except (ValueError, RuntimeError) as e:
            self.logger.error(
                "Error refreshing completed downloads: %s", str(e))

    async def action_add_url(self) -> None:
        """Show modal to add new URL."""
        await self.push_screen(URLInputModal(self))

    async def action_refresh(self) -> None:
        """Manually refresh all data."""
        await self.refresh_data()
        await self.show_status(gettext("🔄 Data refreshed"))

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    async def on_status_update(self, message: StatusUpdate) -> None:
        """Handle status update messages."""
        await self.show_status(message.message)

    async def on_refresh_data(self, _: RefreshData) -> None:
        """Handle refresh data messages."""
        await self.refresh_data()

    async def show_status(self, message: str) -> None:
        """Show a temporary status message."""
        self.status_message = message
        # Note: In a real implementation, you might want to add a temporary
        # status bar or notification. For now, we'll just log it.
        self.logger.info("Status: %s", message)


def main(recent_limit: int = 10):
    """Main entry point for the TUI.

    Args:
        recent_limit: Number of recent completed downloads to show
    """
    app = TUIApp(recent_limit=recent_limit)
    app.run()


if __name__ == "__main__":
    main()
