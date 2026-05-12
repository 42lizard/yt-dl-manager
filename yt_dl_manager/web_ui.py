"""Web UI for yt-dl-manager using Flask and HTMX."""

import atexit
import logging
import os
import secrets
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, abort, current_app, render_template, request, session

from .queue import Queue
from .download_utils import download_media
from .i18n import _

logger = logging.getLogger(__name__)


def _format_timestamp(ts_str):
    """Parse ISO format timestamp and return formatted string.

    Args:
        ts_str (str): ISO format timestamp string.

    Returns:
        str: Formatted timestamp or empty string on error.
    """
    if not ts_str:
        return ""
    try:
        ts_clean = ts_str.replace("Z", "+00:00")
        dt_obj = datetime.fromisoformat(ts_clean)
        return dt_obj.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(ts_str)


def _truncate(text, length):
    """Truncate text to specified length with ellipsis.

    Args:
        text (str): The text to truncate.
        length (int): Maximum length.

    Returns:
        str: Truncated text.
    """
    if not text:
        return ""
    if len(text) > length:
        return text[:length - 3] + "..."
    return text


def _render_with_toast(fragment_template, toast_message, **kwargs):
    """Render an HTML fragment plus an OOB toast notification.

    Args:
        fragment_template (str): Template path for the fragment.
        toast_message (str): Message for the toast.
        **kwargs: Additional template variables.

    Returns:
        str: Concatenated HTML fragment and toast.
    """
    fragment = render_template(fragment_template, **kwargs)
    toast = render_template("partials/toast.html", message=toast_message)
    return fragment + toast


def _prepare_downloads(downloads, url_length=50, ts_field="timestamp_requested"):
    """Format timestamps and truncate URLs for display.

    Args:
        downloads (list): List of download dictionaries.
        url_length (int): Maximum URL display length.
        ts_field (str): Timestamp field to format.

    Returns:
        list: The same list with display fields added.
    """
    for download in downloads:
        download["timestamp_display"] = _format_timestamp(
            download.get(ts_field)
        )
        download["url_display"] = _truncate(
            download.get("url", ""), url_length
        )
    return downloads


def _get_pending_display(queue):
    """Retrieve and format pending downloads for templates.

    Args:
        queue (Queue): The queue instance.

    Returns:
        list: Formatted pending downloads.
    """
    downloads = queue.get_downloads_by_status(
        "pending", sort_by="timestamp_requested", order="DESC"
    )
    return _prepare_downloads(downloads, url_length=50)


def _validate_csrf():
    """Validate CSRF token for state-changing requests."""
    token = session.get("csrf_token")
    submitted = request.headers.get("X-CSRF-Token")
    if not token or token != submitted:
        abort(403)


def _setup_csrf(app):
    """Configure CSRF token generation and template injection."""
    @app.before_request
    def ensure_csrf_token():
        """Generate a CSRF token if one does not exist."""
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)

    @app.context_processor
    def inject_csrf_token():
        """Make CSRF token available to all templates."""
        return {"csrf_token": session.get("csrf_token", "")}


def _dashboard():
    """Render the main dashboard page."""
    return render_template("dashboard.html")


def _partial_pending():
    """Render the pending downloads partial."""
    queue = Queue()
    downloads = _get_pending_display(queue)
    return render_template("partials/pending.html", downloads=downloads)


def _partial_in_progress():
    """Render the in-progress downloads partial."""
    queue = Queue()
    downloads = queue.get_in_progress()
    _prepare_downloads(downloads, url_length=50)
    return render_template("partials/in_progress.html", downloads=downloads)


def _partial_completed():
    """Render the completed downloads partial."""
    queue = Queue()
    downloads = queue.get_downloads_by_status(
        "downloaded",
        limit=10,
        sort_by="timestamp_downloaded",
        order="DESC",
    )
    _prepare_downloads(downloads, url_length=40, ts_field="timestamp_downloaded")
    for download in downloads:
        download["filename_display"] = _truncate(
            download.get("final_filename", ""), 60
        )
    return render_template("partials/completed.html", downloads=downloads)


def _partial_status():
    """Render the status bar partial."""
    queue = Queue()
    status_counts = queue.get_queue_status()
    return render_template(
        "partials/status_bar.html", status_counts=status_counts
    )


def _add_url():
    """Add a URL to the download queue."""
    _validate_csrf()
    queue = Queue()
    url = request.form.get("url", "").strip()
    if not url:
        return _render_with_toast(
            "partials/pending.html",
            _("URL cannot be empty."),
            downloads=_get_pending_display(queue),
        )
    try:
        result = queue.add_url(url)
    except ValueError as err:
        logger.error("Failed to add URL: %s", err)
        return _render_with_toast(
            "partials/pending.html",
            _("Failed to add URL."),
            downloads=_get_pending_display(queue),
        )
    if not result[0]:
        if "already exists" in result[1]:
            message = _("URL already exists in queue.")
        elif "Invalid URL" in result[1]:
            message = _(
                "Invalid URL. Only http(s) URLs are allowed.")
        else:
            message = _("Failed to add URL.")
        return _render_with_toast(
            "partials/pending.html",
            message,
            downloads=_get_pending_display(queue),
        )
    downloads = _get_pending_display(queue)
    return _render_with_toast(
        "partials/pending.html",
        _("URL added to queue."),
        downloads=downloads,
    )


def _start_download(download_id):
    """Start a download in a background thread."""
    _validate_csrf()
    queue = Queue()
    download = queue.get_download_by_id(download_id)
    if not download or download.get("status") != "pending":
        return render_template(
            "partials/toast.html",
            message=_("Download not found or not pending."),
        )
    current_app.executor.submit(
        download_media,
        queue,
        download_id,
        download["url"],
        download["retries"],
    )
    return render_template(
        "partials/toast.html",
        message=_("Starting download..."),
    )


def _retry_download(download_id):
    """Retry a completed or failed download."""
    _validate_csrf()
    queue = Queue()
    try:
        queue.reset_to_pending(download_id)
        return render_template(
            "partials/toast.html",
            message=_("Download marked for retry."),
        )
    except ValueError:
        logger.error("Failed to retry download %d: not found", download_id)
        return render_template(
            "partials/toast.html",
            message=_("Download not found."),
        )


def _remove_download(download_id):
    """Remove a download from the queue."""
    _validate_csrf()
    queue = Queue()
    try:
        queue.remove_by_id(download_id)
    except ValueError:
        logger.error("Failed to remove download %d: not found", download_id)
        return render_template(
            "partials/toast.html",
            message=_("Download not found."),
        )
    except RuntimeError:
        logger.error(
            "Failed to remove download %d: in progress", download_id)
        return render_template(
            "partials/toast.html",
            message=_("Cannot remove a download that is in progress."),
        )
    return "", 200


def _register_routes(app):
    """Register all Flask application routes."""
    app.add_url_rule("/", view_func=_dashboard)
    app.add_url_rule("/partials/pending", view_func=_partial_pending)
    app.add_url_rule("/partials/in-progress", view_func=_partial_in_progress)
    app.add_url_rule("/partials/completed", view_func=_partial_completed)
    app.add_url_rule("/partials/status", view_func=_partial_status)
    app.add_url_rule("/add", view_func=_add_url, methods=["POST"])
    app.add_url_rule(
        "/download/<int:download_id>",
        view_func=_start_download,
        methods=["POST"],
    )
    app.add_url_rule(
        "/retry/<int:download_id>",
        view_func=_retry_download,
        methods=["POST"],
    )
    app.add_url_rule(
        "/remove/<int:download_id>",
        view_func=_remove_download,
        methods=["DELETE"],
    )


def _setup_cache_control(app):
    """Add no-cache headers to all HTML responses."""
    @app.after_request
    def add_cache_control_headers(response):
        """Prevent browser caching of HTML responses."""
        if response.content_type and "text/html" in response.content_type:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


def create_app():
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = os.environ.get(
        "YT_DL_MANAGER_SECRET_KEY"
    ) or secrets.token_hex(32)
    if not os.environ.get("YT_DL_MANAGER_SECRET_KEY"):
        logger.warning(
            "Using a random secret key. Set YT_DL_MANAGER_SECRET_KEY "
            "environment variable for persistent sessions across restarts."
        )
    app.jinja_env.globals["_"] = _
    app.executor = ThreadPoolExecutor(max_workers=3)
    atexit.register(app.executor.shutdown)
    _setup_csrf(app)
    _setup_cache_control(app)
    _register_routes(app)
    return app


def main(host="127.0.0.1", port=5000):
    """Run the Flask web UI.

    Args:
        host (str): Host to bind to.
        port (int): Port to bind to.
    """
    logger.warning(
        "Using Flask development server. "
        "Not recommended for production use."
    )
    app = create_app()
    try:
        app.run(host=host, port=port)
    finally:
        app.executor.shutdown(wait=True)
