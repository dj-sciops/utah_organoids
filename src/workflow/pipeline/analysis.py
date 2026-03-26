import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import sys
import os
from datetime import datetime, timezone, timedelta
from scipy.stats import stats, chi2
from scipy.signal import coherence, butter, sosfiltfilt, hilbert, welch
from specparam import SpectralModel
from scipy.interpolate import interp1d
import plotly.tools as tls
import plotly.io as pio
from element_array_ephys.ephys_no_curation import map_channel_to_electrode, get_probe_type
from element_interface.utils import find_full_path
from tensorpac import Pac, PreferredPhase, EventRelatedPac
from tensorpac.utils import ITC, PeakLockedTF
from spikeinterface.extractors.extractor_classes import (
      recording_extractor_full_dict,
)      
from .ephys import ephys, probe
from workflow.pipeline import mua

from workflow import DB_PREFIX, ORG_NAME, WORKFLOW_NAME

schema = dj.schema(DB_PREFIX + "analysis")

logger = dj.logger


dj.config["stores"]["datajoint-blob"] = dict(
    protocol="s3",
    endpoint="s3.amazonaws.com:9000",
    bucket="dj-sciops",
    location=f"{ORG_NAME}_{WORKFLOW_NAME}/datajoint/blob",
    access_key=os.getenv("AWS_ACCESS_KEY", None),
    secret_key=os.getenv("AWS_ACCESS_SECRET", None),
)

"""
Spectral Analysis
"""

@schema
class SpectralBand(dj.Lookup):
    """
    Spectral bands defined by the lab.
    """

    definition = """
    band_name: varchar(16)
    ---
    lower_freq: float # (Hz)
    upper_freq: float # (Hz)
    """
    contents = [
        ("delta", 1.0, 4.0),
        ("theta", 4.0, 7.0),
        ("alpha", 8.0, 12.0),
        ("beta", 13.0, 30.0),
        ("gamma", 30.0, 50.0),
        ("highgamma1", 70.0, 110.0),
        ("highgamma2", 130.0, 200.0),
    ]


@schema
class LFPQC(dj.Computed):
    """
    Time-domain QC metrics for each LFP trace (per electrode).
    Includes variance, noise level, and waveform shape (skewness/kurtosis).
    """

    definition = """
    -> ephys.LFP.Trace
    ---
    lfp_std: float # Overall signal amplitude (spread, uV)
    lfp_noise_level: float # Median absolute deviation (noise level estimate, uV)
    lfp_skewness: float # Skewness of the voltage distribution (Asymmetry)
    lfp_kurtosis: float # Kurtosis of the voltage distribution (Tail heaviness)
    """

    def make(self, key):

        lfp = (ephys.LFP.Trace & key).fetch1("lfp")

        # Standard deviation (variance)
        lfp_std = float(np.std(lfp))

        # Median absolute deviation
        lfp_noise_level = float(stats.median_abs_deviation(lfp))

        # Waveform shape
        self.insert1(
            {
                **key,
                "lfp_std": lfp_std,
                "lfp_noise_level": lfp_noise_level,
                "lfp_skewness": stats.skew(lfp),
                "lfp_kurtosis": stats.kurtosis(lfp),
            }
        )


@schema
class SpectrogramParameters(dj.Lookup):
    definition = """
    param_idx: int
    ---
    window_size:     float    # Time in seconds
    overlap_size=0:  float    # Time in seconds
    description="":  varchar(64)
    """
    contents = [
        (0, 2.0, 1.0, "2s window, 50pct overlap (delta, theta, alpha)"),
        (1, 0.5, 0.25, "0.5s window, 50pct overlap (beta, gamma)"),
        (2, 0.25, 0.125, "0.25s window, 50pct overlap (high-gamma)"),
    ]


@schema
class LFPSpectrogram(dj.Computed):
    """Spectrograms and frequency-domain power metrics for each LFP trace."""

    definition = """
    -> ephys.LFP.Trace
    -> SpectrogramParameters
    ---
    delta_band_mean_power: float  # Average delta power (1-4 Hz) over entire recording (μV²/Hz)
    power_range_90pct: float      # 90pct spread of broadband amplitude envelope derived from spectrogram (a.u.)
    """

    class ChannelSpectrogram(dj.Part):
        definition = """
        -> master
        ---
        spectrogram: blob@datajoint-blob  # Spectrogram matrix (freq x time) (μV²/Hz)
        time: blob@datajoint-blob         # Time bins (s)
        frequency: blob@datajoint-blob    # Frequency bins (Hz)
        """

    class ChannelPower(dj.Part):
        """Power in each frequency band, per LFP trace."""

        definition = """
        -> master
        -> SpectralBand
        ---
        power_time_series: blob@datajoint-blob  # Power time series for this band (μV²/Hz)
        mean_power: float            # Mean band power (μV²/Hz)
        std_power: float             # Std dev of band power (μV²/Hz)
        """

    # @property
    # def key_source(self):
    #     # Use only the default param_idx for high-gamma windowing params for automated population
    #     return ephys.LFP.Trace * SpectrogramParameters & "param_idx=2"

    def make(self, key):
        # Load LFP trace and sampling rate
        lfp = (ephys.LFP.Trace & key).fetch1("lfp")
        fs = (ephys.LFP & key).fetch1("lfp_sampling_rate")

        # Spectrogram window parameters
        window_size, overlap_size = (SpectrogramParameters & key).fetch1(
            "window_size", "overlap_size"
        )
        nperseg = int(window_size * fs)
        noverlap = int(overlap_size * fs)

        # Compute spectrogram as Power Spectral Density (PSD) (μV²/Hz)
        freq, t, Sxx = signal.spectrogram(
            lfp,
            fs=fs,
            window="tukey",
            nperseg=nperseg,
            noverlap=noverlap,
            scaling="density",
            mode="psd",
        )

        # Insert temporary values for non-nullable secondary attributes; will update with computed metrics below.
        self.insert1(
            {
                **key,
                "delta_band_mean_power": 0.0,
                "power_range_90pct": 0.0,
            }
        )

        self.ChannelSpectrogram.insert1(
            {
                **key,
                "spectrogram": Sxx,
                "frequency": freq,
                "time": t,
            }
        )

        # Compute band power metrics
        band_powers = {}
        for band in (SpectralBand()).fetch(as_dict=True):
            band_mask = (freq >= band["lower_freq"]) & (freq < band["upper_freq"])
            band_power = (
                Sxx[band_mask].mean(axis=0) if band_mask.any() else np.zeros_like(t)
            )
            band_powers[band["band_name"]] = band_power

            self.ChannelPower.insert1(
                {
                    **key,
                    "band_name": band["band_name"],
                    "power_time_series": band_power,
                    "mean_power": band_power.mean(),
                    "std_power": band_power.std(),
                }
            )

        # Compute delta/alpha power ratio
        delta_power = band_powers.get("delta", np.zeros_like(t))

        # Compute session-level summary metrics
        amp_envelope = np.sqrt(np.mean(Sxx, axis=0))  # broadband RMS amplitude envelope
        power_range_90pct = float(
            np.percentile(amp_envelope, 95) - np.percentile(amp_envelope, 5)
        )

        # Insert final computed summary metrics
        self.update1(
            {
                **key,
                "delta_band_mean_power": delta_power.mean(),
                "power_range_90pct": power_range_90pct,
            }
        )

"""
Coherence Analysis
"""

@schema
class Coherence(dj.Computed):
    """
    Compute pairwise coherence between electrodes within an active time frame.
    """

    definition = """
    -> ephys.LFP
    ---
    execution_duration: float  # Time taken to compute coherence (in minutes)
    """

    class Connectivity(dj.Part):
        """
        Pairwise coherence between electrodes (LFP signals).
        """
        definition = """
        -> master
        electrode_a: int  # Electrode in coherence calculation
        electrode_b: int  # Electrode in coherence calculation
        ---
        f: longblob  # Frequency values
        coherence: longblob  # Coherence values between electrode A and B
        """
    
    class Synchrony(dj.Part):
        """
        Coherence between each electrode LFP signal to each frequency band signal
        """
        definition = """
        -> master
        -> SpectralBand
        electrode: int  # Electrode index
        ---
        f: longblob  # Frequency values
        synchrony: longblob  # Coherence between electrode LFP and frequency band signal
        """
        
    def make(self, key):

        execution_time = datetime.now(timezone.utc)

        # define parameters
        fs = 2500
        max_freq = 200 # Hz
        tw = 1
        nperseg = int(tw*fs) # samples per window

        # fetch traces
        traces = (ephys.LFP.Trace & key).fetch("lfp", order_by="electrode")

        # define synchronny parameters
        order = 4
        nyquist = fs/2

        # apply low pass filter to each electrode trace
        lfp_traces = []
        for trace in traces:
            sos = butter(order, np.array([1, max_freq])/nyquist, btype='bandpass', output='sos')
            filtered = sosfiltfilt(sos, trace)

            lfp_traces.append(filtered)
        lfp_traces = np.array(lfp_traces)

        # insert into parent table
        self.insert1(
            {
                **key,
                "execution_duration": 0, # placeholder
            }
        )

        """ 
        Connectivity Analysis
        """

        # loop through electrodes and find coherence between adjacent electrode pairs
        num_elec = lfp_traces.shape[0]
        for electrode_A in range(num_elec - 1):
            for electrode_B in range(electrode_A + 1, num_elec):
                
                # get traces
                el_A_trace = lfp_traces[electrode_A, :]
                el_B_trace = lfp_traces[electrode_B, :]

                # compute coherence
                f, Cxy = coherence(el_A_trace, el_B_trace, fs=fs, nperseg=nperseg)

                # remove frequencies greater than max_freq
                frequencies = f[f <= max_freq]
                connectivity = Cxy[f <= max_freq]

                # insert into part table
                self.Connectivity.insert1({
                    **key,
                    'electrode_a': electrode_A,
                    'electrode_b': electrode_B,
                    'f': frequencies,
                    'coherence': connectivity,
                })
        
        """
        Synchrony Analysis
        """

        # loop through electrodes and find coherence between lfp signal and freq bands
        for elec in range(num_elec):
     
            # get traces
            elec_trace = lfp_traces[elec, :]

            # loop through frequency bands and calculate coherence
            for band in SpectralBand.fetch(as_dict=True, order_by="lower_freq"):

                # get signal of specific frequency band
                freq_cutoff = np.array([band['lower_freq']-1, band['upper_freq']+1]) # includes 1 Hz buffer
                if freq_cutoff[0] < 1:
                    freq_cutoff[0] = 1
                sos = butter(order, freq_cutoff/nyquist, btype='bandpass', output='sos')
                filtered = sosfiltfilt(sos, elec_trace)

                # get magnitude of hilbert transform (doing instead of morlet wavelets)
                hilbert_signal = hilbert(filtered)
                freq_power_signal = np.abs(hilbert_signal) ** 2

                # find coherence between original signal and the power signal (for each frequency)
                f, Cxy = coherence(elec_trace, freq_power_signal, fs=fs, nperseg=nperseg)
                # remove frequencies greater than max_freq
                frequencies = f[f <= max_freq]
                synchrony = Cxy[f <= max_freq]

                # insert into part table
                self.Synchrony.insert1({
                    **key,
                    'band_name': band['band_name'],
                    'electrode': elec,
                    'f': frequencies,
                    'synchrony': synchrony,
                })
        
        # update execution duration
        self.update1(
            {
                **key,
                "execution_duration": (
                    datetime.now(timezone.utc) - execution_time
                ).total_seconds()
                / 60,
            }
        )

"""
Specparam (FOOOF)
"""

def interpolate_spectrum(frequency, spectrum, notch_freqs):
    # create mask for frequencies to remove
    mask = np.ones_like(frequency, dtype=bool)
    for notch_freq in notch_freqs:
        freq_mask = (notch_freq - 5 <= frequency) & (frequency <= notch_freq + 5)
        mask = mask & (~freq_mask)
    # interpolate
    interp_func = interp1d(frequency[mask], spectrum[mask], kind='linear', fill_value="extrapolate")
    interp_spectrum = interp_func(frequency)
    
    return interp_spectrum

@schema
class FOOOFParamset(dj.Lookup):
    """
    FOOOF parameter sets for spectral fitting.
    """

    definition = """ 
    fooof_param_idx: int  # Unique identifier for the FOOOF parameter set
    ---
    peak_width_limits: blob  # Lower and upper bounds on peak widths in Hz. e.g. [1, 12]
    max_n_peaks: int         # Maximum number of peaks the model can fit. e.g. 6
    min_peak_height: float   # Minimum absolute height of a peak above the aperiodic component. e.g. 0.1
    peak_threshold: float    # Relative threshold that candidate peaks must exceed to be included. e.g. 2.0
    aperiodic_mode: varchar(16) # Form of the aperiodic fit. e.g. 'fixed', 'knee'
    """

    contents = [
        (0, [1, 12], 6, 0.1, 2.0, 'fixed'),
        (1, [5, 12], 3, .05, 3.5, 'fixed'),
        (2, [5, 12], 3, .05, 3.5, 'knee')
    ]

@schema
class FBOSCParamset(dj.Lookup):
    """
    fBOSC parameter sets for spectral fitting.
    """

    definition = """ 
    fbosc_param_idx: int  # Unique identifier for the fBOSC parameter set
    ---
    dt: float  # Time resolution in seconds (for each epoch). e.g. 10
    detection_thresh: float  # Chi-squared threshold for peak detection. (between 0 and 1)
    """

    contents = [
        (0, 10, .99),
        (1, 10, .95),
        (2, 30, .99)
    ]

@schema
class FOOOFandFBOSCSession(dj.Manual):
    """
    Manual insert of combined FOOOF spectral fitting and fBOSC oscillation extraction.
    """

    definition = """ 
    -> ephys.LFP
    -> FOOOFParamset
    -> FBOSCParamset
    start_freq: float  # Start frequency for FOOOF fitting
    end_freq: float   # End frequency for FOOOF fitting
    ---
    analysis_electrodes: blob # List of electrodes to be averaged for analysis (if empty, will average across all electrodes)
    """

@schema
class FOOOFAnalysis(dj.Computed):
    """
    Runs FOOOF's spectral decomposition analysis, then quantifies oscillatory activity using fBOSC.
    """

    definition = """
    -> FOOOFandFBOSCSession
    spec_param_idx: int  # Reference to SpectrogramParamset
    ---
    plot: longblob  # Plot of FOOOF fit (as json)
    summary_params: longblob  # FOOOF parameters over entire session
    frequency: longblob  # Frequency values for spectrogram
    oscillatory_activity: longblob  # spectrogram power relative to aperiodic fit (over entire session)
    aperiodic_offset: longblob  # Aperiodic offset over time
    aperiodic_knee: longblob  # Aperiodic knee over time
    aperiodic_exponent: longblob  # Aperiodic exponent over time
    mean_absolute_error: longblob  # Mean absolute error of FOOOF fit over time
    r_squared: longblob  # R^2 of FOOOF fit over time
    """
    class FBOSCAnalysis(dj.Part):
        """
        fBOSC detected oscillatory activity time points for each frequency band.
        """

        definition = """
        -> master
        -> SpectralBand
        ---
        oscillation_times: longblob  # Time points where oscillations were detected in this band (s from session start)
        oscillation_heights: longblob  # Height of oscillations detected in this band (above aperiodic fit)
        """

    def make(self, key):

        # fetch electrodes to analyze
        analysis_electrodes = (FOOOFandFBOSCSession & key).fetch1("analysis_electrodes")

        # fetch time and frequency information
        time, frequency = np.array((LFPSpectrogram.ChannelSpectrogram & key).fetch("time", "frequency"))[:,0]

        # fetch lfp spectrograms (averaged across electrodes)
        if len(analysis_electrodes) > 0:
            spectrograms = (LFPSpectrogram.ChannelSpectrogram & key & f"electrode IN {tuple(analysis_electrodes)}").fetch("spectrogram")
        else:
            spectrograms = (LFPSpectrogram.ChannelSpectrogram & key).fetch("spectrogram")
        mean_spectrum = np.mean(np.stack(spectrograms, axis=-1), axis=2)  # shape: (frequency, time)

        # fetch fooof parameters
        peak_width_limits, max_n_peaks, min_peak_height, peak_threshold, aperiodic_mode = (FOOOFParamset & key).fetch1(
            "peak_width_limits", "max_n_peaks", "min_peak_height", "peak_threshold", "aperiodic_mode"
        )

        # fetch fooof session parameters
        start_freq, end_freq = (FOOOFandFBOSCSession & key).fetch1(
            "start_freq", "end_freq"
        )
        bounded_frequency = frequency[(start_freq <= frequency) & (frequency <= end_freq)]

        # get frequency band information (mask if frequency is within band)
        frequency_band_masks = {
            band['band_name']: (band['lower_freq'] <= bounded_frequency) & (bounded_frequency <= band['upper_freq'])
            for band in SpectralBand.fetch(as_dict=True, order_by='lower_freq')
            } 

        # initialize model
        fm = SpectralModel(
            peak_width_limits=peak_width_limits,
            max_n_peaks=max_n_peaks,
            min_peak_height=min_peak_height,
            peak_threshold=peak_threshold,
            aperiodic_mode=aperiodic_mode,
            verbose=False
        )

        # process summary fooof fit over all time bins
        notch_freqs = np.arange(60, frequency.max(), 60)
        interp_spectrum = interpolate_spectrum(frequency, np.mean(mean_spectrum, axis=1), notch_freqs)
        fm.fit(frequency, interp_spectrum, freq_range=(start_freq, end_freq))

        # generate plot
        fm.plot()
        mpl_fig = plt.gcf()
        plotly_fig = tls.mpl_to_plotly(mpl_fig)
        json_fig = pio.to_json(plotly_fig)

        # extract summary parameters
        summary_params = {name: fm.get_params(name) for name in ['aperiodic_params', 'peak_params', 'metrics']}

        # get aperiodic fit
        aperiodic_params = fm.get_params('aperiodic_params')
        if aperiodic_mode == 'fixed':
            offset, exponent = aperiodic_params
            aperiodic_fit = 10**(offset - exponent * np.log10(bounded_frequency))
        elif aperiodic_mode == 'knee':
            offset, knee, exponent = aperiodic_params
            aperiodic_fit = 10**(offset - np.log10(knee + bounded_frequency ** exponent))
        else:
            raise ValueError(f"Invalid aperiodic mode: {aperiodic_mode}")
        
        # find oscillatory activity relative to aperiodic fit
        interp_spectrum = interp_spectrum[np.isin(frequency, bounded_frequency)]  # restrict to bounded frequency
        oscillatory_activity = interp_spectrum - aperiodic_fit

        # fetch bosc parameters
        dt, detection_thresh = (FBOSCParamset & key).fetch1(
            "dt", "detection_thresh")

        # get chi-square factor for thresholding
        chi2_factor = chi2.ppf(detection_thresh, df=2) / 2

        # loop through time bins and perform fBOSC analysis
        time_bins = np.arange(0, time[-1], dt)
        epoch_data = {
            **{f"{band_name}_times": [] for band_name in frequency_band_masks.keys()},
            **{f"{band_name}_heights": [] for band_name in frequency_band_masks.keys()},
            "aperiodic_offset": [],
            "aperiodic_knee": [],
            "aperiodic_exponent": [],
            "mae": [],
            "r_squared": [],
            }
        for t_start in time_bins:

            # get spectrum within time bin
            epoch_spectrum = np.mean(mean_spectrum[:, (t_start <= time) & (time < t_start + dt)], axis=1)

            # interpolate mean_spectrum to account for 60 Hz line noise removal
            interp_epoch_spectrum = interpolate_spectrum(frequency, epoch_spectrum, notch_freqs)

            # fit model
            fm.fit(frequency, interp_epoch_spectrum, freq_range=(start_freq, end_freq))
            interp_epoch_spectrum = interp_epoch_spectrum[np.isin(frequency, bounded_frequency)]  # restrict to bounded frequency

            # extract aperiodic fit parameters
            aperiodic_params = fm.get_params('aperiodic_params')

            # get aperiodic fit
            if aperiodic_mode == 'fixed':
                offset, exponent = aperiodic_params
                aperiodic_fit = 10**(offset - exponent * np.log10(bounded_frequency))
            elif aperiodic_mode == 'knee':
                offset, knee, exponent = aperiodic_params
                aperiodic_fit = 10**(offset - np.log10(knee + bounded_frequency ** exponent))
            else:
                raise ValueError(f"Invalid aperiodic mode: {aperiodic_mode}")
            
            # extract aperiodic metrics
            epoch_data["aperiodic_offset"].append(offset)
            epoch_data["aperiodic_knee"].append(knee if aperiodic_mode == 'knee' else 0)
            epoch_data["aperiodic_exponent"].append(exponent)
            
            # get chi-square threshold for burst detection
            threshold_spectrum = aperiodic_fit * chi2_factor

            # extract if specific frequency bands have bursts (spectral power > threshold)
            for band_name, band_mask in frequency_band_masks.items():
                if np.any(interp_epoch_spectrum[band_mask] > threshold_spectrum[band_mask]):
                    epoch_data[f"{band_name}_times"].append(t_start + dt/2) # store center time of bin
                    epoch_data[f"{band_name}_heights"].append(np.max(interp_epoch_spectrum[band_mask] - aperiodic_fit[band_mask])) # store max height above aperiodic fit

            # extract fit metrics
            metrics = fm.get_params("metrics")
            epoch_data["mae"].append(metrics["error_mae"])
            epoch_data["r_squared"].append(metrics["gof_rsquared"])
        
        # convert lists to arrays
        for key_name in epoch_data.keys():
            epoch_data[key_name] = np.array(epoch_data[key_name])
        
        # insert into master table
        self.insert1(
            {
                **key,
                "spec_param_idx": (LFPSpectrogram & key).fetch("param_idx")[0],
                "plot": json_fig,
                "summary_params": summary_params,
                "frequency": bounded_frequency,
                "oscillatory_activity": oscillatory_activity,
                "aperiodic_offset": epoch_data["aperiodic_offset"],
                "aperiodic_knee": epoch_data["aperiodic_knee"],
                "aperiodic_exponent": epoch_data["aperiodic_exponent"],
                "mean_absolute_error": epoch_data["mae"],
                "r_squared": epoch_data["r_squared"],
            }
        )

        # insert into part table
        for band_name in frequency_band_masks.keys():
            self.FBOSCAnalysis.insert1(
                {
                    **key,
                    "spec_param_idx": (LFPSpectrogram & key).fetch("param_idx")[0],
                    "band_name": band_name,
                    "oscillation_times": epoch_data[f"{band_name}_times"],
                    "oscillation_heights": epoch_data[f"{band_name}_heights"],
                }
            )

"""
STTFA (power spectrum based)
"""
@schema
class STTFA(dj.Computed):
    """
    Spike-Triggered Time-Frequency Analysis (STTFA) for each electrodes. Shows the impact of spikes on LFP spectral power.
    """

    definition = """
    -> LFPSpectrogram.ChannelSpectrogram
    ---
    spike_count: int # number of spikes 
    a_sttfa: longblob  # average frequency power during spike-triggered time window 
    r_sttfa: longblob # randomized STTFA (random spike times)
    n_sttfa: longblob # normalized STTFA (log(STTFA) - log(rSTTFA))
    frequency: longblob  # frequency values
    """

    @property
    def key_source(self): # only process sessions with all MUA spikes processed

        min_spikes = 10

        lfp_table = dj.U("organoid_id", "start_time", "end_time").aggr(LFPSpectrogram)
        
        electrode_map = probe.ElectrodeConfig.Electrode.proj("channel_idx")

        valid_keys = []
        for lfp_key in lfp_table.fetch(as_dict=True):
            
            lfp_with_channel = ((LFPSpectrogram & lfp_key) * electrode_map).proj("channel_idx")

            mua_keys = (mua.MUASpikes 
                        & f"organoid_id = '{lfp_key['organoid_id']}'" 
                        & f"start_time >= '{lfp_key['start_time']}'" 
                        & f"start_time < '{lfp_key['end_time']}'").fetch("KEY")
            
            summed_spikes_table = lfp_with_channel.aggr(
                (mua.MUASpikes.Channel & mua_keys).proj("spike_count", mua_start="start_time"),
                "channel_idx",
                total_spike_count="sum(spike_count)"
            )

            electrodes, total_spikes = summed_spikes_table.fetch("electrode", "total_spike_count")

            min_spikes_bool = total_spikes >= min_spikes
            for electrode in electrodes[min_spikes_bool]:
                valid_keys.append({
                    **lfp_key,
                    "electrode": electrode
                })

        return (
            LFPSpectrogram.ChannelSpectrogram 
            & valid_keys
        )

    def make(self, key):

        # define parameters
        fs = 20000 # sampling frequency in Hz
        max_freq = 300 # Hz
        num_rand_iterations = 1000 # number of randomizations for rSTTFA

        # find the channel idx for the spectrogram electrode
        probe_type = get_probe_type(key)
        channel_idx = map_channel_to_electrode(probe_type, input_indices=np.array([key['electrode']]), electrode_to_channel=True)[0]

        # fetch MUA parameters within the spectrogram time window
        spike_indices, start_times = (mua.MUASpikes.Channel & 
                                                    f"organoid_id='{key['organoid_id']}'" &
                                                    f"start_time BETWEEN '{key['start_time']}' AND '{key['end_time']}'" &
                                                    f"channel_idx = '{channel_idx}'"
                                                    ).fetch('spike_indices', 'start_time')

        # get array of all spike times (relative to frame start)
        start_ms = (start_times - key['start_time']).astype('timedelta64[ms]') / np.timedelta64(1, 'ms') # ms from frame start
        rel_spike_times_ms = spike_indices / fs / (np.timedelta64(1,'ms')/np.timedelta64(1,'s')) 
        spike_times_ms = np.hstack(rel_spike_times_ms + start_ms).astype(int) # relative to spectrogram start time

        # remove boundary spikes (account for MUA outside spectrogram time)
        num_ms = (key['end_time'] - key['start_time']) / timedelta(milliseconds=1)
        spike_times_ms = spike_times_ms[(0 <= spike_times_ms) & (spike_times_ms <= num_ms)]

        spike_count = len(spike_times_ms)

        # fetch spectrogram
        freq, time, spectrogram = (LFPSpectrogram.ChannelSpectrogram & key).fetch1('frequency', 'time', 'spectrogram')

        # convert time to ms
        time_ms = (time * 1000).astype(int)  # in ms
        times_array = np.arange(0, time_ms[-1] + 1)  # array of all ms time points within spectrogram duration

        # calculate STTFA
        spike_spec_bins = np.histogram(spike_times_ms, bins=np.concatenate([[0], time_ms]))[0].astype(bool) # binary array indicating which spectrogram time bins have spikes
        a_sttfa = np.mean(spectrogram[:, spike_spec_bins], axis=1)

        a_sttfa = a_sttfa[freq <= max_freq]
        frequency = freq[freq <= max_freq]

        # calculate randomized STTFA
        r_sttfa_list = []
        for _ in range(num_rand_iterations):
            rand_spike_times = np.random.choice(times_array, size=spike_count, replace=False)
            rand_spike_indices_spec_bins = np.histogram(rand_spike_times, bins=np.concatenate([[0], time_ms]))[0].astype(bool)
            r_sttfa = np.mean(spectrogram[:, rand_spike_indices_spec_bins], axis=1)
            r_sttfa_list.append(r_sttfa[freq <= max_freq])

        r_sttfa = np.mean(np.vstack(r_sttfa_list), axis=0)

        # calculate normalized STTFA
        n_sttfa = np.log10(a_sttfa) - np.log10(r_sttfa)  # shape: (frequency)

        # insert into table
        self.insert1(
            {
                **key,
                'spike_count': spike_count,
                'a_sttfa': a_sttfa,
                'r_sttfa': r_sttfa,
                'n_sttfa': n_sttfa,
                'frequency': frequency,
            }
        )

"""
Phase Amplitude Coupling
"""

@schema
class TensorpacParamset(dj.Lookup):
    """
    Parameters for phase-amplitude coupling analysis with Tensorpac.
    """

    definition = """
    tensorpac_param_idx: int # Unique identifier for the Tensorpac parameter set
    ---
    idpac: blob # tuple containing (PAC method, surrogate method, normalization method)
    dcomplex: varchar(16) # method for calculating complex phase ('wavelet' or 'hilbert')
    cycles: blob # number of cycles for wavelet convolution (phase, amplitude) (if dcomplex='wavelet')
    width: float # width of morlet wavelet (if dcomplex='wavelet')
    dt: float # time step in seconds for calculating PAC over time (length of epoch)
    """
    contents = [
        (0, (1, 3, 4), 'wavelet', np.nan, 7, 10)
    ]

@schema
class PhaseAmplitudeBands(dj.Lookup):
    """
    Manual insert of phase and amplitude frequency bands for coupling analysis.
    """

    definition = """ 
    band_param_idx: int # Unique identifier for the frequency band parameter set
    ---
    f_pha: longblob # phase frequencies of interest (see CREATE_new_coupling_session for details)
    f_amp: longblob # amplitude frequencies of interest (see CREATE_new_coupling_session for details)
    """
    contents = [
        (0, 
         [[2, 4], [4, 6], [6, 8], [8, 10], [10, 12]],
         [[20, 25], [25, 30], [30, 35], [35, 40], [40, 45], [45, 50]]),
        (1,
         [[4, 6]],
         [[20, 30], [30, 40], [40, 50]])

    ]

@schema
class CouplingSession(dj.Manual):
    """
    Manual insert of Tensorpac coupling analysis (across entire session)
    """

    definition = """ 
    -> ephys.LFP.Trace
    -> TensorpacParamset
    -> PhaseAmplitudeBands
    """

@schema
class PhaseAmplitudeCoupling(dj.Computed):
    """
    Phase-amplitude coupling analysis using Tensorpac (tensorpac.Pac).
    """

    definition = """
    -> CouplingSession
    ---
    pha_vec: longblob # phase frequency bin (center frequencies)
    amp_vec: longblob # amplitude frequency bin (center frequencies)
    pac_array: longblob # PAC values for each phase-amplitude pair (shape: amp_vec, pha_vec, num_epochs)
    pvalues: longblob # p-values for each phase-amplitude pair (shape: amp_vec, pha_vec)
    """

    class PreferredPhase(dj.Part):
        """
        Phase in which amplitude is strongest for each phase-amplitude pair.
        """

        definition = """
        -> PhaseAmplitudeCoupling
        ---
        preferred_phase: longblob # preferred phase for each amplitude frequency (shape: amp_vec, pha_vec, num_epochs)
        vecbin: longblob # phase bins (-pi to pi) (shape: n_bins)
        amplitude_values: longblob # amplitude values for each phase bin (shape: n_bins, amp_vec, pha_vec, num_epochs)
        """

    def make(self, key):

        # fetch Tensorpac parameters
        idpac, dcomplex, cycles, width, dt = (TensorpacParamset & key).fetch1(
            "idpac", "dcomplex", "cycles", "width", "dt"
        )
        dcomplex = sys.intern(str(dcomplex))

        # fetch frequency bands
        f_pha, f_amp = (PhaseAmplitudeBands & key).fetch1("f_pha", "f_amp")

        # fetch data
        trace = (ephys.LFP.Trace & key).fetch1("lfp")
        fs = (ephys.LFP & key).fetch1("lfp_sampling_rate")

        # break data into epochs (data = num_epochs x epoch_len)
        epoch_len = int(fs * dt)  # number of samples in each epoch
        num_epochs = int(len(trace) // epoch_len)
        data = trace[:num_epochs * epoch_len].reshape((num_epochs, epoch_len)) # cut off excess samples if dt not perfectly divisible

        # initialize PAC object
        # define PAC object
        if dcomplex == 'wavelet':
            p = Pac(idpac=idpac, f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, width=width, verbose=False)
        elif dcomplex == 'hilbert':
            p = Pac(idpac=idpac, f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, cycles=cycles, verbose=False)
        else:
            raise ValueError(f"Invalid dcomplex method: {dcomplex}")

        # filter traces
        pha = p.filter(fs, data, ftype='phase', n_jobs=-1) # (num_phase, num_epochs, epoch_len)
        amp = p.filter(fs, data, ftype='amplitude', n_jobs=-1) # (num_amp, num_epochs, epoch_len)

        # fit pac to phase and amplitude
        pac = p.fit(pha, amp, n_perm=200, p=1, mcp='bonferroni', verbose=False) # (num_amp, num_phase, num_epochs)

        # extract pac metrics
        pha_vec = p.xvec  # phase frequency bin (center frequencies)
        amp_vec = p.yvec  # amplitude frequency bin (center frequencies)
        pvalues = p.pvalues  # average p-values across epochs (shape: num_amp, num_phase) (done with null distribution from permutations)

        # initialize preferred phase object
        if dcomplex == 'wavelet':
            pp = PreferredPhase(f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, width=width, verbose=False)
        elif dcomplex == 'hilbert':
            pp = PreferredPhase(f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, cycles=cycles, verbose=False)
        else:
            raise ValueError(f"Invalid dcomplex method: {dcomplex}")

        # fit preferred phase
        ampbin, preferred_phase, vecbin = pp.fit(pha, amp, n_bins=72)

        # insert into table
        self.insert1(
            {
                **key,
                'pha_vec': pha_vec,
                'amp_vec': amp_vec,
                'pac_array': pac,
                'pvalues': pvalues,
            }
        )
        self.PreferredPhase.insert1(
            {
                **key,
                'preferred_phase': preferred_phase,
                'vecbin': vecbin,
                'amplitude_values': ampbin,
            }
        )

@schema
class UnitCouplingSession(dj.Manual):
    """
    Manual insert for Tensorpac Event-based Phase-Amplitude Coupling analysis (coupling during specific single unit spikes).
    """
    
    definition = """ 
    -> ephys.CuratedClustering.Unit
    -> TensorpacParamset
    -> PhaseAmplitudeBands
    """

@schema
class EventBasedCoupling(dj.Computed):
    """
    Event-based phase-amplitude coupling analysis using Tensorpac (tensorpac.Pac). Shows coupling during specific single unit spikes.
    """
    
    definition = """
    -> UnitCouplingSession
    ---
    pha_vec: longblob # phase frequency bin (center frequencies)
    amp_vec: longblob # amplitude frequency bin (center frequencies)
    t: longblob # time vector relative to spike time 
    erpac_array: longblob # Event-Related PAC values for each phase-amplitude pair (shape: amp_vec, pha_vec, time)
    """

    class InterTrialCoherence(dj.Part):
        """
        Inter-trial coherence (ITC) of phase for each phase frequency during specific single unit spikes.
        """

        definition = """
        -> EventBasedCoupling
        ---
        itc_array: longblob # ITC values for each phase frequency and time point (shape: pha_vec, time)
        """

    class PeakLockedTF(dj.Part):
        """
        Peak-locked time-frequency analysis for each phase-amplitude pair during specific single unit spikes.
        """

        definition = """
        -> EventBasedCoupling
        ---
        pltf_array: longblob # Peak-locked time-frequency amplitude for each phase-amplitude pair (shape: amp_vec, pha_vec, time)
        """

    def make(self, key):

        spike_buffer = .5 # seconds extract around spike times (+/-)
        edge = 10 # samples to trim from edges of extracted LFP epochs (to avoid edge artifacts in filtering) (only relavent for ITC)

        # make sure an ephys.LFP session exists for the same time window (will use LFP trace for coupling analysis)
        if not (ephys.LFP & key):
            raise ValueError(f"No corresponding LFP session found for {key} - cannot perform event-based coupling analysis")

        # fetch Tensorpac parameters
        idpac, dcomplex, cycles, width, dt = (TensorpacParamset & key).fetch1(
            "idpac", "dcomplex", "cycles", "width", "dt"
        )
        dcomplex = sys.intern(str(dcomplex))

        # fetch frequency bands
        f_pha, f_amp = (PhaseAmplitudeBands & key).fetch1("f_pha", "f_amp")

        # fetch single unit spike info
        electrode, spike_times, spike_sites = (ephys.CuratedClustering.Unit & key).fetch1("electrode", "spike_times", "spike_sites")
        spike_times = spike_times[spike_sites == electrode] # only use spikes from the electrode corresponding to the LFP trace (will be used for coupling analysis)

        # fetch LFP trace and sampling rate
        trace = (ephys.LFP.Trace & key & f"electrode = '{electrode}'").fetch1("lfp")
        lfp_fs = (ephys.LFP & key).fetch1("lfp_sampling_rate")

        # get time vector (for lfp trace)
        time_vector = np.arange(len(trace)) / lfp_fs

        # remove boundary spikes
        spike_times = spike_times[(spike_times > spike_buffer) & (spike_times < time_vector[-1] - spike_buffer)] # remove boundary spikes

        # insert empty arrays if no spikes remain after removing boundary spikes
        if len(spike_times) == 0:
            self.insert1(
                {
                    **key,
                    'pha_vec': np.array([]),
                    'amp_vec': np.array([]),
                    't': np.array([]),
                    'erpac_array': np.array([]),
                }
            )

            self.InterTrialCoherence.insert1(
                {
                    **key,
                    'itc_array': np.array([]),
                }
            )

            self.PeakLockedTF.insert1(
                {
                    **key,
                    'pltf_array': np.array([]),
                }
            )
            return

        # loop through spikes and extract lfp segments
        lfp_epochs_itc = []
        n_samples = int(spike_buffer * lfp_fs) + edge # number of samples to extract on either side of spike time (accounting for edge trimming)
        for spike_time in spike_times:

            # find nearest index in lfp trace to spike time
            spike_idx = np.argmin(np.abs(time_vector - spike_time))

            # get lfp segment around spike time (accounting for spike_buffer)
            start_idx = spike_idx - n_samples
            end_idx = spike_idx + n_samples
            lfp_segment = trace[start_idx:end_idx]

            lfp_epochs_itc.append(lfp_segment)
        lfp_epochs_itc = np.array(lfp_epochs_itc)

        # remove edge samples from epochs (for non itc analysis)
        lfp_epochs = lfp_epochs_itc[:, edge:-edge]

        # initialize preferred phase object
        if dcomplex == 'wavelet':
            p = EventRelatedPac(f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, width=width, verbose=False)
        elif dcomplex == 'hilbert':
            p = EventRelatedPac(f_pha=f_pha, f_amp=f_amp, dcomplex=dcomplex, cycles=cycles, verbose=False)
        else:
            raise ValueError(f"Invalid dcomplex method: {dcomplex}")
        
        # extract phases and amplitudes
        pha = p.filter(lfp_fs, lfp_epochs, ftype='phase')
        amp = p.filter(lfp_fs, lfp_epochs, ftype='amplitude')

        # compute the erpac
        erpac_array = p.fit(pha, amp, method='gc', smooth=50)

        # get pvalues
        pha_vec = p.xvec  # phase frequency bin (center frequencies)
        amp_vec = p.yvec  # amplitude frequency bin (center frequencies)
        t = np.arange(-spike_buffer, spike_buffer, 1/lfp_fs) # time vector relative to spike time

        # ITC analysis
        if dcomplex == 'wavelet':
            itc = ITC(lfp_epochs_itc, sf=lfp_fs, f_pha=f_pha, dcomplex=dcomplex, width=width, edges=edge, verbose=False)
        elif dcomplex == 'hilbert':
            itc = ITC(lfp_epochs_itc, sf=lfp_fs, f_pha=f_pha, dcomplex=dcomplex, cycle=cycles, edges=edge, verbose=False)
        else:
            raise ValueError(f"Invalid dcomplex method: {dcomplex}")

        itc_array = itc.itc

        # PeakLockedTF analysis
        cue = 0
        pltf_array = []
        for phase_band in f_pha:
            pltf = PeakLockedTF(lfp_epochs, lfp_fs, cue, times=t, f_pha=phase_band, f_amp=f_amp, verbose=False)
            pltf_array.append(pltf.amp_a)
        pltf_array = np.stack(pltf_array, axis=1) # shape = amp_vec, pha_vec, num_spikes, time
        
        # average across spikes
        pltf_array = np.mean(pltf_array, axis=2) # shape = amp_vec, pha_vec, time

        # insert into table
        self.insert1(
            {
                **key,
                'pha_vec': pha_vec,
                'amp_vec': amp_vec,
                't': t,
                'erpac_array': erpac_array,
            }
        )

        self.InterTrialCoherence.insert1(
            {
                **key,
                'itc_array': itc_array,
            }
        )

        self.PeakLockedTF.insert1(
            {
                **key,
                'pltf_array': pltf_array,
            }
        )

"""
Longitudinal Spectral Analysis
"""

@schema
class LongitudinalSpectralAnalysis(dj.Computed):
    """
    Mean frequency band power across single file (per electrode). Designed for longitudinal analysis of spectral power changes across development.
    """

    definition = """
    -> culture.Experiment
    -> ephys.EphysRawFile
    ---
    execution_duration: float # time of analysis execution (seconds)
    channel_ids: longblob # channel ids for each electrode in the recording (not mapped)
    """

    class BandPower(dj.Part):

        definition = """
        -> master
        -> SpectralBand
        ---
        band_power: longblob # mean power for each channel in the specified frequency band (shape: num_channels)
        """

    def make(self, key):
        execution_time = datetime.now(timezone.utc)

        POWERLINE_NOISE_FREQ = 60  # Default powerline noise frequency in Hz
        TARGET_SAMPLING_RATE = 2500 # Target sampling rate for LFP analysis in Hz

        file, acq_software = (ephys.EphysRawFile & key).fetch1("file_path", "acq_software")
        si_extractor = recording_extractor_full_dict[acq_software.replace(" ", "").lower()]

        # Read data. Concatenate if multiple files are found.
        file_path = find_full_path(ephys.get_ephys_root_data_dir(), file)

        # Get stream name for this file
        streams = si_extractor.get_streams(file_path)[0]
        amplifier_streams = [s for s in streams if "amplifier" in s]
        if not amplifier_streams:
            raise ValueError(f"No amplifier stream found in file: {file_path}")
        stream_name = amplifier_streams[0]

        # Get recording object
        si_recording = si_extractor(file_path, stream_name=stream_name)
        fs = si_recording.get_sampling_frequency()

        # Calculate downsampling factor
        true_ratio = fs / TARGET_SAMPLING_RATE
        downsample_factor = int(np.round(true_ratio))

        # Get LFP indices (row index of the LFP matrix to be used)
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

        # Get LFP channels
        channel_ids = si_recording.get_channel_ids()

        port_indices = np.array(
            [
                ind
                for ind, ch in enumerate(channel_ids)
                if ch.startswith(port_id)
            ]
        )
        channel_ids = channel_ids[port_indices]

        # Get Traces
        raw_lfps = si_recording.get_traces(channel_ids=channel_ids)

        # Design notch filter
        notch_b, notch_a = signal.iirnotch(
            w0=POWERLINE_NOISE_FREQ, Q=30, fs=fs
        )

        # Apply notch filter
        lfps = signal.filtfilt(notch_b, notch_a, raw_lfps, axis=0)

        # Downsample the signal with `decimate`
        lfps = signal.decimate(lfps, downsample_factor, ftype="fir", zero_phase=True, axis=0)

        # Simple PSD via Welch
        dt = 3 * TARGET_SAMPLING_RATE  # 3-second windows with 50% overlap
        freqs, psd = welch(lfps, fs=TARGET_SAMPLING_RATE, nperseg=dt, noverlap=dt//2, axis=0)  # PSD in power/Hz

        # insert into master
        self.insert1(
            {
                **key,
                "execution_duration": 0, # placeholder for now - will add timing code later
                "channel_ids": channel_ids,
            }
        )

        # calculate mean power in each frequency band
        for band in SpectralBand.fetch(as_dict=True, order_by='lower_freq'):

            # average power across frequencies within band
            band_mask = (band['lower_freq'] <= freqs) & (freqs <= band['upper_freq'])
            mean_power = np.mean(psd[band_mask, :], axis=0)

            # insert into part
            self.BandPower.insert1(
                {
                    **key,
                    "band_name": band['band_name'],
                    "band_power": mean_power,
                }
            )

        # update execution time
        self.update1(
            {
                **key,
                "execution_duration": (datetime.now(timezone.utc) - execution_time).total_seconds(),
                "channel_ids": channel_ids,
            }
        )
