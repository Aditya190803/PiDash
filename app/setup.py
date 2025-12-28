import json
import os
from typing import Dict, Optional

SETUP_FILE_ENV = 'SETUP_CONFIG_FILE'
DEFAULT_SETUP_FILE = 'setup_config.json'


def _setup_file_path() -> str:
    return os.getenv(SETUP_FILE_ENV, DEFAULT_SETUP_FILE)


def load_setup() -> Dict:
    path = _setup_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_setup(cfg: Dict) -> None:
    path = _setup_file_path()
    with open(path, 'w') as fh:
        json.dump(cfg, fh, indent=2)


def ensure_upload_folder(folder: str):
    # Create folder if needed and make sure it's absolute
    if not folder:
        return
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)
    return folder
