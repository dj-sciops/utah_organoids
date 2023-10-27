import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import datajoint as dj
import numpy as np
import yaml
from element_interface.utils import dict_to_uuid

from workflow import REL_PATH_INBOX
from workflow.utils.paths import get_raw_root_data_dir, get_repo_dir

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


def ingest_experiment():
    """Insert entries into the culture.Experiment."""
    from workflow.pipeline import culture

    # Read from experiment.yaml
    try:
        from workflow.support import FileManifest

        organoid_yml = Path(
            (
                FileManifest & f'remote_fullpath LIKE "{REL_PATH_INBOX}%probe.yaml"'
            ).fetch1("file")
        )
    except:
        organoid_yml = Path(get_repo_dir()) / "data/organoids.yml"
    with open(organoid_yml, "r") as f:
        organoid_info: list[dict] = yaml.safe_load(f)
    culture.Experiment.insert(
        organoid_info, skip_duplicates=True, ignore_extra_fields=True
    )


def ingest_probe() -> None:
    from workflow.pipeline import probe

    """Fetch probe meta information from probe.yml file in the ephys root directory to populate probe schema."""

    # Read from probe.yaml
    try:
        from workflow.support import FileManifest

        probe_yml = Path(
            (
                FileManifest & f'remote_fullpath LIKE "{REL_PATH_INBOX}%probe.yaml"'
            ).fetch1("file")
        )
    except:
        probe_yml = get_repo_dir() / "data/probe.yml"

    with open(probe_yml, "r") as f:
        probe_list: list[dict] = yaml.safe_load(f)

    for probe_info in probe_list:
        probe_type = probe_info["config"]["probe_type"]

        if {"probe_type": probe_type} not in probe.ProbeType.proj():
            electrode_layouts: dict[str, Any] = probe.build_electrode_layouts(
                **probe_info["config"]
            )

            probe.ProbeType.insert1(probe_info["config"], ignore_extra_fields=True)

            probe.ProbeType.Electrode.insert(electrode_layouts)

            electrode_keys = [
                {"probe_type": e["probe_type"], "electrode": e["electrode"]}
                for e in electrode_layouts
            ]
            electrode_config_hash = dict_to_uuid(
                {k["electrode"]: k for k in electrode_keys}
            )
            electrode_list = sorted([k["electrode"] for k in electrode_keys])
            electrode_gaps = (
                [-1]
                + np.where(np.diff(electrode_list) > 1)[0].tolist()
                + [len(electrode_list) - 1]
            )
            electrode_config_name = "; ".join(
                [
                    f"{electrode_list[start + 1]}-{electrode_list[end]}"
                    for start, end in zip(electrode_gaps[:-1], electrode_gaps[1:])
                ]
            )

            electrode_config_key = {"electrode_config_hash": electrode_config_hash}

            probe.ElectrodeConfig.insert1(
                electrode_config_key
                | {
                    "probe_type": probe_type,
                    "electrode_config_name": electrode_config_name,
                }
            )
            probe.ElectrodeConfig.Electrode.insert(
                [
                    electrode_config_key
                    | {
                        "probe_type": probe_type,
                        "electrode": e,
                        "channel": ch,
                    }
                    for ch, e in get_channel_to_electrode_map().items()
                ]
            )

        probe.Probe.insert1(
            {
                "probe": probe_info["serial_number"],
                "probe_type": probe_type,
                "probe_comment": probe_info["comment"],
            },
            skip_duplicates=True,
        )


def ingest_ephys_files(organoid_key: dict[str, Any] = {}) -> None:
    from workflow.pipeline import culture, ephys

    prev_dir = None

    file_list = []

    for organoid in (culture.Experiment & organoid_key).fetch(
        as_dict=True, order_by="organoid_id"
    ):
        organoid_dir = get_raw_root_data_dir() / organoid["experiment_directory"]

        if organoid_dir == prev_dir:
            continue

        ingested_files = set(
            [
                Path(file).name
                for file in (
                    ephys.EphysRawFile & f"parent_folder = '{organoid_dir}'"
                ).fetch("file_path")
            ]
        )

        data_files = set([Path(file).name for file in organoid_dir.rglob("*.rhd")])

        for file in data_files.difference(ingested_files):
            filename_prefix, start_time = re.search(
                r"(.*)_(\d{6}_\d{6})", file
            ).groups()

            start_time = np.datetime64(datetime.strptime(start_time, "%y%m%d_%H%M%S"))

            file_list.append(
                {
                    "file_path": (Path(organoid_dir.name) / file).as_posix(),
                    "acq_software": {".rhd": "Intan", ".rhs": "Intan"}[
                        Path(file).suffix
                    ],
                    "file_time": start_time,
                    "parent_folder": organoid_dir.name,
                    "filename_prefix": filename_prefix,
                    "file": organoid_dir / file,
                }
            )

        prev_dir = organoid_dir

    ephys.EphysRawFile.insert(file_list, skip_duplicates=True)
    dj.logger.info(
        f"{len(file_list)} files have been inserted into ephys.EphysRawFile table"
    )


def ingest_ephys_session() -> None:
    """Insert entries into the ephys.EphysSession and ephys.EphysSessionProbe."""
    from workflow.pipeline import ephys

    # Read from ephys_session.yml
    try:
        from workflow.support import FileManifest

        session_yml = Path(
            (
                FileManifest
                & f'remote_fullpath LIKE "{REL_PATH_INBOX}%ephys_session.yaml"'
            ).fetch1("file")
        )
    except:
        session_yml = Path(get_repo_dir()) / "data/ephys_session.yml"

    with open(session_yml, "r") as f:
        session_list: list[dict] = yaml.safe_load(f)

    ephys.EphysSession.insert(
        session_list, skip_duplicates=True, ignore_extra_fields=True
    )

    ephys.EphysSessionProbe.insert(
        [
            session_info.pop("session_probe") | session_info
            for session_info in session_list
        ],
        skip_duplicates=True,
        ignore_extra_fields=True,
    )
