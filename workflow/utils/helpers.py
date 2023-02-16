from typing import Any, Iterator

import numpy as np
from element_interface.utils import find_full_path

from workflow.utils.paths import get_ephys_root_data_dir, get_session_dir


def get_probe_info(session_key: dict[str, Any]) -> dict[str, Any]:
    """Find probe.yaml in a session folder

    Args:
        session_key (dict[str, Any]): session key

    Returns:
        dict[str, Any]: probe meta information
    """
    import yaml

    experiment_dir = find_full_path(
        get_ephys_root_data_dir(), get_session_dir(session_key)
    )

    probe_meta_file = next(experiment_dir.glob("probe*"))

    with open(probe_meta_file, "r") as f:
        return yaml.safe_load(f)


def array_generator(arr: np.array, chunk_size: int = 10):
    """Generates an array at a specified chunk

    Args:
        arr (np.array): 1d numpy array
        chunk_size (int, optional): Size of the output array. Defaults to 10.

    Yields:
        Iterator[np.array]: generator object
    """
    start_ind = end_ind = 0

    while end_ind < arr.shape[0]:
        
        end_ind += chunk_size

        yield arr[start_ind:end_ind]

        start_ind += chunk_size

