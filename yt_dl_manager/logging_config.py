"""Logging configuration for yt-dl-manager."""

import logging
import sys
from pathlib import Path
from platformdirs import user_log_dir

APP_NAME = "yt-dl-manager"


def setup_logging(level=logging.INFO):
    """Set up logging configuration for the application."""
    # Create logs directory
    log_dir = Path(user_log_dir(APP_NAME, APP_NAME))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "yt-dl-manager.log"

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler for warnings and errors
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    return log_file


def get_logger(name):
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
