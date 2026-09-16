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
        return load_config().get('DEFAULT', 'language', fallback=None)
    except (configparser.Error, OSError):
        return None


def set_language_preference(language: Optional[str]) -> None:
    """Set language preference in configuration.

    Args:
        language: Language code ('en', 'de') or None for auto-detection.
    """
    config_file_path = get_config_path()

    config = load_config()

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


class ConfigurationError(ValueError):
    """Configuration needed by a command is missing or invalid."""


def load_paths(*names):
    """Read and validate only the paths required by this command."""
    path = get_config_path()
    try:
        parser = configparser.ConfigParser()
        with path.open(encoding='utf-8') as config_file:
            parser.read_file(config_file)
        paths = {}
        for name in names:
            value = parser.get('DEFAULT', name, fallback='').strip()
            if not value or '\0' in value:
                raise ConfigurationError(f"Missing or invalid '{name}' in {path}.")
            paths[name] = Path(value).expanduser()
        return paths
    except FileNotFoundError as error:
        raise ConfigurationError(
            "Config file not found. Please run 'yt-dl-manager init' to create one."
        ) from error
    except (configparser.Error, OSError, UnicodeError) as error:
        raise ConfigurationError(f"Cannot read configuration {path}: {error}") from error
