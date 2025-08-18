"""This module provides a CLI for yt-dl-manager."""

import argparse
import os
import sys

from .logging_config import setup_logging
from .create_config import create_default_config
from .daemon import main as daemon_main
from .add_to_queue import main as add_to_queue_main
from .maintenance import MaintenanceCommands
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
        "tui": lambda a: tui_main(recent_limit=a.recent_limit),
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


def handle_list_command(args):
    """Handle list subcommands."""
    if not args.list_type:
        print(_("Error: Must specify list type (pending, failed, downloaded)"))
        sys.exit(1)

    maintenance = MaintenanceCommands()

    # Map sort options
    sort_mapping = {"date": "timestamp_requested",
                    "retries": "retries", "url": "url"}

    if args.list_type == "pending":
        sort_by = sort_mapping.get(args.sort_by, "timestamp_requested")
        downloads = maintenance.list_downloads(
            status="pending", limit=args.limit, sort_by=sort_by
        )
        maintenance.print_downloads_table(downloads, "pending")

    elif args.list_type == "failed":
        downloads = maintenance.list_downloads(
            status="failed", limit=args.limit, retry_count=args.retry_count
        )
        maintenance.print_downloads_table(downloads, "failed")

    elif args.list_type == "downloaded":
        downloads = maintenance.list_downloads(
            status="downloaded",
            limit=args.limit,
            extractor=args.extractor,
            missing_files=args.missing_files,
        )
        maintenance.print_downloads_table(downloads, "downloaded")


def handle_status_command():
    """Handle status command."""
    maintenance = MaintenanceCommands()
    maintenance.show_status()


def _confirm_removal(prompt_message):
    """Ask user for confirmation to proceed with removal.

    Args:
        prompt_message (str): The confirmation prompt to show

    Returns:
        bool: True if user confirms, False otherwise
    """
    response = input(prompt_message)
    return response.lower() == "y"


def _handle_remove_failed(maintenance, args):
    """Handle removal of failed downloads."""
    if not args.dry_run:
        count = maintenance.remove_failed(
            older_than_days=args.older_than, dry_run=True)
        if count > 0:
            prompt = (
                f"Are you sure you want to remove {count} failed downloads? (y/N): "
            )
            if not _confirm_removal(prompt):
                print("Operation cancelled.")
                return

    maintenance.remove_failed(
        older_than_days=args.older_than, dry_run=args.dry_run)


def _handle_remove_by_ids(maintenance, numeric_ids, dry_run):
    """Handle removal of items by IDs."""
    if not dry_run:
        prompt = (
            f"Are you sure you want to remove {len(numeric_ids)} items by ID? (y/N): "
        )
        if not _confirm_removal(prompt):
            print("Operation cancelled.")
            return
    maintenance.remove_by_ids(numeric_ids, dry_run=dry_run)


def _handle_remove_by_pattern(maintenance, pattern, dry_run):
    """Handle removal of items by URL pattern."""
    if not dry_run:
        matching = maintenance.find_downloads_by_url(pattern)
        if matching:
            print(f"Found {len(matching)} downloads matching '{pattern}':")
            for item in matching[:5]:  # Show first 5
                print(f"  ID {item['id']}: {item['url'][:60]}...")
            if len(matching) > 5:
                print(f"  ... and {len(matching) - 5} more")

            prompt = f"Remove these {len(matching)} downloads? (y/N): "
            if not _confirm_removal(prompt):
                print("Skipping URL pattern:", pattern)
                return

    maintenance.remove_by_url_pattern(pattern, dry_run=dry_run)


def handle_remove_command(args):
    """Handle remove subcommands."""
    if not args.remove_type:
        print("Error: Must specify what to remove (failed, items)")
        sys.exit(1)

    maintenance = MaintenanceCommands()

    if args.remove_type == "failed":
        _handle_remove_failed(maintenance, args)
    elif args.remove_type == "items":
        # Parse targets as IDs or URL patterns
        numeric_ids, url_patterns = _parse_targets(args.targets)

        if numeric_ids:
            _handle_remove_by_ids(maintenance, numeric_ids, args.dry_run)

        for pattern in url_patterns:
            _handle_remove_by_pattern(maintenance, pattern, args.dry_run)


def handle_retry_command(args):
    """Handle retry command."""
    maintenance = MaintenanceCommands()

    if args.failed:
        maintenance.retry_downloads(failed_only=True)
    elif args.targets:
        # Parse targets as IDs or URL patterns
        numeric_ids, url_patterns = _parse_targets(args.targets)

        all_ids = numeric_ids[:]

        # Find IDs from URL patterns
        for pattern in url_patterns:
            matching = maintenance.find_downloads_by_url(pattern)
            pattern_ids = [item["id"] for item in matching]
            all_ids.extend(pattern_ids)
            print(
                f"Found {len(pattern_ids)} downloads matching pattern '{pattern}'")

        if all_ids:
            maintenance.retry_downloads(download_ids=all_ids)
        else:
            print("No downloads found to retry.")
    else:
        print("Error: Must specify --failed or provide target IDs/URLs")
        sys.exit(1)


def handle_verify_command(args):
    """Handle verify command."""
    maintenance = MaintenanceCommands()
    maintenance.verify_files(fix_missing=args.fix,
                             delete_records=args.delete_records)


def handle_redownload_command(args):
    """Handle redownload command."""
    maintenance = MaintenanceCommands()

    # Parse targets as IDs or URL patterns
    numeric_ids, url_patterns = _parse_targets(args.targets)

    all_ids = numeric_ids[:]

    # Find IDs from URL patterns
    for pattern in url_patterns:
        matching = maintenance.find_downloads_by_url(pattern)
        pattern_ids = [item["id"] for item in matching]
        all_ids.extend(pattern_ids)
        print(
            f"Found {len(pattern_ids)} downloads matching pattern '{pattern}'")

    if all_ids:
        maintenance.redownload_items(all_ids)
    else:
        print("No downloads found to redownload.")


def handle_cleanup_command(args):
    """Handle cleanup command."""
    maintenance = MaintenanceCommands()

    if not args.dry_run:
        response = input(
            "Are you sure you want to perform database cleanup? (y/N): ")
        if response.lower() != "y":
            print("Operation cancelled.")
            return

    maintenance.cleanup_database(dry_run=args.dry_run)


def handle_export_command(args):
    """Handle export command."""
    maintenance = MaintenanceCommands()
    maintenance.export_data(
        output_format=args.format, status_filter=args.status, output_file=args.output
    )


if __name__ == "__main__":
    main()
