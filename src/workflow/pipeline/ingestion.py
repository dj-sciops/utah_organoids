import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import datajoint as dj
import numpy as np
import yaml

from workflow import REL_PATH_INBOX
from workflow.pipeline import culture, ephys, probe
from workflow.utils.helpers import get_channel_to_electrode_map
from workflow.utils.paths import get_raw_root_data_dir, get_repo_dir


def ingest_orgnoid():
    """Insert entries into the culture.OrganoidCulture and culture.Organoid table."""

    # Read from organoid.yaml
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
        organoid_info: list[dict] = yaml.safe_load(f)["organoid_culture"]
    culture.OrganoidCulture.insert(
        organoid_info, skip_duplicates=True, ignore_extra_fields=True
    )

    culture.Organoid.insert(
        [
            {
                "organoid_culture_id": organoid_culture["organoid_culture_id"],
                "organoid_id": organoid["organoid_id"],
                "experiment_type": organoid["experiment_type"],
                "experiment_directory": organoid["experiment_directory"],
            }
            for organoid_culture in organoid_info
            for organoid in organoid_culture.get("organoid")
        ],
        skip_duplicates=True,
    )


def ingest_probe() -> None:
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

            electrode_config_hash: dict[str, UUID] = ephys.generate_electrode_config(
                probe_type=probe_type,
                electrode_keys=[
                    {"probe_type": e["probe_type"], "electrode": e["electrode"]}
                    for e in electrode_layouts
                ],
            )

            probe.ProbeType.insert1({"probe_type": probe_type})

            probe.ProbeType.Electrode.insert(electrode_layouts)

            probe.ElectrodeConfig.insert1(
                electrode_config_hash
                | {
                    "probe_type": probe_type,
                    "electrode_config_name": "",
                }
            )
            probe.ElectrodeConfig.Electrode.insert(
                [
                    electrode_config_hash
                    | {
                        "probe_type": probe_type,
                        "electrode": e,
                        "channel_id": ch,
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
    prev_dir = None

    file_list = []

    for organoid in (culture.Organoid & organoid_key).fetch(
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
                    "organoid_culture_id": organoid["organoid_culture_id"],
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

    ephys.EphysSession.OrganoidRecording.insert(
        [
            session_info | organoid_recording
            for session_info in session_list
            for organoid_recording in session_info.pop("organoid_recording")
        ],
        skip_duplicates=True,
        ignore_extra_fields=True,
    )
