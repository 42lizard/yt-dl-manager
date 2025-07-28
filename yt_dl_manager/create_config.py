"""Default configuration creation utilities for yt-dl-manager."""
import configparser
import logging
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir, user_downloads_dir

logger = logging.getLogger(__name__)

APP_NAME = "yt-dl-manager"
CONFIG_FILE_NAME = "config.ini"


def create_default_config(force=False):
    """Create a default configuration file with standard settings."""
    config_dir = Path(user_config_dir(APP_NAME, APP_NAME))
    data_dir = Path(user_data_dir(APP_NAME, APP_NAME))
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file_path = config_dir / CONFIG_FILE_NAME

    if config_file_path.exists() and not force:
        message = f"Config file already exists at: {config_file_path}\nUse --force to overwrite."
        logger.info("Config creation skipped: file already exists at %s", config_file_path)
        print(message)  # Keep as print for CLI user feedback
        return

    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'target_folder': str(Path(user_downloads_dir()) / APP_NAME),
        'database_path': str(data_dir / 'yt_dl_manager.db')
    }

    with open(config_file_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
    logger.info("Default configuration created at: %s", config_file_path)
    # Keep as print for CLI user feedback
    print(f"Default configuration created at: {config_file_path}")
