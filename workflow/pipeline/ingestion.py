from datetime import datetime, timedelta
from pathlib import Path

import datajoint as dj
import numpy as np
import yaml
from intanrhsreader import load_file

from workflow import db_prefix
from workflow.pipeline import ephys, induction, probe
from workflow.utils.helpers import get_probe_info
from workflow.utils.paths import get_ephys_root_data_dir, get_session_directory

logger = dj.logger
schema = dj.schema(db_prefix + "ingestion")


@schema
class EphysIngestion(dj.Imported):
    definition = """
    -> induction.OrganoidExperiment
    ---
    ingestion_time  : datetime    # Stores the start time of ephys data ingestion
    """

    def make(self, key):
        # Get the session data path
        session_dir = get_session_directory(
            key
        )  #! fetch the ephys raw table, restricted by the start and end of the ephys session
        data_files = sorted(list(session_dir.glob("*.rhs")))

        # Load data
        timestamp_concat = lfp_mean_concat = lfp_amp_concat = np.array(
            [], dtype=np.float64
        )  # initialize

        DS_FACTOR = 10  # downsampling factor
        econfig = {}

        for file in data_files:
            data = load_file(file)

            if not econfig:
                lfp_sampling_rate = data["header"]["sample_rate"] / DS_FACTOR

                lfp_channels = [
                    ch["native_channel_name"] for ch in data["amplifier_channels"]
                ]

                # Populate probe.ElectrodeConfig and probe.ElectrodeConfig.Electrode
                econfig = probe.generate_electrode_config(
                    probe_type=probe_info["type"],
                    electrode_keys=[
                        {
                            "probe_type": probe_info["type"],
                            "electrode": probe_info["channel_to_electrode_map"][c],
                        }
                        for c in lfp_channels
                    ],
                )

            # Concatenate timestamps
            start_time = "".join(file.stem.split("_")[-2:])
            start_time = datetime.strptime(start_time, "%y%m%d%H%M%S")
            timestamps = start_time + (data["t"] - data["t"][0])[
                ::DS_FACTOR
            ] * timedelta(seconds=1)
            timestamp_concat = np.concatenate((timestamp_concat, timestamps), axis=0)

            # Concatenate LFP traces
            lfp_amp = data["amplifier_data"][:, ::DS_FACTOR]

            del data

            lfp_mean = np.mean(lfp_amp, axis=0)
            lfp_mean_concat = np.concatenate((lfp_mean_concat, lfp_mean), axis=0)
            if lfp_amp_concat.size == 0:
                lfp_amp_concat = lfp_amp
            else:
                lfp_amp_concat = np.hstack((lfp_amp_concat, lfp_amp))

        # Populate ephys.EphysRecording
        ephys.EphysRecording.insert1(
            {
                **key,
                **econfig,
                "insertion_number": insertion_number,
                "acq_software": "Intan",
                "sampling_rate": lfp_sampling_rate,
                "recording_datetime": (induction.OrganoidExperiment() & key).fetch1(
                    "experiment_datetime"
                ),
                "recording_duration": (
                    timestamp_concat[-1] - timestamp_concat[0]
                ).total_seconds(),  # includes potential gaps
            },
            allow_direct_insert=True,
        )

        # Populate ephys.LFP
        ephys.LFP.insert1(
            {
                **key,
                "insertion_number": insertion_number,
                "lfp_sampling_rate": lfp_sampling_rate,
                "lfp_time_stamps": timestamp_concat,
                "lfp_mean": lfp_mean_concat,
            },
            allow_direct_insert=True,
        )

        electrode_query = (
            probe.ElectrodeConfig.Electrode * ephys.EphysRecording & key
        ).fetch("electrode_config_hash", "probe_type", "electrode", as_dict=True)

        probe_electrodes = {q["electrode"]: q for q in electrode_query}

        # Populate ephys.LFP.Electrode
        for ch, lfp_trace in zip(lfp_channels, lfp_amp_concat):
            ephys.LFP.Electrode.insert1(
                {
                    **key,
                    **probe_electrodes[probe_info["channel_to_electrode_map"][ch]],
                    "insertion_number": insertion_number,
                    "lfp": lfp_trace,
                },
                allow_direct_insert=True,
            )


def ingest_probe() -> None:
    """Fetch probe meta information from probe.yaml file in the ephys root directory to populate probe schema."""

    probe_info = get_probe_info()

    for probe_config_id, probe_config in probe_info.items():
        probe.ProbeType.insert1(
            dict(probe_type=probe_config["config"]["probe_type"]), skip_duplicates=True
        )

        electrode_layouts = probe.build_electrode_layouts(**probe_config["config"])

        probe.ProbeType.Electrode.insert(electrode_layouts, skip_duplicates=True)

        probe.Probe.insert1(
            dict(
                probe=probe_config["serial_number"],
                probe_type=probe_config["config"]["probe_type"],
                probe_comment=probe_config["comment"],
            ),
            skip_duplicates=True,
        )

        probe.ElectrodeConfig.insert1(
            {
                "probe_config_id": probe_config_id,
                "probe_type": probe_config["config"]["probe_type"],
                "channel_to_electrode_map": probe_config["channel_to_electrode_map"],
            }
        )

        probe.ElectrodeConfig.Electrode.insert(
            [
                {
                    "probe_config_id": probe_config_id,
                    "probe_type": probe_config["config"]["probe_type"],
                    "electrode": e,
                    "channel_id": ch,
                }
                for ch, e in probe_config["channel_to_electrode_map"].items()
            ]
        )
