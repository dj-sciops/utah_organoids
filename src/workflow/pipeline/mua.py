import datajoint as dj
from datetime import timedelta, datetime, timezone
import numpy as np
import scipy.stats
from scipy.signal import find_peaks

import spikeinterface as si
from spikeinterface import extractors, preprocessing

from element_interface.utils import find_full_path

from workflow import DB_PREFIX
from workflow.pipeline import culture, ephys


schema = dj.schema(DB_PREFIX + "mua")


@schema
class MUAEphysSession(dj.Computed):
    definition = """
    -> culture.Experiment
    start_time                  : datetime
    ---
    end_time                    : datetime  
    port_id: char(2)  # e.g. A, B, C, ... 
    unique index (organoid_id, start_time, end_time)
    """

    key_source = culture.Experiment & "organoid_id in ('MB05', 'MB06', 'MB07', 'MB08', 'E9', 'E10', 'E11', 'E12', 'O25', 'O26', 'O27', 'O28')"

    session_duration = timedelta(minutes=1)

    def make(self, key):
        exp_start, exp_end = (culture.Experiment & key).fetch1(
            "experiment_start_time", "experiment_end_time"
        )

        # Figure out `Port ID` from the existing EphysSession
        if not (ephys.EphysSessionProbe & key):
            raise ValueError(
                f"No EphysSessionProbe found for the {key} - cannot determine the port ID"
            )

        port_id = set((ephys.EphysSessionProbe & key).fetch("port_id"))
        if len(port_id) > 1:
            raise ValueError(
                f"Multiple Port IDs found for the {key} - cannot determine the port ID"
            )
        port_id = port_id.pop()

        parent_folder = (culture.ExperimentDirectory & key).fetch1(
            "experiment_directory"
        )

        # Get all Ephys Raw Files
        ephys_raw_times = (
            ephys.EphysRawFile
            & {"parent_folder": parent_folder}
            & f"file_time BETWEEN '{exp_start}' AND '{exp_end}'"
        ).fetch("file_time")

        ephys_sessions = []
        for session_start in ephys_raw_times:
            session_end = session_start + self.session_duration
            if session_end <= exp_end:
                ephys_sessions.append(
                    dict(
                        **key,
                        start_time=session_start,
                        end_time=session_end,
                        port_id=port_id,
                    )
                )

        self.insert(ephys_sessions)


@schema
class MUASpikes(dj.Computed):
    definition = """
    -> MUAEphysSession
    ---
    threshold_uv: float  # uV threshold for spike detection
    peak_sign: enum('pos', 'neg', 'both')  # peak sign for spike detection
    execution_duration: float  # execution duration in hours
    """

    class Channel(dj.Part):
        definition = """
        -> master
        channel_idx: int  # channel index
        ---
        channel_id: varchar(64)  # channel id
        spike_count: int    # number of spikes
        spike_rate: float   # Hz
        noise_level: float  # Median Absolute Deviation of the signal
        spike_times: longblob  # spike times in seconds
        spike_amp: longblob    # spike amplitudes in uV
        """

    key_source = MUAEphysSession & "start_time >= '2024-09-07'"

    threshold_uV = 25  # 25 uV
    peak_sign = "neg"

    def make(self, key):
        import intanrhdreader

        execution_time = datetime.now(timezone.utc)

        start_time, end_time = (MUAEphysSession & key).fetch1("start_time", "end_time")

        port_id = (MUAEphysSession & key).fetch1("port_id")
        parent_folder = (culture.ExperimentDirectory & key).fetch1(
            "experiment_directory"
        )

        files, file_times, acq_softwares = (
            ephys.EphysRawFile
            & {"parent_folder": parent_folder}
            & f"file_time >= '{start_time}'"
            & f"file_time < '{end_time}'"
        ).fetch("file_path", "file_time", "acq_software", order_by="file_time")

        acq_software = acq_softwares[0]

        si_extractor: si.extractors.neoextractors = (
            si.extractors.extractorlist.recording_extractor_full_dict[
                acq_software.replace(" ", "").lower()
            ]
        )  # data extractor object

        # read intan header
        with open(find_full_path(ephys.get_ephys_root_data_dir(), files[0]), "rb") as f:
            header = intanrhdreader.read_header(f)
        port_indices = np.array(
            [
                ind
                for ind, ch in enumerate(header["amplifier_channels"])
                if ch["port_prefix"] == port_id
            ]
        )  # get the row indices of the port

        si_recording = None
        # Read data. Concatenate if multiple files are found.
        for file_path in (
            find_full_path(ephys.get_ephys_root_data_dir(), f) for f in files
        ):
            if not si_recording:
                stream_name = [
                    s
                    for s in si_extractor.get_streams(file_path)[0]
                    if "amplifier" in s
                ][0]
                si_recording: si.BaseRecording = si_extractor(
                    file_path, stream_name=stream_name
                )
            else:
                si_recording: si.BaseRecording = si.concatenate_recordings(
                    [
                        si_recording,
                        si_extractor(file_path, stream_name=stream_name),
                    ]
                )

        si_recording = si_recording.select_channels(
            si_recording.channel_ids[port_indices]
        )  # select only the port data

        # Preprocess the recording
        si_recording = si.preprocessing.bandpass_filter(
            recording=si_recording, freq_min=300, freq_max=6000
        )
        si_recording = si.preprocessing.common_reference(
            recording=si_recording, operator="median"
        )

        fs = si_recording.get_sampling_frequency()
        duration = si_recording.get_duration()
        refractory_period = 0.002  # 2 ms
        refractory_samples = int(refractory_period * fs)

        threshold_uV = self.threshold_uV
        peak_sign = self.peak_sign

        self.insert1(
            {
                **key,
                "threshold_uv": threshold_uV,
                "peak_sign": peak_sign,
                "execution_duration": 0,
            }
        )

        for ch_idx, ch_id in enumerate(si_recording.channel_ids):
            # channel trace in uV
            trace = np.squeeze(
                si_recording.get_traces(channel_ids=[ch_id], return_scaled=True)
            )

            if peak_sign == "neg":
                trace = -trace

            # median absolute deviation
            noise_level = scipy.stats.median_abs_deviation(trace, scale="normal")

            # spike detection
            threshold_uV = max(threshold_uV, 5 * noise_level)
            spk_ind, spk_amp = find_peaks(
                trace, height=threshold_uV, distance=refractory_samples
            )

            spk_times = spk_ind / fs
            spk_amp = spk_amp["peak_heights"]

            self.Channel.insert1(
                dict(
                    **key,
                    channel_idx=ch_idx,
                    channel_id=ch_id,
                    spike_count=len(spk_times),
                    spike_rate=len(spk_times) / duration,
                    noise_level=noise_level,
                    spike_times=spk_times,
                    spike_amp=spk_amp,
                )
            )

        self.update1(
            {
                **key,
                "execution_duration": (
                    datetime.now(timezone.utc) - execution_time
                ).total_seconds()
                / 3600,
            }
        )


def _plot_trace_with_peaks(trace, peak_indices):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot(trace)
    ax.plot(peak_indices, trace[peak_indices], "ro")
    return fig
