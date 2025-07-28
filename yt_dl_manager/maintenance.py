"""Database maintenance commands for yt-dl-manager."""

import os
from .db_utils import DatabaseUtils, DownloadStatus


class MaintenanceCommands:
    """Handles database maintenance operations for yt-dl-manager."""

    def __init__(self, db_path=None):
        """Initialize maintenance commands with database path.

        Args:
            db_path (str, optional): Path to the SQLite database file.
        """
        self.db = DatabaseUtils(db_path)

    def list_downloads(self, status, **options):
        """List downloads by status with optional filters.

        Args:
            status (str): Status to filter by ('pending', 'failed', 'downloaded').
            **options: Optional filters (limit, sort_by, retry_count, extractor, missing_files).

        Returns:
            list: List of download records.
        """
        if status == 'downloaded' and options.get('missing_files', False):
            return self.db.get_downloads_missing_files()

        # Extract specific options
        limit = options.get('limit')
        sort_by = options.get('sort_by', 'timestamp_requested')

        # Pass remaining filters to database method
        filters = {k: v for k, v in options.items()
                   if k in ['retry_count', 'extractor']}

        return self.db.get_downloads_by_status(
            status=status,
            limit=limit,
            sort_by=sort_by,
            **filters
        )

    def print_downloads_table(self, downloads, status):
        """Print downloads in a formatted table.

        Args:
            downloads (list): List of download records.
            status (str): Status being displayed.
        """
        if not downloads:
            print(f"No {status} downloads found.")
            return

        print(f"\n{status.upper()} DOWNLOADS ({len(downloads)} items):")
        print("-" * 80)

        if status == 'pending':
            print(f"{'ID':<8} {'RETRIES':<8} {'REQUESTED':<20} {'URL':<40}")
            print("-" * 80)
            for download in downloads:
                url = download['url']
                url_display = url[:37] + '...' if len(url) > 40 else url
                timestamp = download['timestamp_requested']
                requested = timestamp[:16] if timestamp else 'N/A'
                print(f"{download['id']:<8} {download['retries']:<8} "
                      f"{requested:<20} {url_display:<40}")

        elif status == 'failed':
            print(f"{'ID':<8} {'RETRIES':<8} {'EXTRACTOR':<12} {'URL':<40}")
            print("-" * 80)
            for download in downloads:
                url = download['url']
                url_display = url[:37] + '...' if len(url) > 40 else url
                extractor = download['extractor'] or 'N/A'
                extractor_display = extractor[:9] + \
                    '...' if len(extractor) > 12 else extractor
                print(f"{download['id']:<8} {download['retries']:<8} "
                      f"{extractor_display:<12} {url_display:<40}")

        elif status == 'downloaded':
            print(f"{'ID':<8} {'EXTRACTOR':<12} {'EXISTS':<7} {'FILENAME':<40}")
            print("-" * 80)
            for download in downloads:
                filename = download['final_filename'] or 'N/A'
                basename = os.path.basename(filename)
                filename_display = basename[:37] + \
                    '...' if len(basename) > 40 else basename
                file_exists = ('YES' if download['final_filename'] and
                               os.path.exists(download['final_filename']) else 'NO')
                extractor = download['extractor'] or 'N/A'
                extractor_display = extractor[:9] + \
                    '...' if len(extractor) > 12 else extractor
                print(f"{download['id']:<8} {extractor_display:<12} "
                      f"{file_exists:<7} {filename_display:<40}")

        print("-" * 80)

    def show_status(self):
        """Display queue status dashboard."""
        status_counts = self.db.get_queue_status()
        total = sum(status_counts.values())

        print("\nYT-DL-MANAGER QUEUE STATUS")
        print("=" * 40)
        print(f"Total downloads:    {total:>8}")
        print(f"Pending:           {status_counts.get('pending', 0):>8}")
        print(f"Downloading:       {status_counts.get('downloading', 0):>8}")
        print(f"Completed:         {status_counts.get('downloaded', 0):>8}")
        print(f"Failed:            {status_counts.get('failed', 0):>8}")

        # Show storage usage if there are downloaded files
        if status_counts.get('downloaded', 0) > 0:
            storage = self.db.get_storage_usage_summary()
            print("\nSTORAGE USAGE")
            print("-" * 40)
            print(f"Files found:       {storage['files_found']:>8}")
            print(f"Files missing:     {storage['files_missing']:>8}")
            print(f"Total size:        {storage['total_size_mb']:>8.1f} MB")

        print("=" * 40)

    def remove_failed(self, older_than_days=None, dry_run=False):
        """Remove failed downloads.

        Args:
            older_than_days (int, optional): Only remove items older than this many days.
            dry_run (bool): Preview what would be removed without removing.

        Returns:
            int: Number of items removed or that would be removed.
        """
        count = self.db.remove_downloads_by_status(
            DownloadStatus.FAILED.value,
            older_than_days=older_than_days,
            dry_run=dry_run
        )

        action = "Would remove" if dry_run else "Removed"
        age_filter = f" older than {older_than_days} days" if older_than_days else ""
        print(f"{action} {count} failed downloads{age_filter}.")

        return count

    def remove_by_ids(self, download_ids, dry_run=False):
        """Remove downloads by their IDs.

        Args:
            download_ids (list): List of download IDs to remove.
            dry_run (bool): Preview what would be removed.

        Returns:
            int: Number of items removed.
        """
        count = self.db.remove_downloads_by_ids(download_ids, dry_run=dry_run)

        action = "Would remove" if dry_run else "Removed"
        print(f"{action} {count} downloads by ID.")

        return count

    def remove_by_url_pattern(self, url_pattern, dry_run=False):
        """Remove downloads by URL pattern.

        Args:
            url_pattern (str): URL pattern to match.
            dry_run (bool): Preview what would be removed.

        Returns:
            int: Number of items removed.
        """
        count = self.db.remove_downloads_by_url_pattern(
            url_pattern, dry_run=dry_run)

        action = "Would remove" if dry_run else "Removed"
        print(f"{action} {count} downloads matching URL pattern '{url_pattern}'.")

        return count

    def retry_downloads(self, download_ids=None, failed_only=False):
        """Retry downloads by resetting them to pending.

        Args:
            download_ids (list, optional): Specific IDs to retry.
            failed_only (bool): Retry all failed downloads.

        Returns:
            int: Number of downloads reset to pending.
        """
        if failed_only:
            failed_downloads = self.db.get_downloads_by_status(
                DownloadStatus.FAILED.value)
            download_ids = [d['id'] for d in failed_downloads]

        if not download_ids:
            print("No downloads to retry.")
            return 0

        count = self.db.reset_downloads_to_pending(
            download_ids, reset_retries=True)
        print(f"Reset {count} downloads to pending status for retry.")

        return count

    def redownload_items(self, download_ids):
        """Mark downloaded items for redownload.

        Args:
            download_ids (list): List of download IDs to redownload.

        Returns:
            int: Number of downloads reset for redownload.
        """
        count = self.db.reset_downloads_to_pending(
            download_ids, reset_retries=True)
        print(f"Marked {count} downloads for redownload.")

        return count

    def verify_files(self, fix_missing=False, delete_records=False):
        """Verify downloaded files exist on disk.

        Args:
            fix_missing (bool): Automatically mark missing files for redownload.
            delete_records (bool): Remove database records for missing files.

        Returns:
            dict: Verification statistics.
        """
        missing_files = self.db.get_downloads_missing_files()
        downloaded = self.db.get_downloads_by_status(
            DownloadStatus.DOWNLOADED.value)

        stats = {
            'total_downloaded': len(downloaded),
            'files_found': len(downloaded) - len(missing_files),
            'files_missing': len(missing_files)
        }

        print("\nFILE VERIFICATION RESULTS")
        print("-" * 40)
        print(f"Total downloaded:   {stats['total_downloaded']:>8}")
        print(f"Files found:        {stats['files_found']:>8}")
        print(f"Files missing:      {stats['files_missing']:>8}")

        if missing_files:
            print("\nMISSING FILES:")
            for item in missing_files:
                print(f"  ID {item['id']}: {item['final_filename']}")

        if missing_files and fix_missing:
            missing_ids = [item['id'] for item in missing_files]
            self.db.reset_downloads_to_pending(missing_ids, reset_retries=True)
            print(f"\nMarked {len(missing_ids)} missing files for redownload.")

        if missing_files and delete_records:
            missing_ids = [item['id'] for item in missing_files]
            self.db.remove_downloads_by_ids(missing_ids)
            print(
                f"\nDeleted {len(missing_ids)} database records for missing files.")

        return stats

    def cleanup_database(self, dry_run=False):
        """Perform database maintenance.

        Args:
            dry_run (bool): Preview cleanup actions without performing them.

        Returns:
            dict: Cleanup statistics.
        """
        stats = self.db.cleanup_database(dry_run=dry_run)

        action = "Would perform" if dry_run else "Performed"
        print("\nDATABASE CLEANUP RESULTS")
        print("-" * 40)
        print(f"Orphaned records:   {stats['orphaned_records']:>8}")

        if not dry_run:
            print(f"Space saved:        {stats['space_saved_kb']:>8} KB")
            print(
                f"Vacuum performed:   {'YES' if stats['vacuum_performed'] else 'NO':>8}")
        else:
            print(f"{action} vacuum and cleanup operations.")

        return stats

    def export_data(self, output_format='json', status_filter=None, output_file=None):
        """Export queue data.

        Args:
            output_format (str): Export format ('json' or 'csv').
            status_filter (str, optional): Filter by status.
            output_file (str, optional): Output file path.

        Returns:
            str: Exported data.
        """
        data = self.db.export_data(output_format, status_filter)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(data)
            print(f"Data exported to {output_file}")
        else:
            print(data)

        return data

    def find_downloads_by_url(self, url_pattern):
        """Find downloads matching a URL pattern.

        Args:
            url_pattern (str): URL pattern to search for.

        Returns:
            list: Matching download records.
        """
        return self.db.find_downloads_by_url_pattern(url_pattern)
