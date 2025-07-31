"""Configuration management for yt-dl-manager."""
import configparser
from typing import Optional
from pathlib import Path
from platformdirs import user_config_dir

APP_NAME = "yt-dl-manager"
CONFIG_FILE_NAME = "config.ini"


def get_config_path():
    """Get the path to the configuration file."""
    config_dir = Path(user_config_dir(APP_NAME, APP_NAME))
    return config_dir / CONFIG_FILE_NAME


def load_config():
    """Load configuration from file."""
    config_parser = configparser.ConfigParser()
    config_file_path = get_config_path()
    config_parser.read(config_file_path)
    return config_parser


def get_language_preference() -> Optional[str]:
    """Get language preference from configuration.

    Returns:
        Language code ('en', 'de') or None for auto-detection.
    """
    try:
        return config.get('DEFAULT', 'language', fallback=None)
    except (configparser.Error, AttributeError):
        return None


def set_language_preference(language: Optional[str]) -> None:
    """Set language preference in configuration.

    Args:
        language: Language code ('en', 'de') or None for auto-detection.
    """
    config_file_path = get_config_path()

    # Ensure DEFAULT section exists
    if 'DEFAULT' not in config:
        config['DEFAULT'] = {}

    if language is None:
        # Remove language setting to use auto-detection
        config.remove_option('DEFAULT', 'language')
    else:
        config.set('DEFAULT', 'language', language)

    # Write back to file
    config_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


config = load_config()
