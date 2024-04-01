import subprocess
from pathlib import Path
from typing import Any, Literal

import datajoint as dj
from appdirs import user_cache_dir
from element_interface.utils import find_full_path


def _local_cache_data_dir(box: Literal["inbox", "outbox"]) -> Path:
    from workflow import REL_PATH_INBOX, REL_PATH_OUTBOX

    relpath = REL_PATH_INBOX if box == "inbox" else REL_PATH_OUTBOX
    data_dir = Path(user_cache_dir()) / relpath
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_raw_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("raw_root_data_dir")
    return Path(data_dir) if data_dir else _local_cache_data_dir("inbox")


def get_processed_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("processed_root_data_dir")
    return Path(data_dir) if data_dir else _local_cache_data_dir("outbox")


def get_ephys_root_data_dir() -> Path:
    return get_raw_root_data_dir()


def get_organoid_directory(organoid_key: dict[str, Any]) -> Path:
    from workflow.pipeline import culture

    return find_full_path(
        get_ephys_root_data_dir(),
        (culture.ExperimentDirectory & organoid_key).fetch1("experiment_directory"),
    )


def get_repo_dir() -> Path:
    """Get root directory path"""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE
    )
    return Path(result.stdout.decode().strip())
