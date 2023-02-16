from datetime import datetime, timedelta

import datajoint as dj
import numpy as np
from element_interface.intanloader import load_file

from workflow import db_prefix
from workflow.pipeline import ephys, induction, probe
from workflow.utils.helpers import get_probe_info
from workflow.utils.paths import get_session_dir

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
        # Fetch probe meta information from the session directory
        probe_info = get_probe_info(key)

        # Populate the probe schema
        # Fill in dummy parameters including probe config
        electrode_layouts = probe.build_electrode_layouts(**probe_info["config"])

        probe.ProbeType.insert1(
            dict(probe_type=probe_info["type"]), skip_duplicates=True
        )

        probe.ProbeType.Electrode.insert(electrode_layouts, skip_duplicates=True)

        probe.Probe.insert1(
            dict(
                probe=probe_info["serial_number"],
                probe_type=probe_info["type"],
                probe_comment=probe_info["comment"],
            ),
            skip_duplicates=True,
        )

        # Populate ephys.ProbeInsertion
        # Fill in dummy probe config
        insertion_number = 0
        ephys.ProbeInsertion.insert1(
            {
                **key,
                "insertion_number": insertion_number,
                "probe": probe_info["serial_number"],
            },
            skip_duplicates=True,
        )

        # Get the session data path
        session_dir = get_session_dir(key)
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
                econfig = ephys.generate_electrode_config(
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
            timestamps = start_time + (data["t"] - data["t"][0])[::DS_FACTOR] * timedelta(seconds=1)
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
        for ch, lfp_trace in zip(lfp_channels, lfp_amp):
            ephys.LFP.Electrode.insert1(
                {
                    **key,
                    **probe_electrodes[probe_info["channel_to_electrode_map"][ch]],
                    "insertion_number": insertion_number,
                    "lfp": lfp_trace,
                },
                allow_direct_insert=True,
            )
