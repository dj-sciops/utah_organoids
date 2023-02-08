from pathlib import Path

import datajoint as dj

from workflow.pipeline import induction


def get_ephys_root_data_dir() -> Path:
    return Path(dj.config.get("custom", {}).get("ephys_root_data_dir", None))


def get_raw_root_data_dir() -> Path:
    return Path(dj.config.get("custom", {}).get("raw_root_data_dir", None))


def get_processed_root_data_dir() -> Path:
    return Path(dj.config.get("custom", {}).get("processed_root_data_dir", None))


def get_session_dir(session_key: dict) -> Path:
    return Path(get_ephys_root_data_dir() / (induction.OrganoidExperiment & session_key).fetch1("experiment_dir"))

    
    
    
