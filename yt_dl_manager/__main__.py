import argparse
from .create_config import create_default_config
from .daemon import main as daemon_main
from .add_to_queue import main as add_to_queue_main
import os

def main():
    parser = argparse.ArgumentParser(
        description="yt-dl-manager: A tool for managing youtube-dl downloads."
    )
    subparsers = parser.add_subparsers(dest="command")

    # init command
    init_parser = subparsers.add_parser("init", help="Create default config file.")

    # daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run the download daemon.")

    # add command
    add_parser = subparsers.add_parser("add", help="Add a video to the queue.")
    add_parser.add_argument("url", type=str, help="The URL of the video to download.")

    args = parser.parse_args()

    if args.command == "init":
        create_default_config()
    elif args.command == "daemon":
        daemon_main()
    elif args.command == "add":
        add_to_queue_main(args)

if __name__ == "__main__":
    main()
