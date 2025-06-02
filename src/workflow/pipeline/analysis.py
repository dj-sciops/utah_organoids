import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from workflow import DB_PREFIX

from .ephys import ephys

schema = dj.schema(DB_PREFIX + "analysis")

logger = dj.logger


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
        import scipy.stats as stats

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
        (0, 2.0, 1.0, "2s window, 50% overlap (delta, theta, alpha)"),
        (1, 0.5, 0.25, "0.5s window, 50% overlap (beta, gamma)"),
        (2, 0.25, 0.125, "0.25s window, 50% overlap (high-gamma)"),
    ]


@schema
class LFPSpectrogram(dj.Computed):
    """Spectrograms and frequency-domain power metrics for each LFP trace."""

    definition = """
    -> ephys.LFP.Trace
    -> SpectrogramParameters
    ---
    delta_band_mean_power: float  # Average delta power (1-4 Hz) over entire recording (μV²/Hz)
    power_range_90pct: float      # 90% range (95th-5th percentile) of broadband RMS amplitude envelope (μV RMS)
    """

    class ChannelSpectrogram(dj.Part):
        definition = """
        -> master
        ---
        spectrogram: longblob  # Spectrogram matrix (freq x time) (μV²/Hz)
        time: longblob         # Time bins (s)
        frequency: longblob    # Frequency bins (Hz)
        """

    class ChannelPower(dj.Part):
        """Power in each frequency band, per LFP trace."""

        definition = """
        -> master
        -> SpectralBand
        ---
        power_time_series: longblob  # Power time series for this band (μV²/Hz)
        mean_power: float            # Mean band power (μV²/Hz)
        std_power: float             # Std dev of band power (μV²/Hz)
        """

    def key_source(self):
        # Use only the default param_idx for high-gamma windowing params for automated population
        return ephys.LFP.Trace * SpectrogramParameters & "param_idx=2"

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

        # Compute spectrogram
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
        # 90% amplitude envelope range (μV RMS)
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
