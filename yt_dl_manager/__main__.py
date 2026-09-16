"""This module provides a CLI for yt-dl-manager."""

import argparse
import os
import re
import sys

from .logging_config import setup_logging
from .create_config import create_default_config
from .daemon import main as daemon_main
from .add_to_queue import main as add_to_queue_main
from .download_store import (
    DownloadQuery,
    DownloadSort,
    DownloadStatus,
    DownloadStore,
)
from .tui import main as tui_main
from .config import get_language_preference, set_language_preference
from .i18n import _, setup_translation, get_available_languages
from .i18n import get_current_language


def setup_argument_parser():
    """Set up and return the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description=_(
            "yt-dl-manager: A tool for managing youtube-dl downloads.")
    )
    subparsers = parser.add_subparsers(dest="command")

    # init command
    init_parser = subparsers.add_parser(
        "init", help=_("Create default config file."))
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=_("Force overwrite of existing config file."),
    )

    # daemon command
    subparsers.add_parser("daemon", help=_("Run the download daemon."))

    # add command
    add_parser = subparsers.add_parser(
        "add", help=_("Add a video to the queue."))
    add_parser.add_argument(
        "url", type=str, help=_("The URL of the video to download.")
    )
    add_parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        help=_("Immediately start the download after adding to the queue."),
    )

    # tui command
    tui_parser = subparsers.add_parser(
        "tui", help=_("Launch the Terminal User Interface.")
    )
    tui_parser.add_argument(
        "--recent-limit",
        type=int,
        default=10,
        help=_("Number of recent completed downloads to show (default: 10)."),
    )

    # language command
    lang_parser = subparsers.add_parser(
        "language", help=_("Manage language settings."))
    lang_subparsers = lang_parser.add_subparsers(dest="lang_action")

    # language set
    set_parser = lang_subparsers.add_parser(
        "set", help=_("Set language preference."))
    set_parser.add_argument(
        "language",
        choices=get_available_languages() + ["auto"],
        help=_("Language code or 'auto' for automatic detection."),
    )

    # language show
    lang_subparsers.add_parser("show", help=_(
        "Show current language setting."))

    _setup_maintenance_commands(subparsers)
    return parser


def _setup_maintenance_commands(subparsers):
    """Set up maintenance-related subcommands."""
    # list command
    list_parser = subparsers.add_parser(
        "list", help=_("List downloads by status."))
    list_subparsers = list_parser.add_subparsers(dest="list_type")

    # list pending
    pending_parser = list_subparsers.add_parser(
        "pending", help=_("List pending downloads.")
    )
    pending_parser.add_argument(
        "--limit", type=int, help=_("Maximum number of results.")
    )
    pending_parser.add_argument(
        "--sort-by",
        choices=["date", "retries", "url"],
        default="date",
        help=_("Sort by field."),
    )

    # list failed
    failed_parser = list_subparsers.add_parser(
        "failed", help=_("List failed downloads.")
    )
    failed_parser.add_argument(
        "--limit", type=int, help=_("Maximum number of results.")
    )
    failed_parser.add_argument(
        "--retry-count", type=int, help=_("Filter by retry count.")
    )

    # list downloaded
    downloaded_parser = list_subparsers.add_parser(
        "downloaded", help=_("List downloaded items.")
    )
    downloaded_parser.add_argument(
        "--limit", type=int, help=_("Maximum number of results.")
    )
    downloaded_parser.add_argument(
        "--missing-files",
        action="store_true",
        help=_("Only show items with missing files."),
    )
    downloaded_parser.add_argument(
        "--extractor", help=_("Filter by extractor type."))

    # status command
    subparsers.add_parser("status", help=_("Show queue status dashboard."))

    # remove command
    remove_parser = subparsers.add_parser(
        "remove", help=_("Remove items from queue."))
    remove_subparsers = remove_parser.add_subparsers(dest="remove_type")

    # remove failed
    remove_failed_parser = remove_subparsers.add_parser(
        "failed", help=_("Remove failed downloads.")
    )
    remove_failed_parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help=_("Only remove items older than DAYS."),
    )
    remove_failed_parser.add_argument(
        "--dry-run", action="store_true", help=_("Preview what would be removed.")
    )

    # remove by ID or URL
    remove_items_parser = remove_subparsers.add_parser(
        "items", help=_("Remove specific items.")
    )
    remove_items_parser.add_argument(
        "targets", nargs="+", help=_("Database IDs or URL patterns to remove.")
    )
    remove_items_parser.add_argument(
        "--dry-run", action="store_true", help=_("Preview what would be removed.")
    )

    # retry command
    retry_parser = subparsers.add_parser(
        "retry", help=_("Retry failed or completed downloads.")
    )
    retry_parser.add_argument(
        "targets", nargs="*", help=_("Database IDs or URL patterns to retry.")
    )
    retry_parser.add_argument(
        "--failed", action="store_true", help=_("Retry all failed downloads.")
    )

    # verify command
    verify_parser = subparsers.add_parser(
        "verify", help=_("Verify downloaded files exist.")
    )
    verify_parser.add_argument(
        "--fix",
        action="store_true",
        help=_("Automatically mark missing files for redownload."),
    )
    verify_parser.add_argument(
        "--delete-records",
        action="store_true",
        help=_("Remove database entries for missing files."),
    )

    # redownload command
    redownload_parser = subparsers.add_parser(
        "redownload", help=_("Mark items for redownload.")
    )
    redownload_parser.add_argument(
        "targets", nargs="+", help=_("Database IDs or URL patterns to redownload.")
    )

    # cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help=_("Perform database maintenance.")
    )
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help=_("Preview cleanup actions.")
    )

    # export command
    export_parser = subparsers.add_parser(
        "export", help=_("Export queue data."))
    export_parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help=_("Export format.")
    )
    export_parser.add_argument("--status", help=_("Filter by status."))
    export_parser.add_argument("--output", help=_("Output file path."))


def main():
    """Main function for the CLI."""
    # Initialize i18n with language preference from config
    language_preference = get_language_preference()
    setup_translation(language_preference)

    # Set up logging
    log_level = getattr(
        __import__("logging"), os.getenv(
            "YT_DL_MANAGER_LOG_LEVEL", "INFO").upper()
    )
    setup_logging(log_level)

    parser = setup_argument_parser()
    args = parser.parse_args()

    # Command dispatch mapping
    command_handlers = {
        "init": lambda a: create_default_config(force=a.force),
        "daemon": lambda a: daemon_main(),
        "add": add_to_queue_main,
        "tui": lambda a: tui_main(recent_limit=max(a.recent_limit, 1)),
        "language": handle_language_command,
        "list": handle_list_command,
        "status": lambda a: handle_status_command(),
        "remove": handle_remove_command,
        "retry": handle_retry_command,
        "verify": handle_verify_command,
        "redownload": handle_redownload_command,
        "cleanup": handle_cleanup_command,
        "export": handle_export_command,
    }

    if args.command in command_handlers:
        command_handlers[args.command](args)
    else:
        # display help if no command is provided
        parser.print_help()


def handle_language_command(args):
    """Handle language subcommands."""

    if args.lang_action == "set":
        if args.language == "auto":
            set_language_preference(None)
            print(_("Language preference set to automatic detection."))
        else:
            set_language_preference(args.language)
            print(_("Language preference set to: {}").format(args.language))
        print(_("Restart the application for changes to take effect."))

    elif args.lang_action == "show":
        current_lang = get_current_language()
        pref = get_language_preference()
        if pref is None:
            print(
                _("Language preference: automatic (currently: {})").format(
                    current_lang)
            )
        else:
            print(
                _("Language preference: {} (currently: {})").format(
                    pref, current_lang)
            )

    else:
        print(_("Error: Must specify language action (set, show)"))
        sys.exit(1)


def _parse_targets(targets):
    """Parse target arguments as IDs or URL patterns.

    Args:
        targets (list): List of targets to parse.

    Returns:
        tuple: (numeric_ids, url_patterns)
    """
    numeric_ids = []
    url_patterns = []

    for target in targets:
        try:
            numeric_ids.append(int(target))
        except ValueError:
            url_patterns.append(target)

    return numeric_ids, url_patterns


def _list_downloads(store, status, **options):
    """Select Downloads for terminal display."""
    if status == 'downloaded' and options.get('missing_files', False):
        return _missing_downloads(store)

    return store.list_downloads(DownloadQuery(
        status=status,
        limit=options.get('limit'),
        sort=options.get('sort', DownloadSort.REQUESTED),
        retries=options.get('retry_count'),
        extractor=options.get('extractor'),
    ))


def _missing_downloads(store):
    """Return completed Downloads whose media file is missing."""
    downloads = store.list_downloads(
        DownloadQuery(DownloadStatus.DOWNLOADED)
    )
    return [
        download
        for download in downloads
        if download.filename and not download.filename.exists()
    ]


def _storage_usage(downloads):
    """Measure files belonging to completed Downloads."""
    sizes = []
    missing = 0
    for download in downloads:
        filename = download.filename
        if not filename:
            continue
        try:
            sizes.append(os.path.getsize(filename))
        except OSError:
            missing += 1
    return {
        'files_found': len(sizes),
        'files_missing': missing,
        'total_size_mb': sum(sizes) / (1024 * 1024),
    }


def _format_display_text(text, max_length):
    """Truncate text for terminal tables."""
    return text[:max_length - 3] + '...' if len(text) > max_length else text


def _sanitize_filename(filename):
    """Make a Download filename safe for terminal display."""
    return re.sub(r'[^A-Za-z0-9._-]', '_', filename.name)


def _print_pending_downloads(downloads):
    """Print pending Downloads."""
    print(f"{'ID':<8} {'RETRIES':<8} {'REQUESTED':<20} {'URL':<40}")
    print("-" * 80)
    for download in downloads:
        requested = (
            download.requested_at.strftime('%Y-%m-%d %H:%M')
            if download.requested_at else 'N/A'
        )
        print(
            f"{download.id:<8} {download.retries:<8} "
            f"{requested:<20} {_format_display_text(download.url, 40):<40}"
        )


def _print_failed_downloads(downloads):
    """Print failed Downloads."""
    print(f"{'ID':<8} {'RETRIES':<8} {'EXTRACTOR':<12} {'URL':<40}")
    print("-" * 80)
    for download in downloads:
        extractor = _format_display_text(download.extractor or 'N/A', 12)
        print(
            f"{download.id:<8} {download.retries:<8} "
            f"{extractor:<12} {_format_display_text(download.url, 40):<40}"
        )


def _print_downloaded_files(downloads):
    """Print completed Downloads."""
    print(f"{'ID':<8} {'EXTRACTOR':<12} {'EXISTS':<7} {'FILENAME':<40}")
    print("-" * 80)
    for download in downloads:
        filename = (
            _format_display_text(_sanitize_filename(download.filename), 40)
            if download.filename else 'N/A'
        )
        exists = 'YES' if download.filename and download.filename.exists() else 'NO'
        extractor = _format_display_text(download.extractor or 'N/A', 12)
        print(
            f"{download.id:<8} {extractor:<12} "
            f"{exists:<7} {filename:<40}"
        )


def _print_downloads_table(downloads, status):
    """Print Downloads in a status-specific table."""
    if not downloads:
        print(f"No {status} downloads found.")
        return

    print(f"\n{status.upper()} DOWNLOADS ({len(downloads)} items):")
    print("-" * 80)
    printers = {
        'pending': _print_pending_downloads,
        'failed': _print_failed_downloads,
        'downloaded': _print_downloaded_files,
    }
    printers[status](downloads)
    print("-" * 80)


def _show_status(store):
    """Print Download and storage totals."""
    status_counts = store.status_counts()
    print("\nYT-DL-MANAGER QUEUE STATUS")
    print("=" * 40)
    print(f"Total downloads:    {sum(status_counts.values()):>8}")
    print(f"Pending:           {status_counts[DownloadStatus.PENDING]:>8}")
    print(f"Downloading:       {status_counts[DownloadStatus.DOWNLOADING]:>8}")
    print(f"Completed:         {status_counts[DownloadStatus.DOWNLOADED]:>8}")
    print(f"Failed:            {status_counts[DownloadStatus.FAILED]:>8}")
    if status_counts[DownloadStatus.DOWNLOADED] > 0:
        downloaded = store.list_downloads(
            DownloadQuery(DownloadStatus.DOWNLOADED)
        )
        storage = _storage_usage(downloaded)
        print("\nSTORAGE USAGE")
        print("-" * 40)
        print(f"Files found:       {storage['files_found']:>8}")
        print(f"Files missing:     {storage['files_missing']:>8}")
        print(f"Total size:        {storage['total_size_mb']:>8.1f} MB")
    print("=" * 40)


def handle_list_command(args):
    """Handle list subcommands."""
    if not args.list_type:
        print(_("Error: Must specify list type (pending, failed, downloaded)"))
        sys.exit(1)

    store = DownloadStore()

    # Map sort options
    sort_mapping = {
        "date": DownloadSort.REQUESTED,
        "retries": DownloadSort.RETRIES,
        "url": DownloadSort.URL,
    }

    if args.list_type == "pending":
        sort = sort_mapping.get(args.sort_by, DownloadSort.REQUESTED)
        downloads = _list_downloads(
            store,
            status=DownloadStatus.PENDING,
            limit=args.limit,
            sort=sort,
        )
        _print_downloads_table(downloads, "pending")

    elif args.list_type == "failed":
        downloads = _list_downloads(
            store,
            status=DownloadStatus.FAILED,
            limit=args.limit,
            retry_count=args.retry_count,
        )
        _print_downloads_table(downloads, "failed")

    elif args.list_type == "downloaded":
        downloads = _list_downloads(
            store,
            status=DownloadStatus.DOWNLOADED,
            limit=args.limit,
            extractor=args.extractor,
            missing_files=args.missing_files,
        )
        _print_downloads_table(downloads, "downloaded")


def handle_status_command():
    """Handle status command."""
    _show_status(DownloadStore())


def _confirm_removal(prompt_message):
    """Ask user for confirmation to proceed with removal.

    Args:
        prompt_message (str): The confirmation prompt to show

    Returns:
        bool: True if user confirms, False otherwise
    """
    response = input(prompt_message)
    return response.lower() == "y"


def _remove_failed(store, older_than_days=None, dry_run=False):
    """Remove failed Downloads and report the result."""
    count = store.remove_by_status(
        DownloadStatus.FAILED,
        older_than_days=older_than_days,
        dry_run=dry_run,
    )
    action = "Would remove" if dry_run else "Removed"
    age_filter = f" older than {older_than_days} days" if older_than_days else ""
    print(f"{action} {count} failed downloads{age_filter}.")
    return count


def _handle_remove_failed(store, args):
    """Handle removal of failed downloads."""
    if not args.dry_run:
        count = _remove_failed(
            store,
            older_than_days=args.older_than, dry_run=True)
        if count > 0:
            prompt = (
                f"Are you sure you want to remove {count} failed downloads? (y/N): "
            )
            if not _confirm_removal(prompt):
                print("Operation cancelled.")
                return

    _remove_failed(
        store,
        older_than_days=args.older_than, dry_run=args.dry_run)


def _handle_remove_by_ids(store, numeric_ids, dry_run):
    """Handle removal of items by IDs."""
    if not dry_run:
        prompt = (
            f"Are you sure you want to remove {len(numeric_ids)} items by ID? (y/N): "
        )
        if not _confirm_removal(prompt):
            print("Operation cancelled.")
            return
    count = store.remove(numeric_ids, dry_run=dry_run)
    action = "Would remove" if dry_run else "Removed"
    print(f"{action} {count} downloads by ID.")


def _handle_remove_by_pattern(store, pattern, dry_run):
    """Handle removal of items by URL pattern."""
    if not dry_run:
        matching = store.find_by_url(pattern)
        if matching:
            print(f"Found {len(matching)} downloads matching '{pattern}':")
            for item in matching[:5]:  # Show first 5
                print(f"  ID {item.id}: {item.url[:60]}...")
            if len(matching) > 5:
                print(f"  ... and {len(matching) - 5} more")

            prompt = f"Remove these {len(matching)} downloads? (y/N): "
            if not _confirm_removal(prompt):
                print("Skipping URL pattern:", pattern)
                return

    count = store.remove_by_url(pattern, dry_run=dry_run)
    action = "Would remove" if dry_run else "Removed"
    print(f"{action} {count} downloads matching URL pattern '{pattern}'.")


def handle_remove_command(args):
    """Handle remove subcommands."""
    if not args.remove_type:
        print("Error: Must specify what to remove (failed, items)")
        sys.exit(1)

    store = DownloadStore()

    if args.remove_type == "failed":
        _handle_remove_failed(store, args)
    elif args.remove_type == "items":
        # Parse targets as IDs or URL patterns
        numeric_ids, url_patterns = _parse_targets(args.targets)

        if numeric_ids:
            _handle_remove_by_ids(store, numeric_ids, args.dry_run)

        for pattern in url_patterns:
            _handle_remove_by_pattern(store, pattern, args.dry_run)


def handle_retry_command(args):
    """Handle retry command."""
    store = DownloadStore()

    if args.failed:
        failed = store.list_downloads(DownloadQuery(DownloadStatus.FAILED))
        download_ids = [download.id for download in failed]
    elif args.targets:
        # Parse targets as IDs or URL patterns
        numeric_ids, url_patterns = _parse_targets(args.targets)

        all_ids = numeric_ids[:]

        # Find IDs from URL patterns
        for pattern in url_patterns:
            matching = store.find_by_url(pattern)
            pattern_ids = [item.id for item in matching]
            all_ids.extend(pattern_ids)
            print(
                f"Found {len(pattern_ids)} downloads matching pattern '{pattern}'")

        download_ids = all_ids
    else:
        print("Error: Must specify --failed or provide target IDs/URLs")
        sys.exit(1)

    if download_ids:
        count = store.reset(
            download_ids,
            reset_retries=True,
        )
        print(f"Reset {count} downloads to pending status for retry.")
    else:
        print("No downloads to retry.")


def handle_verify_command(args):
    """Handle verify command."""
    store = DownloadStore()
    downloaded = store.list_downloads(
        DownloadQuery(DownloadStatus.DOWNLOADED)
    )
    missing_files = _missing_downloads(store)

    print("\nFILE VERIFICATION RESULTS")
    print("-" * 40)
    print(f"Total downloaded:   {len(downloaded):>8}")
    print(f"Files found:        {len(downloaded) - len(missing_files):>8}")
    print(f"Files missing:      {len(missing_files):>8}")

    if missing_files:
        print("\nMISSING FILES:")
        for download in missing_files:
            print(f"  ID {download.id}: {download.filename}")

    missing_ids = [download.id for download in missing_files]
    if missing_ids and args.fix:
        store.reset(missing_ids, reset_retries=True)
        print(f"\nMarked {len(missing_ids)} missing files for redownload.")
    if missing_ids and args.delete_records:
        store.remove(missing_ids)
        print(f"\nDeleted {len(missing_ids)} database records for missing files.")


def handle_redownload_command(args):
    """Handle redownload command."""
    store = DownloadStore()

    # Parse targets as IDs or URL patterns
    numeric_ids, url_patterns = _parse_targets(args.targets)

    all_ids = numeric_ids[:]

    # Find IDs from URL patterns
    for pattern in url_patterns:
        matching = store.find_by_url(pattern)
        pattern_ids = [item.id for item in matching]
        all_ids.extend(pattern_ids)
        print(
            f"Found {len(pattern_ids)} downloads matching pattern '{pattern}'")

    if all_ids:
        count = store.reset(all_ids, reset_retries=True)
        print(f"Marked {count} downloads for redownload.")
    else:
        print("No downloads found to redownload.")


def handle_cleanup_command(args):
    """Handle cleanup command."""
    store = DownloadStore()

    if not args.dry_run:
        response = input(
            "Are you sure you want to perform database cleanup? (y/N): ")
        if response.lower() != "y":
            print("Operation cancelled.")
            return

    stats = store.cleanup_database(dry_run=args.dry_run)
    action = "Would perform" if args.dry_run else "Performed"
    print("\nDATABASE CLEANUP RESULTS")
    print("-" * 40)
    print(f"Orphaned records:   {stats['orphaned_records']:>8}")
    if not args.dry_run:
        print(f"Space saved:        {stats['space_saved_kb']:>8} KB")
        vacuum = 'YES' if stats['vacuum_performed'] else 'NO'
        print(f"Vacuum performed:   {vacuum:>8}")
    else:
        print(f"{action} vacuum and cleanup operations.")


def handle_export_command(args):
    """Handle export command."""
    data = DownloadStore().export_data(args.format, args.status)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as output_file:
            output_file.write(data)
        print(f"Data exported to {args.output}")
    else:
        print(data)


if __name__ == "__main__":
    main()
