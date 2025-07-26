import configparser
from pathlib import Path
from platformdirs import user_config_dir

APP_NAME = "yt-dl-manager"
CONFIG_FILE_NAME = "config.ini"

def create_default_config():
    config_dir = Path(user_config_dir(APP_NAME, APP_NAME))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file_path = config_dir / CONFIG_FILE_NAME

    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'TARGET_FOLDER': 'downloads',
        'DATABASE_PATH': 'yt_dl_manager.db'
    }

    with open(config_file_path, 'w') as configfile:
        config.write(configfile)
    print(f"Default configuration created at: {config_file_path}")

if __name__ == "__main__":
    create_default_config()
