# yt-dl-manager Implementation Plan

## Overview
A Python daemon that manages media downloads using yt-dlp. URLs are fetched from an SQLite3 database, downloaded in the best available quality, and organized by extractor type. Download status and metadata are tracked in the database.

## Components

### 1. Configuration
- `.env` file for settings:
  - `TARGET_FOLDER`: Base directory for downloads
  - Database path
  - Other relevant options (e.g., yt-dlp options)

### 2. Database Schema
- Table: `downloads`
  - `id` (INTEGER PRIMARY KEY)
  - `url` (TEXT, unique)
  - `status` (TEXT: pending, downloading, downloaded, failed)
  - `timestamp_requested` (DATETIME)
  - `timestamp_downloaded` (DATETIME, nullable)
  - `final_filename` (TEXT, nullable)
  - `extractor` (TEXT, nullable)

### 3. Daemon Process
- Runs as a background service
- Periodically polls the database for new URLs with `status = 'pending'`
- Handles graceful shutdown and error logging

### 4. Download Logic
- For each pending URL:
  - Mark as `downloading`
  - Use yt-dlp to fetch extractor name and download media
  - Save to `TARGET_FOLDER/<extractor>/`
  - On success:
    - Mark as `downloaded`
    - Store `timestamp_downloaded` and `final_filename`
  - On failure:
    - Mark as `failed`
    - Log error

### 5. File Organization
- Downloaded files are placed in subfolders named after the yt-dlp extractor (e.g., `youtube`, `vimeo`)

### 6. Error Handling & Logging
- Log errors to file
- Retry logic for failed downloads (optional)

### 7. Extensibility
- Easy to add new fields or download options
- Modular code structure

## Implementation Steps
## Feature Checklist

- [x] .env configuration for target folder and database path
- [x] SQLite3 schema and migration script
- [x] Daemon process for polling and downloading
- [x] yt-dlp integration for best quality download
- [x] File organization by extractor
- [x] Database update logic for status, filename, extractor, timestamp
- [x] Retry logic for failed downloads (up to 3 times)
- [x] Add-to-queue script with duplicate handling and file path display
- [x] Metadata embedding in final file
- [ ] Error logging to file
- [ ] Optional: Thumbnail download and embedding (disabled)
- [ ] Optional: Web UI for monitoring
- [ ] Optional: REST API for adding URLs
- [ ] Optional: Notification on download completion

1. Define `.env` configuration
2. Create SQLite3 schema and migration script
3. Implement daemon process
4. Integrate yt-dlp download logic
5. Implement database update logic
6. Add logging and error handling
7. Test end-to-end workflow

## Optional Features
- Web UI for monitoring
- REST API for adding URLs
- Notification on download completion

---
This plan provides a clear roadmap for building the yt-dl-manager daemon. Next steps: set up configuration and database schema.
