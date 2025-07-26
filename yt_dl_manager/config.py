"""Configuration management for yt-dl-manager."""
import configparser
from pathlib import Path
from platformdirs import user_config_dir

APP_NAME = "yt-dl-manager"
CONFIG_FILE_NAME = "config.ini"

def get_config_path():
    """Get the path to the configuration file."""
    config_dir = Path(user_config_dir(APP_NAME, APP_NAME))
    return config_dir / CONFIG_FILE_NAME

def load_config():
    """Load configuration from file, creating default if needed."""
    config_parser = configparser.ConfigParser()
    config_file_path = get_config_path()
    if not config_file_path.exists():
        # If config file doesn't exist, create a default one
        from .create_config import create_default_config  # pylint: disable=import-outside-toplevel
        create_default_config()
    config_parser.read(config_file_path)
    return config_parser

config = load_config()
