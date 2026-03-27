import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
import spikeinterface as si
from element_interface.utils import find_full_path
from element_array_ephys.ephys_no_curation import map_channel_to_electrode, get_probe_type
from scipy.signal import find_peaks
import bottleneck as bn
from scipy.ndimage import gaussian_filter1d

from workflow import DB_PREFIX
from workflow.pipeline import culture
from .ephys import ephys, probe

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
    key_source = culture.Experiment & ephys.EphysSessionProbe

    session_duration = timedelta(minutes=1)

    def make(self, key):
        raise NotImplementedError(
            "Manual insertion is required for `MUAEphysSession`. `Populate()` method is implemented but not currently in use."
        )

        exp_start, exp_end = (culture.Experiment & key).fetch1(
            "experiment_start_time", "experiment_end_time"
        )

        # Figure out `Port ID` from the existing EphysSessionProbe
        port_id = set((ephys.EphysSessionProbe & key).fetch("port_id"))

        # Figure out `Port ID` from the existing EphysSession
        if not (ephys.EphysSessionProbe & key):
            raise ValueError(
                f"No EphysSessionProbe found for the {key} - cannot determine the port ID"
            )

        # Check if there are multiple port IDs for the same experiment, if so, it needs to be fixed in the EphysSessionProbe table
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

        peak_sign = self.peak_sign

        self.insert1(
            {
                **key,
                "threshold_uv": self.threshold_uV,
                "peak_sign": peak_sign,
                "fs": fs,
                "execution_duration": 0,
            }
        )

        key["threshold_uv"] = self.threshold_uV

        for ch_idx, ch_id in enumerate(si_recording.channel_ids):
            # channel trace in uV
            trace = np.squeeze(
                si_recording.get_traces(channel_ids=[ch_id], return_in_uV=True)
            )
            # median absolute deviation
            noise_level = scipy.stats.median_abs_deviation(trace, scale="normal")
            # spike detection
            threshold_uV = max(self.threshold_uV, 5 * noise_level)
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
                "threshold_uv": self.threshold_uV,
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

    spike_rate_threshold = 100.0  # Hz, temporarily set high for testing/validation (default was 0.5 Hz)

    key_source = (
        MUASpikes
        & {"threshold_uv": 50}
        & (MUASpikes.Channel & f"spike_rate >= {spike_rate_threshold}")
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
                si_recording.get_traces(channel_ids=[ch_id], return_in_uV=True)
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

            if len(wfs) > 0:
                mean_wf = np.mean(np.vstack(wfs), axis=0)
            else:
                mean_wf = np.array([])

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
        plt.close("all")
        plt.clf()


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

    if len(acq_softwares) == 0:
        raise ValueError(
            f"No ephys files found for time range {start_time} to {end_time}"
        )

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

    # Check if recording is unsigned and convert if necessary
    # Please check the SI documentation for more details: https://spikeinterface.readthedocs.io/en/latest/how_to/unsigned_to_signed.html
    if str(si_recording.get_dtype()).startswith("u"):
        si_recording = si.preprocessing.unsigned_to_signed(si_recording)

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
    
    from spikeinterface.extractors.extractor_classes import recording_extractor_full_dict

    si_recording = None

    si_extractor = recording_extractor_full_dict[acq_software.replace(" ", "").lower()]

    # Read data. Concatenate if multiple files are found.
    for file_path in (
        find_full_path(ephys.get_ephys_root_data_dir(), f) for f in files
    ):
        # Get stream name for this file
        streams = si_extractor.get_streams(file_path)[0]
        amplifier_streams = [s for s in streams if "amplifier" in s]

        if not amplifier_streams:
            raise ValueError(f"No amplifier stream found in file: {file_path}")

        stream_name = amplifier_streams[0]

        if not si_recording:
            si_recording = si_extractor(file_path, stream_name=stream_name)
        else:
            si_recording = si.concatenate_recordings(
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
    times = np.arange(-len(mean_wf) / 2, len(mean_wf) / 2) / fs
    times *= 1e3  # times in ms
    fig, ax = plt.subplots()
    ax.plot(times, mean_wf)
    ax.set_title(title)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (uV)")
    return fig

"""
Generate Trace Plot
"""
@schema 
class TraceSession(dj.Manual):
    """
    Manual insert of MUA trace plotting sessions.
    """

    definition = """ 
    -> MUASpikes.Channel
    """

@schema
class TracePlot(dj.Computed):
    """
    Generate plot of the inserted MUA trace with detected spike peaks.
    """
    
    definition = """
    -> TraceSession
    ---
    electrode: int # electrode idx when mapped (tip=0)
    trace_plot: longblob  # Plot of trace with spike peaks (as json)
    """

    def make(self, key):

        # fetch MUA channel data
        start_time, channel_idx, spike_indices = (MUASpikes.Channel & key).fetch1("start_time", "channel_idx", "spike_indices")

        # get spike interface recording object
        port_id = (MUAEphysSession & key).fetch1("port_id")
        parent_folder = (culture.ExperimentDirectory & key).fetch1(
            "experiment_directory"
        )
        end_time = start_time + timedelta(minutes=1)  # 1 minute duration
        si_recording = _get_si_recording(start_time, end_time, parent_folder, port_id)

        # Preprocess the recording
        si_recording = si.preprocessing.bandpass_filter(
            recording=si_recording, freq_min=300, freq_max=6000
        )
        si_recording = si.preprocessing.common_reference(
            recording=si_recording, operator="median"
        )

        # get trace info
        times = si_recording.get_times()
        title = f"{key['organoid_id']} | {key['start_time']} | ChnID: {channel_idx}"

        # 
        ch_id = si_recording.channel_ids[channel_idx]
        trace = np.squeeze(
            si_recording.get_traces(channel_ids=[ch_id], return_scaled=True)
        )

        trace_fig = _plot_trace_with_peaks(
            trace, times, spike_indices, f"ch_{ch_id}", title
        )

        # get electrode
        probe_type = set((ephys.EphysSessionProbe * probe.Probe & f"organoid_id = '{key['organoid_id']}'").fetch('probe_type'))
        if len(probe_type) != 1:
            raise ValueError(f"Expected exactly one probe type for organoid_id='{key['organoid_id']}', found {len(probe_type)}")
        electrode = map_channel_to_electrode(probe_type.pop(), input_indices=np.array([channel_idx]))[0]

        self.insert1(
            {
                **key,
                "electrode": electrode,
                "trace_plot": trace_fig.to_json(),
            }
        )

"""
Population Bursts
"""

@schema
class BurstDetectionParamset(dj.Lookup):
    """
    Parameters for burst detection with multi-unit population activity.
    """

    definition = """
    burst_param_idx: int # Unique identifier for the burst detection parameter set
    ---
    gaus_len_ms: int # Gaussian kernel length in milliseconds
    boxcar_len_ms: int # Boxcar kernel length in milliseconds
    detection_threshold: float # Threshold for burst detection in standard deviations
    min_distance_ms: float # Minimum distance between bursts in milliseconds
    """
    contents = [
        (1, 100, 20, 2.0, 1000.0), # Parameters used in Sharf et al. 2021
    ]

@schema 
class BurstSession(dj.Manual):
    """
    Manual insert of burst detection sessions for population burst analysis.
    """

    definition = """ 
    -> ephys.EphysSession
    -> BurstDetectionParamset
    """

@schema
class PopulationBursts(dj.Computed):
    """
    Detect population bursts within a time frame using specified burst detection parameters.
    """

    definition = """
    -> BurstSession
    ---
    burst_indices: longblob # ms since start of detected bursts within the time frame
    burst_peak_heights: longblob # Peak heights of detected bursts
    burst_bounds: longblob # [-ms, +ms] relative to burst peak (firing rate >= 10%% of peak height)
    burst_spike_array: longblob # Single electrode spike array for each burst (num_bursts x num_electrodes x time_window)
    weighted_sttc: longblob # Spike time tiling coefficient across all electrodes weighted by number of spikes
    """

    def make(self, key):
        import neo
        import quantities as pq
        from elephant.spike_train_correlation import spike_time_tiling_coefficient

        # define parameters
        fs = 20000 # sampling frequency in Hz
        burst_extract_dur = np.timedelta64(1, 's') # time for extracting burst spike array (+ and - from peak)
        burst_bound_thresh = 0.1 # threshold for defining burst bounds (percentage of peak height)

        # Fetch MUA parameters within the frame
        spike_indices, start_times, channel_ids = (MUASpikes.Channel & 
                                                 f"organoid_id='{key['organoid_id']}'" &
                                                 f"start_time BETWEEN '{key['start_time']}' AND '{key['end_time']}'"
                                                 ).fetch('spike_indices', 'start_time', 'channel_idx')
        
        # check if we have spike indices for all times
        if len(np.unique(start_times)) < np.timedelta64(key['end_time'] - key['start_time'], 'm') / np.timedelta64(1,'m'):
            raise ValueError(f"Not all time windows have MUA spike data for {key} - cannot perform burst detection")

        # convert channel ids to electrode indices
        probe_type = get_probe_type(key)
        electrode_ids = map_channel_to_electrode(probe_type, input_indices=channel_ids)

        # get array of all spike times (relative to frame start)
        start_ms = (start_times - key['start_time']).astype('timedelta64[ms]') / np.timedelta64(1, 'ms') # ms from frame start
        rel_spike_times_ms = spike_indices / fs / (np.timedelta64(1,'ms')/np.timedelta64(1,'s')) 
        spike_times_ms = rel_spike_times_ms + start_ms

        # fetch electrode count from implantation image (source of truth)
        img_query = culture.OrganoidImplantationImage & {"organoid_id": key["organoid_id"]}
        if not img_query:
            raise ValueError(f"No OrganoidImplantationImage entry found for organoid_id='{key['organoid_id']}' - insert a row before running this computation")
        if len(img_query) > 1:
            raise ValueError(f"Multiple OrganoidImplantationImage entries found for organoid_id='{key['organoid_id']}' - expected exactly one")
        num_elec_inside = img_query.fetch1("num_electrodes_inside")
        if num_elec_inside is None:
            raise ValueError(f"num_electrodes_inside is not set in OrganoidImplantationImage for organoid_id='{key['organoid_id']}'")
        elec_bool = (electrode_ids >= 0) & (electrode_ids < num_elec_inside)

        # create population spike time series (1 ms bins)
        time_bins = np.arange(0, np.timedelta64(key['end_time'] - key['start_time'], 'ms') / np.timedelta64(1, 'ms') + 1) # 1 ms bins
        population_spike_series, _ = np.histogram(np.hstack(spike_times_ms[elec_bool]), bins=time_bins)

        # convert spike series to firing rate
        population_firing_rate = population_spike_series * 1000 # convert to spikes per second

        # smooth firing rate with Gaussian and Boxcar kernels
        # fetch burst detection parameters
        gaus_len_ms, boxcar_len_ms, detection_threshold, min_distance_ms = (BurstDetectionParamset & key).fetch1(
            'gaus_len_ms', 'boxcar_len_ms', 'detection_threshold', 'min_distance_ms'
        )
        # boxcar kernel
        population_firing_rate = bn.move_mean(population_firing_rate, window=boxcar_len_ms, min_count=1)

        # Gaussian kernel 
        truncate = 4
        population_firing_rate = gaussian_filter1d(population_firing_rate, sigma=gaus_len_ms, truncate=truncate, mode="reflect")

        # detect spike bursts
        min_height = detection_threshold * np.std(population_firing_rate)
        
        # find peaks
        burst_indices, properties = find_peaks(population_firing_rate, height=min_height, distance=min_distance_ms)
        burst_peak_heights = properties['peak_heights']

        # find burst bounds (start and end indices where firing rate >= 10% of peak height)

        # define burst extraction parameters
        num_burst_samples = int(burst_extract_dur / np.timedelta64(1,'ms')) # number of samples to extract from burst peak (+ and -)
        
        # remove boundary bursts (will raise an error when extracting burst windows)
        boundary_bool = (num_burst_samples <= burst_indices) & (burst_indices <= (len(population_firing_rate)-num_burst_samples))
        burst_indices = burst_indices[boundary_bool]
        burst_peak_heights = burst_peak_heights[boundary_bool]

        # find burst windows and create spike array
        burst_windows = []
        burst_spike_array = np.zeros((len(burst_indices), num_elec_inside, 2*num_burst_samples), dtype=bool)
        for burst_idx, (index, height) in enumerate(zip(burst_indices, burst_peak_heights)):

            # extract burst waveform
            waveform = population_firing_rate[index-num_burst_samples : index+num_burst_samples]

            # find burst specific window threshold
            window_thresh = burst_bound_thresh * height
            window = np.array([0, 0])

            # find number of indices adjacent to the burst peak are over the burst threshold
            i = 1
            while (waveform[num_burst_samples-i] >= window_thresh) & (num_burst_samples-i > 0): # make sure it doesn't exceed the number of extracted samples
                window[0] -= 1 # indices before burst peak
                i += 1
            i = 1
            while (waveform[num_burst_samples+i] >= window_thresh) & (num_burst_samples+i < len(waveform)-1):
                window[1] += 1 # indices after burst peak
                i += 1        
            
            burst_windows.append(window)

            # fill in spike array for each electrode
            for elec_idx in range(num_elec_inside):

                # get spike times for electrode
                elec_spike_times = np.hstack(spike_times_ms[electrode_ids == elec_idx])

                # find spikes within burst window
                burst_spike_times = elec_spike_times[((index-num_burst_samples) <= elec_spike_times) & (elec_spike_times < (index+num_burst_samples))]

                # convert to indices within burst spike array
                burst_spike_indices = (burst_spike_times - (index-num_burst_samples)).astype(int)
                burst_spike_array[burst_idx, elec_idx, burst_spike_indices] = True
        burst_bounds = np.array(burst_windows)

        # determine spike time tiling coefficient (functional connectivity) for each burst (weighted by spikes per pair)
        sttc_array = np.zeros((len(burst_indices), num_elec_inside, num_elec_inside))
        weight_array = np.zeros((len(burst_indices), num_elec_inside, num_elec_inside))

        dt = 5 # time window for STTC in ms
        t_stop = 2*num_burst_samples # total time window for spike trains in ms
        for b_idx in range(len(burst_indices)):
            for i in range(num_elec_inside):
                for j in range(i+1, num_elec_inside):
                    
                    # define spike times for each electrode within burst (in ms)
                    spike_times_i = np.where(burst_spike_array[b_idx, i, :])[0]
                    spike_times_j = np.where(burst_spike_array[b_idx, j, :])[0]

                    # skip if either electrode has no spikes in burst
                    if len(spike_times_i) == 0 or len(spike_times_j) == 0:
                        continue


                    # convert to spike trains (neo)
                    spiketrain_A = neo.SpikeTrain(spike_times_i, units='ms', t_stop=t_stop)
                    spiketrain_B = neo.SpikeTrain(spike_times_j, units='ms', t_stop=t_stop)

                    # calculate STTC
                    sttc = spike_time_tiling_coefficient(spiketrain_A, spiketrain_B, dt=dt*pq.ms)   
                    sttc_array[b_idx, i, j] = sttc

                    # calculate weight (number of spike pairs)
                    weight_array[b_idx, i, j] = len(spike_times_i) * len(spike_times_j)

        # determine weighted average STTC for each burst; NaN for bursts with no spike pairs
        total_weight = weight_array.sum(axis=(1, 2))
        weighted_sttc = np.where(
            total_weight > 0,
            (sttc_array * weight_array).sum(axis=(1, 2)) / total_weight,
            np.nan,
        )

        # insert into table
        self.insert1({
            **key,
            'burst_indices': burst_indices,
            'burst_peak_heights': burst_peak_heights,
            'burst_bounds': burst_bounds,
            'burst_spike_array': burst_spike_array,
            'weighted_sttc': weighted_sttc,
        })
        