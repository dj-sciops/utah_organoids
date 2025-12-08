# Import Modules
import datajoint as dj
from workflow import DB_PREFIX
from workflow.pipeline import culture, ephys, mua, analysis, probe

import numpy as np
import bottleneck as bn
from scipy.signal import find_peaks, gaussian_filter1d, butter, sosfiltfilt, hilbert, coherence
from datetime import datetime, timedelta


# Set up schema (connects to database and manages table creation)
schema = dj.schema(DB_PREFIX + "frame")

# Define Lookup Tables
@schema
class NumElectrodesInside(dj.Lookup):
    """
    Number of electrodes inside the organoid for each session (defined by organoid images).
    """

    definition = """
    organoid_id: varchar(4) # e.g. O17
    ---
    num_electrodes: int # Number of electrodes inside the organoid
    """
    contents = [
        ("O09", 32), ("O10", 16), ("O11", 20), ("O12", 14), # Control Batch 1
        ("O13", 25), ("O14", 13), ("O15", 11), ("O16", 11), # Control Batch 2
        ("O17", 22), ("O18", 19), ("O19", 20), ("O20", 17), # GBM Batch 1
        ("O21", 18), ("O22", 21), ("O23", 22), ("O24", 23), # Control Batch 3
        ("O25", 20), ("O26", 32), ("O27", 26), ("O28", 24), # GBM Batch 2
        ("O29", 22), ("O30", 20), ("O31", 20), ("O32", 20), # Control Batch 4
    ]

@schema
class TimeFrameParamset(dj.Lookup):
    """
    Time frame extraction parameters for LFP and spike analyses. 
    """

    definition = """
    frame_param_idx: int # Unique identifier for the frame parameter set
    ---
    num_frames: int # Number of frames to extract
    min_per_frame: int # Length of each frame in minutes
    """
    contents = [
        (1, 12, 5),  # 12 frames at 5 minutes each (1 hour total)
        (2, 4, 15), # 4 frames at 15 minutes each (1 hour total)
        (3, 8, 15), # 8 frames at 15 minutes each (2 hours total)
    ]

@schema
class BurstDetectionParamset(dj.Lookup):
    """
    Parameters for burst detection with multi-unit population activity.
    """

    definition = """
    burst_param_idx: int # Unique identifier for the burst detection parameter set
    ---
    gaus_len_ms: float # Gaussian kernel length in milliseconds
    boxcar_len_ms: float # Boxcar kernel length in milliseconds
    detection_threshold: float # Threshold for burst detection in standard deviations
    min_distance_ms: float # Minimum distance between bursts in milliseconds
    """
    contents = [
        (1, 100.0, 20.0, 2.0, 1000.0), # Parameters used in Sharf et al. 2021
    ]

# Define Manual Tables
@schema
class AnalysisBoundaries(dj.Manual):
    """
    Time boundaries for analysis of each organoid session.
    """

    definition = """ 
    -> culture.Experiment
    start_boundary     : datetime # Start datetime for analysis
    end_boundary       : datetime # End datetime for analysis
    frame_param_idx   : int     # Reference to TimeFrameParamset
    """

# Define Computed Tables
@schema
class ActiveTimeFrames(dj.Computed):
    """
    Identify the "num_frames" most active time frames (length "sec_per_frame") within the analysis boundaries for each organoid session.
    """

    definition = """
    -> AnalysisBoundaries
    start_time: datetime # Start of active time frame
    end_time: datetime   # End of active time frame
    ---
    frame_firing_rate: list # Firing rates for each frame
    """

    def make(self, key):
        
        # fetch MUA parameters
        spike_rates, start_times, channel_ids = (mua.MUASpikes.Channel & 
                                                 f"organoid_id='{key['organoid_id']}'" &
                                                 f"start_time BETWEEN '{key['start_boundary']}' AND '{key['end_boundary']}'"
                                                 ).fetch('spike_rate', 'start_time', 'channel_idx')
        
        # convert channel ids to electrode indices
        electrode_ids = map_channel_to_electrode(channel_ids)

        # create population spike rate time series
        unique_start_times = np.unique(start_times)
        num_elec_inside = (NumElectrodesInside & f"organoid_id='{key['organoid_id']}'").fetch1('num_electrodes')

        # create full time vector from recording start to end (1 minute increments)
        time_vector = np.arange(min(unique_start_times.astype("datetime64[m]")), max(unique_start_times.astype("datetime64[m]"))+np.timedelta64(1, 'm'), np.timedelta64(1, 'm')) # full array of recording timeline (needed to account for missing data)
        population_firing_vector = np.zeros(time_vector.shape)

        # loop through start times and insert data into population firing vector
        for start_time in unique_start_times:

            time_bool = (start_times == start_time)

            # only consider electrodes inside organoid
            elec_bool = (electrode_ids < num_elec_inside)

            # sum valid electrodes for each time window (minute)
            time_index = np.where(time_vector == start_time.astype("datetime64[m]"))[0][0]
            population_firing_vector[time_index] = np.sum(spike_rates[time_bool & elec_bool])

        # filter population firing vector - boxcar with the length of min_per_frame
        min_per_frame = (TimeFrameParamset & key).fetch1('min_per_frame')
        population_firing_vector = bn.move_mean(population_firing_vector, window=min_per_frame, min_count=1)

        # find active frames
        frame_indices, properties = find_peaks(population_firing_vector, height=0, distance=min_per_frame)
        frame_amplitudes = properties['peak_heights']

        # remove boundary peaks (these will raise an error when trying to extract burst windows)
        boundary_bool = (min_per_frame <= frame_indices)

        frame_indices = frame_indices[boundary_bool]
        frame_amplitudes = frame_amplitudes[boundary_bool]

        # find most active regions -> extract windows
        num_frames = (TimeFrameParamset & key).fetch1('num_frames')
        peak_indices = np.argsort(frame_amplitudes)[-num_frames:]  # indexes of the most active peaks
        frame_bounds = np.array([np.array([-min_per_frame, 0]) + frame_indices[peak_idx] for peak_idx in peak_indices]) # indexes (per minute)

        # loop through bounds -> extract info -> insert into table
        for frame_idx in frame_bounds:

            # find insert metrics
            start_time, end_time = np.unique(start_times[np.isin(start_times.astype("datetime64[m]"), time_vector[frame_idx])])
            frame_firing_rate = np.mean(population_firing_vector[frame_idx[0]:frame_idx[1]])
            
            # find probe information
            # Figure out `Port ID` from the existing EphysSessionProbe
            port_id, probe = set((ephys.EphysSessionProbe & key).fetch("port_id", "probe"))

            # Figure out `Port ID` from the existing EphysSession
            if not (ephys.EphysSessionProbe & key):
                raise ValueError(
                    f"No EphysSessionProbe found for the {key} - cannot determine the port ID"
                )

            # Check if there are multiple port IDs for the same experiment, if so, it needs to be fixed in the EphysSessionProbe table
            if len(ephys.EphysSessionProbe & key) > 1:
                raise ValueError(
                    f"Multiple Port IDs found for the {key} - cannot determine the port ID"
                )
            port_id = port_id.pop()
            probe = probe.pop()
            
            # insert into lfp ephys session (needed for downstream analyses)
            ephys.EphysSession.insert1({
                "organoid_id": key['organoid_id'],
                "experiment_start_time": key['experiment_start_time'],
                "insertion_number": 0,
                "start_time": start_time,
                "end_time": end_time,
                "session_type": "lfp"
            }, skip_duplicates=True)
            ephys.EphysSessionProbe.insert1({
                "organoid_id": key['organoid_id'],
                "experiment_start_time": key['experiment_start_time'],
                "insertion_number": 0,
                "start_time": start_time,
                "end_time": end_time,
                "probe": probe,
                "port_id": port_id,
                "used_electrodes": []
            }, skip_duplicates=True)


            # insert into frame table
            self.insert1({
                **key,
                'start_time': start_time,
                'end_time': end_time,
                'frame_firing_rate': frame_firing_rate,
            })

@schema
class PopulationBursts(dj.Computed):
    """
    Detect population bursts within an active time frame using specified burst detection parameters.
    """

    definition = """
    -> ActiveTimeFrames
    burst_param_idx: int # Reference to BurstDetectionParamset
    ---
    burst_indices: np.ndarray # Indices of detected bursts within the time frame
    burst_peak_heights: np.ndarray # Peak heights of detected bursts
    burst_bounds: np.ndarray # Start and end indices of detected bursts (firing rate >= 10% of peak height)
    burst_spike_array: np.ndarray # Single electrode spike array for each burst (num_bursts x num_electrodes x time_window)
    """

    def make(self, key):

        # define parameters
        fs = 20000 # sampling frequency in Hz
        burst_extract_dur = np.timedelta64(1, 's') # time for extracting burst spike array (+ and - from peak)
        burst_bound_thresh = 0.1 # threshold for defining burst bounds (percentage of peak height)

        # Fetch MUA parameters within the frame
        spike_indices, start_times, channel_ids = (mua.MUASpikes.Channel & 
                                                 f"organoid_id='{key['organoid_id']}'" &
                                                 f"start_time BETWEEN '{key['start_time']}' AND '{key['end_time']}'"
                                                 ).fetch('spike_idx', 'start_time', 'channel_idx')
        
        # convert channel ids to electrode indices
        electrode_ids = map_channel_to_electrode(channel_ids)

        # get array of all spike times (relative to frame start)
        start_ms = (start_times - key['start_time']).astype('timedelta64[ms]') / np.timedelta64(1, 'ms') # ms from frame start
        rel_spike_times_ms = spike_indices / fs / (np.timedelta64(1,'ms')/np.timedelta64(1,'s')) 
        spike_times_ms = rel_spike_times_ms + start_ms

        # remove electrodes outside organoid
        num_elec_inside = (NumElectrodesInside & f"organoid_id='{key['organoid_id']}'").fetch1('num_electrodes')
        elec_bool = (electrode_ids < num_elec_inside)
        spike_times_ms = spike_times_ms[elec_bool]

        # create population spike time series (1 ms bins)
        time_bins = np.arange(0, (key['end_time'] - key['start_time']).astype('timedelta64[ms]') / np.timedelta64(1, 'ms') + 1) # 1 ms bins
        population_spike_series, _ = np.histogram(spike_times_ms, bins=time_bins)

        # convert spike series to firing rate
        population_firing_rate = population_spike_series * 1000 # convert to spikes per second

        # smooth firing rate with Gaussian and Boxcar kernels
        # fetch burst detection parameters
        gaus_len_ms, boxcar_len_ms, detection_threshold, min_distance_ms = (BurstDetectionParamset & key).fetch1(
            'gaus_len_ms', 'boxcar_len_ms', 'detection_threshold', 'min_distance_ms'
        )
        # boxcar kernel
        boxcar_samples = int(boxcar_len_ms / np.timedelta64(1, 'ms'))
        population_firing_rate = bn.move_mean(population_firing_rate, window=boxcar_samples, min_count=1)

        # Gaussian kernel
        sigma = gaus_len_ms / np.timedelta64(1, 'ms')  
        truncate = 4
        population_firing_rate = gaussian_filter1d(population_firing_rate, sigma=sigma, truncate=truncate, mode="reflect")

        # detect spike bursts
        min_height = detection_threshold * np.std(population_firing_rate)
        min_distance_samples = min_distance_ms / np.timedelta64(1, 'ms')  
        
        # find peaks
        burst_indices, properties = find_peaks(population_firing_rate, height=min_height, distance=min_distance_samples)
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
        for i, (index, height) in enumerate(zip(burst_indices, burst_peak_heights)):

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
                elec_spike_times = spike_times_ms[electrode_ids == elec_idx]

                # find spikes within burst window
                burst_spike_times = elec_spike_times[((index-num_burst_samples) <= elec_spike_times) & (elec_spike_times <= (index+num_burst_samples))]

                # convert to indices within burst spike array
                burst_spike_indices = (burst_spike_times - (index-num_burst_samples)).astype(int)
                burst_spike_array[i, elec_idx, burst_spike_indices] = True
        burst_bounds = np.array(burst_windows)

        # insert into table
        self.insert1({
            **key,
            'burst_indices': burst_indices,
            'burst_peak_heights': burst_peak_heights,
            'burst_bounds': burst_bounds,
            'burst_spike_array': burst_spike_array,
        })

@schema
class Coherence(dj.Computed):
    """
    Compute pairwise coherence between electrodes within an active time frame.
    """

    definition = """
    -> ActiveTimeFrames
    -> ephys.LFP.Trace
    """

    class Connectivity(dj.Part):
        """
        Pairwise coherence between electrodes (LFP signals).
        """
        definition = """
        -> master
        electrode_A: int # Electrode in coherence calculation
        electrode_B: int # Electrode in coherence calculation
        --- 
        f: np.ndarray # Frequency values
        coherence: np.ndarray # Coherence values between electrode A and B
        """
    
    class Synchrony(dj.Part):
        """
        Coherence between each electrode LFP signal to each frequency band signal
        """
        definition = """
        -> master
        -> analysis.SpectralBand
        electrode: int # Electrode in synchrony calculation
        ---
        f: np.ndarray # Frequency values
        synchrony: np.ndarray # Coherence between electrode LFP and frequency band signal
        """

    def make(self, key):

        # define parameters
        fs = 2500
        max_freq = 200 # Hz
        tw = 1
        nperseg = int(tw*fs) # samples per window

        # fetch Traces
        traces, electrode_ids, = ((analysis.LFPQC * ephys.LFP.Trace) & key).fetch("lfp", "electrode")

        # reorder electrode traces and remove electrodes outside organoid
        num_elec_inside = (NumElectrodesInside & f"organoid_id='{key['organoid_id']}'").fetch1('num_electrodes')
        ordered_traces = np.array([traces[electrode_ids == elec] for elec in range(num_elec_inside)])


        # define synchronny parameters
        order = 4
        nyquist = fs/2

        # apply low pass filter to each electrode trace
        lfp_traces = []
        for trace in ordered_traces:
            sos = butter(order, np.array([1, max_freq])/nyquist, btype='bandpass', output='sos')
            filtered = sosfiltfilt(sos, trace)

            lfp_traces.append(filtered)
        lfp_traces = np.array(lfp_traces)

        """ 
        Connectivity Analysis
        """

        # loop through electrodes and find coherence between adjacent electrode pairs
        for electrode_A in range(num_elec_inside):
            for electrode_B in range(num_elec_inside):

                # skip duplicate electrode pairings
                if electrode_A >= electrode_B:
                    continue
                
                # get traces
                el_A_trace = lfp_traces[electrode_A, :]
                el_B_trace = lfp_traces[electrode_B, :]

                # compute coherence
                f, Cxy = coherence(el_A_trace, el_B_trace, fs=fs, nperseg=nperseg)

                # remove frequencies greater than max_freq
                f = f[f <= max_freq]
                connectivity = Cxy[f <= max_freq]

                # insert into part table
                self.Connectivity.insert1({
                    **key,
                    'electrode_A': electrode_A,
                    'electrode_B': electrode_B,
                    'f': f,
                    'coherence': connectivity,
                })
        
        """
        Synchrony Analysis
        """

        # loop through electrodes and find coherence between lfp signal and freq bands
        for elec in range(num_elec_inside):
     
            # get traces
            elec_trace = lfp_traces[elec, :]

            # loop through frequency bands and calculate coherence
            for band in (analysis.SpectralBand()).fetch(as_dict=True):

                # get signal of specific frequency band
                freq_cutoff = np.array([band['lower_freq']-1, band['upper_freq']+1]) # includes 1 Hz buffer
                sos = butter(order, freq_cutoff/nyquist, btype='bandpass', output='sos')
                filtered = sosfiltfilt(sos, elec_trace)

                # get magnitude of hilbert transform (doing instead of morlet wavelets)
                hilbert_signal = hilbert(filtered)
                freq_power_signal = np.abs(hilbert_signal) ** 2

                # find coherence between original signal and the power signal (for each frequency)
                f, Cxy = coherence(elec_trace, freq_power_signal, fs=fs, nperseg=nperseg)

                # remove frequencies greater than max_freq
                f = f[f <= max_freq]
                synchrony = Cxy[f <= max_freq]

                # insert into part table
                self.Synchrony.insert1({
                    **key,
                    'electrode': elec,
                    'band_name': band['band_name'],
                    'f': f,
                    'synchrony': synchrony,
                })
        
        # insert into main table
        self.insert1(key)

# Helpful Functions
def map_channel_to_electrode(channel_ids):

    electrode_mapping, channel_mapping = probe.ElectrodeConfig.Electrode.fetch("electrode", "channel_idx")

    # create lookup to convert
    lookup = np.empty(32, dtype=int)
    lookup[channel_mapping] = electrode_mapping

    # correctly map electrode indices
    electrode_ids = lookup[channel_ids]
    
    return electrode_ids