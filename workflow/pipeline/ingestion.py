from datetime import datetime, timedelta
from typing import Any, Iterator

import datajoint as dj
import numpy as np
from element_interface import intan_loader as intan
from element_interface.utils import find_full_path

from workflow import db_prefix
from workflow.pipeline import ephys, induction, probe
from workflow.utils.paths import get_ephys_root_data_dir, get_session_dir

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

        # Get the session data path
        session_dir = get_session_dir(key)
        data_dirs = sorted(list(session_dir.glob("[!probe]*")))

        # Load data
        timestamp_concat = lfp_mean_concat = lfp_amp_concat = np.array(
            [], dtype=np.float64
        )  # initialize

        for dir_ in data_dirs:
            data = intan.load_rhs(dir_)

            if "base" in str(dir_):  # Get meta information from the baseline session
                lfp_channels = [ch for ch in data["recordings"] if ch.startswith("amp")]
                lfp_sampling_rate = data["header"]["sample_rate"]

                # Get used channels for the session
                used_channels = [
                    "".join(channel.split("-")[1:])
                    for channel in data["recordings"]
                    if channel.startswith("amp")
                ]

                used_channels = [
                    int(channel[1:])
                    if channel.startswith("B")
                    else int(channel[1:]) + 16
                    for channel in used_channels
                ]  # this had to be hard-coded for now.

                # Populate probe.ElectrodeConfig and probe.ElectrodeConfig.Electrode
                econfig = ephys.generate_electrode_config(
                    probe_type=probe_info["type"],
                    electrode_keys=[
                        {"probe_type": probe_info["type"], "electrode": c}
                        for c in used_channels
                    ],
                )

            # Concatenate timestamps
            start_time = "".join(dir_.stem.split("_")[-2:])
            start_time = datetime.strptime(start_time, "%y%m%d%H%M%S")
            timestamps = start_time + data["timestamps"] * timedelta(seconds=1)
            timestamp_concat = np.concatenate((timestamp_concat, timestamps), axis=0)

            # Concatenate LFP traces
            lfp_amp = np.array(
                [
                    data["recordings"][d]
                    for d in data["recordings"]
                    if d.startswith("amp")
                ]
            )
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
                ).total_seconds(),
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

        # Populate ephys.LFP.Electrode
        electrode_query = (
            probe.ProbeType.Electrode
            * probe.ElectrodeConfig.Electrode
            * ephys.EphysRecording
            & key
        )

        lfp_channel_ind = [
            electrode for electrode in data["recordings"] if electrode.startswith("amp")
        ]

        for recorded_site in lfp_channels:
            ephys.LFP.Electrode.insert1(
                {**key, "lfp": data["recordings"][recorded_site]},
                allow_direct_insert=True,
            )


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


def array_generator(arr: np.array, chunk_size: int = 10) -> Iterator[np.array]:
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
        new_arr = arr[start_ind:end_ind]

        yield new_arr
        start_ind += chunk_size


def downsample_arr(
    arr: np.array, ds_factor: int = 10, selected_ind: int = 0
) -> np.array:
    """Function for downsampling an array

    Args:
        arr (np.array): 1d numpy array
        ds_factor (int, optional): Downsampling factor. Defaults to 10. If 10, 20kHz will be downsampled to 2kHz.
        selected_ind (int, optional): Select which index to keep. Defaults to 0 (first index).

    Returns:
        np.array: Final downsampled array.
    """
    if arr.shape[0] < ds_factor:
        raise NotImplementedError("Array is smaller than the downsampling factor")

    assert selected_ind < ds_factor, "selected_ind should be < ds_factor"

    downsampled_arr = []

    for new_arr in array_generator(arr, chunk_size=ds_factor):
        if new_arr.shape[0] <= selected_ind:
            selected_ind = -1
        downsampled_arr.append(new_arr[selected_ind])

    return np.array(downsampled_arr)
