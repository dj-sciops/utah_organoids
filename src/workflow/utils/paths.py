from pathlib import Path
import datajoint as dj

from element_interface.utils import find_full_path
from workflow.pipeline import culture
import subprocess


def get_raw_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("raw_root_data_dir", None)
    return Path(data_dir) if data_dir else None


def get_processed_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("processed_root_data_dir", None)
    return Path(data_dir) if data_dir else None


def get_ephys_root_data_dir() -> Path:
    return get_raw_root_data_dir()


def get_organoid_directory(experiment_key: dict) -> Path:
    from workflow.pipeline import culture

    return find_full_path(
        get_ephys_root_data_dir(),
        (culture.Organoid & experiment_key).fetch1("experiment_directory"),
    )


def get_repo_dir() -> Path:
    """Get get root directory path"""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE
    )
    return Path(result.stdout.decode().strip())
