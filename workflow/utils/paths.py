from pathlib import Path

import datajoint as dj

from workflow.pipeline import induction


def get_ephys_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("ephys_root_data_dir", None)
    return Path(data_dir) if data_dir else None


def get_raw_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("raw_root_data_dir", None)
    return Path(data_dir) if data_dir else None


def get_processed_root_data_dir() -> Path:
    data_dir = dj.config.get("custom", {}).get("processed_root_data_dir", None)
    return Path(data_dir) if data_dir else None


def get_subject_directory(experiment_key: dict) -> Path:
    return (
        get_ephys_root_data_dir() / induction.OrganoidExperiment & experiment_key
    ).fetch1("experiment_dir")
