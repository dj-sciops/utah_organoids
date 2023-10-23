from pathlib import Path

import numpy as np
import yaml

from workflow import REL_PATH_INBOX
from workflow.utils.paths import get_repo_dir

# fmt: off
El2ROW = [20, 5, 19, 6, 18, 7, 32, 9, 31, 10, 30, 11, 21, 4, 22, 3, 23, 2, 25, 16, 26, 15, 27, 14, 28, 13, 24, 1, 29, 12, 17, 8]  # array of row number for each electrode obtained from el2row.m
# fmt: on

electrode_to_row = np.array(El2ROW) - 1  # 0-based indexing


def get_channel_to_electrode_map(port_id: str | None = None) -> dict[str, int]:
    """Returns dictionary of channel to electrode number mapping (channel : electrode)

    Args:
        port_id (str | None): 'A', 'B', 'C', 'D'

    Returns:
        dict[str, int]: channel to electrode number mapping.
    """
    if port_id in ["A", "B", "C", "D"]:
        channel_to_electrode_map = {
            f"{port_id}-{value:03}": key for key, value in enumerate(electrode_to_row)
        }
    elif port_id is None:
        channel_to_electrode_map = {
            str(value): key for key, value in enumerate(electrode_to_row)
        }
    else:
        raise ValueError(f"Invalid port_id: {port_id}")

    # Sort by the key
    return {
        key: channel_to_electrode_map[key] for key in sorted(channel_to_electrode_map)
    }
