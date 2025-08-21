"""Textual-based Terminal User Interface for yt-dl-manager."""

import logging
import asyncio
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Header, Footer, Input, Label, Button
from textual.screen import ModalScreen
from textual.message import Message
from textual.binding import Binding
# from textual.widgets._data_table import RowKey

from .queue import Queue
from .download_utils import download_media
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
                TUIApp.StatusUpdate(gettext("✗ Error: %s") % str(e))
            )


class TUIApp(App):
    """Main TUI application class."""

    def on_startup(self) -> None:
        """Configure logging to show debug output on the console."""
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )

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
        self.queue = Queue()
        self.logger = logging.getLogger(__name__)

        # UI state management
        self.ui_state = {
            'status_message': "",
            'selected_pending_id': None,
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
            yield DataTable(id="pending-table")

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

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting in pending downloads table."""
        if event.data_table.id == "pending-table":
            self.logger.debug("Row highlighted: %s", event.row_key)
            if event.row_key.value is not None:
                try:
                    # Get the ID from the first column of the highlighted row
                    row_data = event.data_table.get_row(event.row_key)
                    if row_data:
                        self.ui_state['selected_pending_id'] = int(row_data[0])
                        self.logger.debug(
                            "Highlighted pending ID: %d", self.ui_state['selected_pending_id'])
                    else:
                        self.ui_state['selected_pending_id'] = None
                except (ValueError, IndexError) as e:
                    self.logger.debug("Error getting highlighted row: %s", e)
                    self.ui_state['selected_pending_id'] = None

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in pending downloads table."""
        if event.data_table.id == "pending-table":
            self.logger.debug("Row selected: %s", event.row_key)
            try:
                # Get the ID from the first column of the selected row
                row_data = event.data_table.get_row(event.row_key)
                if row_data:
                    self.ui_state['selected_pending_id'] = int(row_data[0])
                    self.logger.debug(
                        "Row selected, pending ID: %d", self.ui_state['selected_pending_id'])
                else:
                    self.ui_state['selected_pending_id'] = None
            except (ValueError, IndexError) as e:
                self.logger.debug("Error getting selected row: %s", e)
                self.ui_state['selected_pending_id'] = None

    async def refresh_data(self) -> None:
        """Refresh data in all tables."""
        await self.refresh_pending_downloads()
        await self.refresh_inprogress_downloads()
        await self.refresh_completed_downloads()

    async def refresh_pending_downloads(self) -> None:
        """Refresh the pending downloads table."""
        pending_table = self.query_one("#pending-table", DataTable)

        # Store current selection ID
        current_selection = self.ui_state['selected_pending_id']

        pending_table.clear()

        try:
            # Get pending downloads with full information
            pending_downloads = self.queue.db.get_downloads_by_status(
                'pending',
                sort_by='timestamp_requested',
                sort_order='DESC'
            )

            restore_row = None
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

                row_key = pending_table.add_row(
                    str(download.get('id', '')),
                    display_url,
                    download.get('status', ''),
                    requested,
                    str(download.get('retries', 0))
                )

                # Check if this was the previously selected row
                if current_selection and download.get('id') == current_selection:
                    restore_row = row_key

            # Restore selection if possible, or select first row
            if pending_downloads:
                self._restore_or_select_first_row(
                    pending_table, pending_downloads, restore_row)

        except (ValueError, RuntimeError) as e:
            self.logger.error("Error refreshing pending downloads: %s", e)

    def _restore_or_select_first_row(self, pending_table, pending_downloads, restore_row):
        """Restore previous selection or select first row."""
        if restore_row is not None:
            try:
                # Only try to move cursor if the restore_row is valid
                if restore_row in pending_table.rows:
                    pending_table.move_cursor(row=restore_row)
                    # Update selected_pending_id to match the restored selection
                    row_data = pending_table.get_row(restore_row)
                    if row_data:
                        self.ui_state['selected_pending_id'] = int(row_data[0])
                    return
            except (ValueError, IndexError, KeyError, TypeError):
                pass  # Fall through to select first row

        # If restore fails or no previous selection, select first row
        self._select_first_pending_row(pending_table, pending_downloads)

    def _select_first_pending_row(self, pending_table, pending_downloads):
        """Helper to select the first row in pending downloads."""
        try:
            # If we have rows and downloads, set the selected_pending_id to the first download's ID
            if pending_downloads and pending_table.row_count > 0:
                self.ui_state['selected_pending_id'] = pending_downloads[0].get('id')
                self.logger.debug(
                    "Selected first pending ID: %s", self.ui_state['selected_pending_id'])
                # Let the table handle cursor positioning naturally
        except (IndexError, KeyError, ValueError) as e:
            self.logger.debug("Error selecting first row: %s", e)

    async def refresh_inprogress_downloads(self) -> None:
        """Refresh the in-progress downloads table."""
        inprogress_table = self.query_one("#inprogress-table", DataTable)
        inprogress_table.clear()

        try:
            inprogress_downloads = self.queue.get_in_progress()
            for download in inprogress_downloads:
                # Format timestamp
                started = download.get('timestamp_requested', '')
                if started:
                    try:
                        dt = datetime.fromisoformat(
                            started.replace('Z', '+00:00'))
                        started = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, AttributeError):
                        started = str(started)[:16]

                # Truncate long URLs for display
                url = download.get('url', '')
                display_url = url[:50] + '...' if len(url) > 50 else url

                inprogress_table.add_row(
                    str(download.get('id', '')),
                    display_url,
                    download.get('status', ''),
                    started,
                    str(download.get('retries', 0))
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
                "Error refreshing completed downloads: %s", e)

    async def action_add_url(self) -> None:
        """Show modal to add new URL."""
        self.logger.debug("action_add_url called")
        await self.push_screen(URLInputModal(self))

    def _get_current_pending_selection(self):
        """Get the current selection from the pending table."""
        pending_table = self.query_one("#pending-table", DataTable)

        # First try the explicitly tracked selection
        if self.ui_state['selected_pending_id'] is not None:
            self.logger.debug(
                "Using tracked selection: %s", self.ui_state['selected_pending_id'])
            return self.ui_state['selected_pending_id']

        # Then try to get from current cursor position
        if pending_table.cursor_row is not None:
            try:
                row_data = pending_table.get_row(pending_table.cursor_row)
                if row_data and len(row_data) > 0:
                    selection_id = int(row_data[0])
                    self.logger.debug(
                        "Got selection from cursor: %s", selection_id)
                    return selection_id
            except (ValueError, IndexError) as e:
                self.logger.debug("Error getting cursor row: %s", e)

        # Finally, try to get the first row if table is not empty
        if pending_table.row_count > 0:
            try:
                first_row_key = list(pending_table.rows.keys())[0]
                row_data = pending_table.get_row(first_row_key)
                if row_data and len(row_data) > 0:
                    selection_id = int(row_data[0])
                    self.logger.debug(
                        "Got selection from first row: %s", selection_id)
                    return selection_id
            except (ValueError, IndexError) as e:
                self.logger.debug("Error getting first row: %s", e)

        return None

    async def action_start_download(self) -> None:
        """Start download for the selected pending item."""
        self.logger.debug("action_start_download called")

        selection_id = self._get_current_pending_selection()
        await self.show_status(f"Debug: Selected ID = {selection_id}")

        if selection_id is not None:
            try:
                # Get the full download info from database
                pending_downloads = self.queue.get_pending()
                self.logger.debug("Pending downloads: %s", pending_downloads)
                download_info = None
                for row_id, url, retries in pending_downloads:
                    if row_id == selection_id:
                        download_info = (row_id, url, retries)
                        break

                if download_info is None:
                    await self.show_status(gettext("✗ Download {} not found in pending queue").format(selection_id))
                    return

                row_id, url, retries = download_info

                # Start the download in a background task
                self.logger.debug(
                    "Starting download for row_id=%s, url=%s, retries=%s", row_id, url, retries)
                asyncio.create_task(
                    self._start_download_async(row_id, url, retries))
                await self.show_status(gettext("🚀 Starting download for ID {}...").format(row_id))

            except (ValueError, RuntimeError, KeyError, TypeError) as e:
                self.logger.error("Error starting download: %s", e)
                await self.show_status(gettext("✗ Error: %s") % str(e))
        else:
            await self.show_status(gettext("⚠ No item selected"))

    async def _start_download_async(self, download_id: int, url: str, retries: int) -> None:
        """Start download asynchronously in the background."""
        try:
            # Run the download in a thread to avoid blocking the UI
            def run_download():
                try:
                    download_media(self.queue, download_id, url, retries)
                    return True, None
                except (ValueError, RuntimeError) as exc:
                    return False, str(exc)
                # Do not catch Exception here to avoid W0718

            # Use run_in_executor to run the blocking download in a thread
            loop = asyncio.get_event_loop()
            success, error = await loop.run_in_executor(None, run_download)

            if success:
                await self.show_status(gettext("✓ Download completed for ID {}").format(download_id))
            else:
                await self.show_status(gettext("✗ Download failed for ID {}: {}").format(download_id, error))

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
