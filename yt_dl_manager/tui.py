"""Textual-based Terminal User Interface for yt-dl-manager."""

import logging
import asyncio
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Header, Footer, Input, Label, Button
from textual.screen import ModalScreen
from textual.message import Message
from textual.binding import Binding
# from textual.widgets._data_table import RowKey

from .download_store import (
    DownloadQuery,
    DownloadSort,
    DownloadStatus,
    DownloadStore,
)
from .config import load_paths
from .download import DownloadLifecycle, DownloadOutcomeKind
from .i18n import _ as gettext


class URLInputModal(ModalScreen):
    """Modal screen for entering new URLs."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, app_ref):
        """Initialize the modal with reference to parent app."""
        super().__init__()
        self.app_ref = app_ref

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
            success, message, _ = self.app_ref.store.add_url(url)
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
                TUIApp.StatusUpdate(gettext("✗ Error: %s") % str(e))
            )


class TUIApp(App):
    """Main TUI application class."""

    CSS = """
    #pending-table {
        height: 33%;
    }

    #inprogress-table {
        height: 33%;
    }

    #completed-table {
        height: 34%;
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
        Binding("a", "add_url", "Add URL", show=True, priority=True),
        Binding("d", "start_download", "Download", show=True, priority=True),
        Binding("r", "refresh", "Refresh", show=True, priority=True),
        Binding("q", "quit", "Quit", show=True, priority=True),
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
        paths = load_paths('database_path', 'target_folder')
        self.store = DownloadStore(paths['database_path'])
        self.downloads = DownloadLifecycle(self.store, paths['target_folder'])
        self.logger = logging.getLogger(__name__)

        # UI state management
        self.ui_state = {
            'status_message': "",
            'last_status_task': None
        }

        # Set translated title and subtitle
        self.title = gettext("yt-dl-manager TUI")
        self.sub_title = gettext(
            "Terminal User Interface for YouTube Download Manager")

    def compose(self) -> ComposeResult:
        """Compose the main layout."""
        yield Header()

        with Vertical():
            yield Label("", id="status-label", classes="status-message")
            yield Label(gettext("📥 Pending Downloads (use arrow keys to select, 'd' to download)"), id="pending-label")
            yield DataTable(id="pending-table", cursor_type="row")

            yield Label(gettext("⏳ In Progress"), id="inprogress-label")
            yield DataTable(id="inprogress-table")

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
        # Start periodic auto-refresh every 2 seconds
        self.set_interval(2.0, self.refresh_data)
        # Focus the pending table so user can select items
        pending_table = self.query_one("#pending-table", DataTable)
        pending_table.focus()

    async def setup_tables(self) -> None:
        """Set up the data tables with columns."""
        pending_table = self.query_one("#pending-table", DataTable)
        pending_table.add_columns(
            gettext("ID"), gettext("URL"), gettext("Status"),
            gettext("Requested"), gettext("Retries"))

        # Allow pending table to be focused for selection
        pending_table.can_focus = True

        inprogress_table = self.query_one("#inprogress-table", DataTable)
        inprogress_table.add_columns(
            gettext("ID"), gettext("URL"), gettext("Status"),
            gettext("Started"), gettext("Retries")
        )
        inprogress_table.can_focus = False

        completed_table = self.query_one("#completed-table", DataTable)
        completed_table.add_columns(
            gettext("ID"), gettext("URL"), gettext("Downloaded"), gettext("File"))

        # Make sure tables don't interfere with app-level key bindings
        completed_table.can_focus = False

    async def on_key(self, event) -> None:
        """Handle key press events."""
        self.logger.debug("Key pressed: %s", event.key)

        if event.key == "d":
            self.logger.debug("D key detected, calling action_start_download")
            await self.action_start_download()
            event.prevent_default()
        elif event.key == "a":
            self.logger.debug("A key detected, calling action_add_url")
            await self.action_add_url()
            event.prevent_default()
        elif event.key == "r":
            self.logger.debug("R key detected, calling action_refresh")
            await self.action_refresh()
            event.prevent_default()
        elif event.key == "q":
            self.logger.debug("Q key detected, calling action_quit")
            await self.action_quit()
            event.prevent_default()

    async def refresh_data(self) -> None:
        """Refresh data in all tables."""
        await self.refresh_pending_downloads()
        await self.refresh_inprogress_downloads()
        await self.refresh_completed_downloads()

    async def refresh_pending_downloads(self) -> None:
        """Refresh the pending downloads table."""
        pending_table = self.query_one("#pending-table", DataTable)

        # Store current selection ID
        current_selection = self._get_current_pending_selection()

        pending_table.clear()

        try:
            # Get pending downloads with full information
            pending_downloads = self.store.list_downloads(
                DownloadQuery(DownloadStatus.PENDING)
            )

            restore_row = 0
            for index, download in enumerate(pending_downloads):
                requested = (
                    download.requested_at.strftime('%Y-%m-%d %H:%M')
                    if download.requested_at else ''
                )

                # Truncate long URLs for display
                url = download.url
                display_url = url[:50] + '...' if len(url) > 50 else url

                pending_table.add_row(
                    str(download.id),
                    display_url,
                    download.status.value,
                    requested,
                    str(download.retries),
                    key=str(download.id),
                )

                # Check if this was the previously selected row
                if current_selection and download.id == current_selection:
                    restore_row = index

            # Restore selection if possible, or select first row
            if pending_downloads:
                pending_table.move_cursor(row=restore_row)

        except (ValueError, RuntimeError) as e:
            self.logger.error("Error refreshing pending downloads: %s", e)

    async def refresh_inprogress_downloads(self) -> None:
        """Refresh the in-progress downloads table."""
        inprogress_table = self.query_one("#inprogress-table", DataTable)
        inprogress_table.clear()

        try:
            inprogress_downloads = self.store.list_downloads(
                DownloadQuery(DownloadStatus.DOWNLOADING)
            )
            for download in inprogress_downloads:
                started = (
                    download.requested_at.strftime('%Y-%m-%d %H:%M')
                    if download.requested_at else ''
                )

                # Truncate long URLs for display
                url = download.url
                display_url = url[:50] + '...' if len(url) > 50 else url

                inprogress_table.add_row(
                    str(download.id),
                    display_url,
                    download.status.value,
                    started,
                    str(download.retries),
                )
        except (ValueError, RuntimeError) as e:
            self.logger.error(
                "Error refreshing in-progress downloads: %s", e)

    async def refresh_completed_downloads(self) -> None:
        """Refresh the completed downloads table."""
        completed_table = self.query_one("#completed-table", DataTable)
        completed_table.clear()

        try:
            # Get completed downloads using existing database methods
            downloads = self.store.list_downloads(DownloadQuery(
                status=DownloadStatus.DOWNLOADED,
                limit=self.recent_limit,
                sort=DownloadSort.COMPLETED,
            ))

            for download in downloads:
                downloaded = (
                    download.completed_at.strftime('%Y-%m-%d %H:%M')
                    if download.completed_at else ''
                )

                # Truncate long URLs and filenames for display
                url = download.url
                display_url = url[:40] + '...' if len(url) > 40 else url

                filename = str(download.filename) if download.filename else ''
                if filename:
                    # Show the full path to the file
                    display_filename = filename[:60] + \
                        '...' if len(filename) > 60 else filename
                else:
                    display_filename = 'N/A'

                completed_table.add_row(
                    str(download.id),
                    display_url,
                    downloaded,
                    display_filename
                )
        except (ValueError, RuntimeError) as e:
            self.logger.error(
                "Error refreshing completed downloads: %s", e)

    async def action_add_url(self) -> None:
        """Show modal to add new URL."""
        self.logger.debug("action_add_url called")
        await self.push_screen(URLInputModal(self))

    def _get_current_pending_selection(self):
        """Get the current selection from the pending table."""
        pending_table = self.query_one("#pending-table", DataTable)

        if pending_table.row_count:
            return int(pending_table.get_row_at(pending_table.cursor_row)[0])
        return None

    async def action_start_download(self) -> None:
        """Start download for the selected pending item."""
        self.logger.debug("action_start_download called")

        selection_id = self._get_current_pending_selection()

        if selection_id is not None:
            try:
                self.logger.debug(
                    "Starting download for ID %s", selection_id)
                asyncio.create_task(self._start_download_async(selection_id))
                await self.show_status(
                    gettext("🚀 Starting download for ID {}...").format(
                        selection_id
                    )
                )

            except (ValueError, RuntimeError, KeyError, TypeError) as e:
                self.logger.error("Error starting download: %s", e)
                await self.show_status(gettext("✗ Error: %s") % str(e))
        else:
            await self.show_status(gettext("⚠ No item selected"))

    async def _start_download_async(self, download_id: int) -> None:
        """Start download asynchronously in the background."""
        try:
            loop = asyncio.get_event_loop()
            outcome = await loop.run_in_executor(
                None,
                self.downloads.execute,
                download_id,
            )

            if outcome.kind is DownloadOutcomeKind.COMPLETED:
                message = gettext("✓ Download completed for ID {}").format(
                    download_id
                )
            elif outcome.kind is DownloadOutcomeKind.RETRY_SCHEDULED:
                message = gettext(
                    "⚠ Download failed for ID {}; retry scheduled: {}"
                ).format(download_id, outcome.error)
            elif outcome.kind is DownloadOutcomeKind.FAILED:
                message = gettext("✗ Download failed for ID {}: {}").format(
                    download_id,
                    outcome.error,
                )
            else:
                message = gettext("⚠ Download {} is not available").format(
                    download_id
                )
            await self.show_status(message)

            # Refresh data to show updated status
            await self.refresh_data()

        except (ValueError, RuntimeError) as exc:
            self.logger.error("Error in background download: %s", exc)
            await self.show_status(gettext("✗ Download error for ID %s: %s") % (download_id, str(exc)))
        # Do not catch Exception here to avoid W0718

    async def action_refresh(self) -> None:
        """Manually refresh all data."""
        self.logger.debug("action_refresh called")
        await self.refresh_data()
        await self.show_status(gettext("🔄 Data refreshed"))

    async def action_quit(self) -> None:
        """Quit the application."""
        self.logger.debug("action_quit called")
        self.exit()

    async def on_status_update(self, message: StatusUpdate) -> None:
        """Handle status update messages."""
        await self.show_status(message.message)

    async def on_refresh_data(self, _: RefreshData) -> None:
        """Handle refresh data messages."""
        await self.refresh_data()

    async def show_status(self, message: str) -> None:
        """Show a temporary status message."""
        self.ui_state['status_message'] = message
        self.logger.info("Status: %s", message)

        # Update the status label
        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update(message)

            # Cancel previous auto-clear task
            if self.ui_state['last_status_task']:
                self.ui_state['last_status_task'].cancel()

            # Auto-clear status after 3 seconds
            self.ui_state['last_status_task'] = asyncio.create_task(
                self._clear_status_after_delay())
        except (ValueError, KeyError, RuntimeError) as exc:
            self.logger.debug("Error updating status label: %s", exc)

    async def _clear_status_after_delay(self):
        """Clear status message after a delay."""
        try:
            await asyncio.sleep(3)
            status_label = self.query_one("#status-label", Label)
            status_label.update("")
        except asyncio.CancelledError:
            pass
        except (ValueError, KeyError, RuntimeError) as exc:
            self.logger.debug("Error clearing status: %s", exc)
        # Only catch specific exceptions, not Exception


def main(recent_limit: int = 10):
    """Main entry point for the TUI.

    Args:
        recent_limit: Number of recent completed downloads to show
    """
    app = TUIApp(recent_limit=recent_limit)
    app.run()


if __name__ == "__main__":
    main()
