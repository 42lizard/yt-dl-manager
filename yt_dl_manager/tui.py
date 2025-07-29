"""Text User Interface for yt-dl-manager."""

import sys
from .maintenance import MaintenanceCommands
from .db_utils import DatabaseUtils


def _show_menu():
    """Display the TUI menu options."""
    print("\n" + "=" * 50)
    print("TUI Commands:")
    print("  1. Show queue status")
    print("  2. List pending downloads")
    print("  3. List failed downloads")
    print("  4. List downloaded items")
    print("  5. Add URL to queue")
    print("  6. Exit")
    print("=" * 50)


def _handle_status_command(maintenance):
    """Handle status display command."""
    print("\nQueue Status:")
    maintenance.show_status()


def _handle_list_command(maintenance, status, status_name):
    """Handle list commands for different statuses."""
    print(f"\n{status_name} Downloads:")
    downloads = maintenance.list_downloads(status=status, limit=10)
    if downloads:
        maintenance.print_downloads_table(downloads, status)
    else:
        print(f"No {status.lower()} downloads.")


def _handle_add_url_command(db_utils):
    """Handle add URL command."""
    url = input("Enter URL to add: ").strip()
    if url:
        success, message, _ = db_utils.add_url(url)
        if success:
            print(f"✓ {message}")
        else:
            print(f"! {message}")
    else:
        print("No URL provided.")


def _initialize_database():
    """Initialize database and return DatabaseUtils instance."""
    try:
        db_utils = DatabaseUtils()
        # This will create the database if it doesn't exist via _ensure_schema
        print(f"Database initialized at: {db_utils.db_path}")
        return db_utils
    except (OSError, PermissionError) as exc:
        print(f"Error initializing database: {exc}")
        sys.exit(1)


def main():
    """Run the Text User Interface for yt-dl-manager.

    This function creates the database if it doesn't exist and provides
    a simple interactive interface for managing downloads.
    """
    print("YT-DL-MANAGER - Text User Interface")
    print("===================================")

    # Ensure database exists
    db_utils = _initialize_database()

    # Initialize maintenance commands
    maintenance = MaintenanceCommands()

    # Show status
    print("\nCurrent Queue Status:")
    print("-" * 20)
    maintenance.show_status()

    # Simple interactive loop
    while True:
        _show_menu()

        try:
            choice = input("Enter your choice (1-6): ").strip()

            if choice == "1":
                _handle_status_command(maintenance)
            elif choice == "2":
                _handle_list_command(maintenance, 'pending', 'Pending')
            elif choice == "3":
                _handle_list_command(maintenance, 'failed', 'Failed')
            elif choice == "4":
                _handle_list_command(maintenance, 'downloaded', 'Downloaded')
            elif choice == "5":
                _handle_add_url_command(db_utils)
            elif choice == "6":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-6.")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}")
