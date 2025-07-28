"""This module provides a CLI for yt-dl-manager."""

import argparse
import os

from .logging_config import setup_logging
from .create_config import create_default_config
from .daemon import main as daemon_main
from .add_to_queue import main as add_to_queue_main


def main():
    """Main function for the CLI."""
    # Set up logging
    log_level = getattr(
        __import__('logging'),
        os.getenv(
            'YT_DL_MANAGER_LOG_LEVEL',
            'INFO').upper())
    setup_logging(log_level)

    parser = argparse.ArgumentParser(
        description="yt-dl-manager: A tool for managing youtube-dl downloads."
    )
    subparsers = parser.add_subparsers(dest="command")

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Create default config file.")
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing config file.")

    # daemon command
    subparsers.add_parser("daemon", help="Run the download daemon.")

    # add command
    add_parser = subparsers.add_parser("add", help="Add a video to the queue.")
    add_parser.add_argument(
        "url", type=str, help="The URL of the video to download.")
    add_parser.add_argument(
        "-d", "--download", action="store_true",
        help="Immediately start the download after adding to the queue.")

    args = parser.parse_args()

    if args.command == "init":
        create_default_config(force=args.force)
    elif args.command == "daemon":
        daemon_main()
    elif args.command == "add":
        add_to_queue_main(args)
    # display help if no command is provided
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
