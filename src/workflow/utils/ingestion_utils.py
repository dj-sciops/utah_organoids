from __future__ import annotations

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

El2ROW = np.array(El2ROW) - 1  # 0-based indexing


def get_channel_to_electrode_map(port_id: str | None = None) -> dict[str, int]:
    """Returns dictionary of channel to electrode number mapping (channel : electrode)

    Args:
        port_id (str | None): 'A', 'B', 'C', 'D'

    Returns:
        dict[str, int]: channel to electrode number mapping.
    """
    if port_id in ["A", "B", "C", "D"]:
        channel_to_electrode_map = {
            f"{port_id}-{value:03}": key for key, value in enumerate(El2ROW)
        }
    elif port_id is None:
        channel_to_electrode_map = {str(value): key for key, value in enumerate(El2ROW)}
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
        organoid_yml = Path(get_repo_dir()) / "data/experiment.yml"
    with open(organoid_yml, "r") as f:
        organoid_info: list[dict] = yaml.safe_load(f)
    culture.Experiment.insert(
        organoid_info, skip_duplicates=True, ignore_extra_fields=True
    )
    culture.ExperimentDirectory.insert(
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
        probe_list: list[dict] = yaml.safe_load(f).pop("probes")

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

    """Insert entries into the ephys.EphysRawFile."""

    prev_dir = None

    file_list = []

    for organoid_dir in np.unique(
        (culture.ExperimentDirectory & organoid_key).fetch("experiment_directory")
    ):
        organoid_dir = get_raw_root_data_dir() / organoid_dir

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


def create_sessions(
    experiment_key: dict[str, Any], session_type=str, duration_in_minutes: int = 30
) -> list[dict]:
    """Creates a list of session dictionaries for a given experiment.

    Args:
        experiment_key (dict[str, Any]): A key fetched from culture.Experiment.
        duration_in_minutes (int, optional): The duration of each session in minutes. Defaults to 30 minutes.

    Returns:
        list[dict]: Entries to be inserted into ephys.EphysSession and ephys.EphysSessionProbe tables.

    Example:
        >>> from workflow.pipeline import culture
        >>> key = (culture.Experiment & "organoid_id='O13'").fetch("KEY")[0]
        >>> session_list = create_sessions(key, session_type="spike_sorting", duration_in_minutes=30)
        >>> ephys.EphysSession.insert(session_list, ignore_extra_fields=True)
        >>> ephys.EphysSessionProbe.insert(
            [session_info.pop("session_probe") | session_info for session_info in session_list],
            ignore_extra_fields=True,
        )
    """
    import datetime

    from workflow.pipeline import culture

    assert session_type in [
        "spike_sorting",
        "lfp",
        "both",
    ], "session_type must be either 'spike_sorting', 'lfp', 'both'."

    exp_key = (culture.Experiment & experiment_key).proj("experiment_end_time").fetch1()

    # Load ephys_experiment.yml
    session_yml = Path(get_repo_dir()) / "data/ephys_session.yml"
    with open(session_yml, "r") as f:
        experiment_list: list[dict] = yaml.safe_load(f)

    try:
        exp_info = next(
            exp
            for exp in experiment_list
            if (exp["organoid_id"] == exp_key["organoid_id"])
            and (exp["start_time"] == str(exp_key["experiment_start_time"]))
        )
    except StopIteration:
        raise Exception("Experiment info not found from experiment.yml")

    session_list: list[dict[str, Any]] = []
    session_end = None

    # Create sessions within the experiment duration
    while True:
        session_start = session_end or exp_key["experiment_start_time"]

        if session_start >= exp_key["experiment_end_time"]:
            break

        session_end = min(
            session_start + datetime.timedelta(minutes=duration_in_minutes),
            exp_key["experiment_end_time"],
        )

        exp_info["experiment_start_time"] = exp_info["start_time"]
        session_info = exp_info.copy()
        session_info["start_time"] = session_start
        session_info["end_time"] = session_end
        session_info["session_type"] = session_type
        session_info["duration"] = (session_end - session_start).total_seconds() / 60

        session_list.append(session_info)

    return session_list


def auto_insert_sessions(
    experiment_key: dict,
    session_info: dict,
    session_type: str,
    duration_in_minutes: int,
):
    """Insert sessions created from create_sessions

    Args:
        experiment_key (dict)
        session_info (dict)
        session_type (str): 'lft', 'spike_sorting', 'both'
        duration_in_minutes (int): session duration (min)

    Examples:
        >>> experiment_key = dict(
            organoid_id="O13",
            experiment_start_time="2023-06-08 19:05:00",
            )

        >>> session_info = dict(
            organoid_id="O13",
            experiment_start_time="2023-06-08 19:05:00",
            insertion_number=0,
            start_time="2023-06-08 19:10:00",
            end_time="2023-06-09 19:15:00",
            session_type="lfp",  # "lfp" or "spike_sorting"
            probe="Q983",  # probe serial number
            port_id="A",  # Port ID ("A", "B", etc.)
            used_electrodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],  # electrodes used for the session
            )
        >>> auto_insert_sessions(experiment_key, session_info, session_type="lfp", duration_in_minutes=15)
    """

    from workflow.pipeline import ephys

    # Insert the session
    session_list = create_sessions(
        experiment_key,
        session_type=session_type,
        duration_in_minutes=duration_in_minutes,
    )
    ephys.EphysSession.insert(
        session_list, ignore_extra_fields=True, skip_duplicates=True
    )
    ephys.EphysSessionProbe.insert(
        [
            session_info.pop("session_probe") | session_info
            for session_info in session_list
        ],
        ignore_extra_fields=True,
        skip_duplicates=True,
    )
