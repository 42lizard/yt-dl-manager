"""Default configuration creation utilities for yt-dl-manager."""
import configparser
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir, user_downloads_dir

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
        print(
            f"Config file already exists at: {config_file_path}\nUse --force to overwrite.")
        return

    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'TARGET_FOLDER': str(Path(user_downloads_dir()) / APP_NAME),
        'DATABASE_PATH': str(data_dir / 'yt_dl_manager.db')
    }

    with open(config_file_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
    print(f"Default configuration created at: {config_file_path}")
