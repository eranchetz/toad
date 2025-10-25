from pathlib import Path

from xdg_base_dirs import xdg_config_home, xdg_data_home


APP_NAME = "toad"


def get_data() -> Path:
    """Return (possibly creating) the application data directory."""
    path = xdg_data_home() / APP_NAME
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_config() -> Path:
    """Return (possibly creating) the application config directory."""
    path = xdg_config_home() / APP_NAME
    path.mkdir(exist_ok=True, parents=True)
    return path
