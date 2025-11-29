import json
import os
from pathlib import Path
from typing import Optional

APP_DIR_NAME = 'cb_pdf_converter'
MAPPINGS_FILENAME = 'mappings.json'


def get_config_dir() -> str:
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    cfg = os.path.join(base, APP_DIR_NAME)
    Path(cfg).mkdir(parents=True, exist_ok=True)
    return cfg


def mappings_path() -> str:
    return os.path.join(get_config_dir(), MAPPINGS_FILENAME)


def load_mappings() -> Optional[dict]:
    path = mappings_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as fh:
            return json.load(fh)
    except Exception:
        return None


def save_mappings(template: dict, *, overwrite: bool = False) -> bool:
    """Save the mapping template. If overwrite is False and file exists, do not overwrite and return False."""
    path = mappings_path()
    if os.path.exists(path) and not overwrite:
        return False
    try:
        with open(path, 'w') as fh:
            json.dump(template, fh, indent=2)
        return True
    except Exception:
        return False
