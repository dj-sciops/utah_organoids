import datajoint as dj
from datetime import timedelta, datetime, timezone
import numpy as np
import scipy.stats
from scipy.signal import find_peaks
import json
import tempfile
from pathlib import Path

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

    key_source = (
        culture.Experiment
        & "organoid_id in ('MB05', 'MB06', 'MB07', 'MB08', 'E9', 'E10', 'E11', 'E12', 'O25', 'O26', 'O27', 'O28')"
    )

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
    threshold_uv: decimal(5,1)  # uV threshold for spike detection
    ---
    peak_sign: enum('pos', 'neg', 'both')  # peak sign for spike detection
    fs: float  # sampling frequency in Hz
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
        spike_indices: longblob  # spike indices in samples
        spike_amp: longblob    # spike amplitudes in uV
        """

    key_source = MUAEphysSession & "start_time >= '2024-09-07'"

    threshold_uV = 50  # 50 uV
    peak_sign = "both"

    def make(self, key):
        execution_time = datetime.now(timezone.utc)

        start_time, end_time = (MUAEphysSession & key).fetch1("start_time", "end_time")

        port_id = (MUAEphysSession & key).fetch1("port_id")
        parent_folder = (culture.ExperimentDirectory & key).fetch1(
            "experiment_directory"
        )

        si_recording = _get_si_recording(start_time, end_time, parent_folder, port_id)

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
                "fs": fs,
                "execution_duration": 0,
            }
        )

        for ch_idx, ch_id in enumerate(si_recording.channel_ids):
            # channel trace in uV
            trace = np.squeeze(
                si_recording.get_traces(channel_ids=[ch_id], return_scaled=True)
            )
            # median absolute deviation
            noise_level = scipy.stats.median_abs_deviation(trace, scale="normal")
            # spike detection
            threshold_uV = max(threshold_uV, 5 * noise_level)
            if peak_sign == "neg":
                spk_ind, spk_amp = find_peaks(
                    -trace, height=threshold_uV, distance=refractory_samples
                )
                spk_amp = -spk_amp["peak_heights"]
            elif peak_sign == "both":
                spk_ind, spk_amp = find_peaks(
                    np.abs(trace), height=threshold_uV, distance=refractory_samples
                )
                spk_amp = trace[spk_ind]
            else:
                spk_ind, spk_amp = find_peaks(
                    trace, height=threshold_uV, distance=refractory_samples
                )

            self.Channel.insert1(
                dict(
                    **key,
                    channel_idx=ch_idx,
                    channel_id=ch_id,
                    spike_count=len(spk_ind),
                    spike_rate=len(spk_ind) / duration,
                    noise_level=noise_level,
                    spike_indices=spk_ind,
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


@schema
class MUATracePlot(dj.Computed):
    definition = """
    -> MUASpikes
    ---
    spike_rate_threshold: float  # spike rate threshold for channel selection
    execution_duration: float  # execution duration in hours
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> MUASpikes.Channel
        ---
        mean_waveform: longblob
        trace_plot: longblob
        waveform_plot: attach
        """

    spike_rate_threshold = 0.5

    key_source = MUASpikes & {"threshold_uv": 50} & (
        MUASpikes.Channel & f"spike_rate >= {spike_rate_threshold}"
    )

    def make(self, key):
        execution_time = datetime.now(timezone.utc)

        start_time, end_time = (MUAEphysSession & key).fetch1("start_time", "end_time")
        port_id = (MUAEphysSession & key).fetch1("port_id")
        parent_folder = (culture.ExperimentDirectory & key).fetch1(
            "experiment_directory"
        )
        si_recording = _get_si_recording(start_time, end_time, parent_folder, port_id)
        # Preprocess the recording
        si_recording = si.preprocessing.bandpass_filter(
            recording=si_recording, freq_min=300, freq_max=6000
        )
        si_recording = si.preprocessing.common_reference(
            recording=si_recording, operator="median"
        )

        fs = si_recording.get_sampling_frequency()
        times = si_recording.get_times()
        title = f"{key['organoid_id']} | {key['start_time']}"
        spk_rate_thres = self.spike_rate_threshold

        self.insert1(
            {
                **key,
                "spike_rate_threshold": spk_rate_thres,
                "execution_duration": 0,
            }
        )

        tmp_dir = tempfile.TemporaryDirectory()
        peak_sign = (MUASpikes & key).fetch1("peak_sign")
        chn_query = MUASpikes.Channel & key & f"spike_rate >= {spk_rate_thres}"
        for chn_data in chn_query.fetch(as_dict=True):
            ch_id = si_recording.channel_ids[chn_data["channel_idx"]]
            trace = np.squeeze(
                si_recording.get_traces(channel_ids=[ch_id], return_scaled=True)
            )
            spk_ind = chn_data["spike_indices"]

            if peak_sign == "both":
                # get the "neg" peaks only
                spk_ind = spk_ind[np.where(chn_data["spike_amp"] < 0)[0]]

            title_ = title + f" | ChnID: {ch_id}"
            # waveform plot
            # compute average waveform - 2ms before and after the spike
            pad_len = int(2e-3 * fs)
            wfs = []
            for idx in spk_ind:
                if idx - pad_len >= 0 and idx + pad_len < len(trace):
                    wfs.append(trace[idx - pad_len : idx + pad_len])
            mean_wf = np.mean(np.vstack(wfs), axis=0)

            wf_fig = _plot_mean_waveform(mean_wf, fs, title_)

            # format a string into a filename compatible string
            filename = title_.replace(" ", "").replace(":", "-").replace("|", "-")
            filepath = Path(tmp_dir.name) / f"{filename}_waveform.png"
            wf_fig.savefig(filepath)

            trace_fig = _plot_trace_with_peaks(
                trace, times, spk_ind, f"ch_{ch_id}", title_
            )

            self.Channel.insert1(
                {
                    **key,
                    "channel_idx": chn_data["channel_idx"],
                    "trace_plot": trace_fig.to_json(),
                    "mean_waveform": mean_wf,
                    "waveform_plot": filepath,
                }
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

        tmp_dir.cleanup()


def _get_si_recording(start_time, end_time, parent_folder, port_id):
    """
    Get the spikeinterface recording object for the given time range.
    """
    import intanrhdreader

    files, file_times, acq_softwares = (
        ephys.EphysRawFile
        & {"parent_folder": parent_folder}
        & f"file_time >= '{start_time}'"
        & f"file_time < '{end_time}'"
    ).fetch("file_path", "file_time", "acq_software", order_by="file_time")

    acq_software = acq_softwares[0]

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

    si_recording = _build_si_recording_object(files, acq_software)

    si_recording = si_recording.select_channels(
        si_recording.channel_ids[port_indices]
    )  # select only the port data
    return si_recording


def _build_si_recording_object(files, acq_software="intan"):
    """
    Build the spikeinterface recording object from the given files.
    Args:
        files: list of file full paths
        acq_software: acquisition software name

    Returns:
        si_recording: SI recording object
    """
    si_recording = None

    si_extractor: si.extractors.neoextractors = (
        si.extractors.extractorlist.recording_extractor_full_dict[
            acq_software.replace(" ", "").lower()
        ]
    )  # data extractor object

    # Read data. Concatenate if multiple files are found.
    for file_path in (
        find_full_path(ephys.get_ephys_root_data_dir(), f) for f in files
    ):
        if not si_recording:
            stream_name = [
                s for s in si_extractor.get_streams(file_path)[0] if "amplifier" in s
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
    return si_recording


def _plot_trace_with_peaks(
    trace, times, peak_indices, trace_name="trace", title="Spike Detection"
):
    from plotly import graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=trace, mode="lines", name=trace_name))
    fig.add_trace(
        go.Scatter(
            x=times[peak_indices],
            y=trace[peak_indices],
            mode="markers",
            marker=dict(color="red"),
            name="spike",
        )
    )
    # add y-axis title as `uV` and x-axis title as `Time (s)`
    fig.update_layout(
        title=title,
        yaxis_title="Amplitude (uV)",
        xaxis_title="Time (s)",
    )

    return fig


def _plot_mean_waveform(mean_wf, fs, title="Mean Waveform"):
    import matplotlib.pyplot as plt

    times = np.arange(-len(mean_wf) / 2, len(mean_wf) / 2) / fs
    times *= 1e3  # times in ms
    fig, ax = plt.subplots()
    ax.plot(times, mean_wf)
    ax.set_title(title)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (uV)")
    return fig
