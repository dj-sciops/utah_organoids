import datajoint as dj
import pathlib


def get_ephys_root_data_dir():
    return dj.config.get("custom", {}).get("ephys_root_data_dir", None)


def get_processed_root_data_dir():
    data_dir = dj.config.get("custom", {}).get("ephys_processed_data_dir", None)
    return pathlib.Path(data_dir) if data_dir else None


def get_ephys_root_data_dir():
    return dj.config.get("custom", {}).get("ephys_root_data_dir", None)
