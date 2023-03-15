import datajoint as dj
from .ephys import ephys
from workflow import db_prefix
from scipy import signal
import numpy as np

schema = dj.schema(db_prefix + "analysis")


@schema
class SpectralBand(dj.Lookup):
    definition = """
    band_name: varchar(16)
    ---
    lower_freq: float # (Hz)
    upper_freq: float # (Hz)
    """
    contents = [
        ("delta", 0.5, 4.0),
        ("theta", 4.0, 7.0),
        ("alpha", 8.0, 12.0),
        ("beta", 18.0, 22.0),
        ("gamma", 30.0, 70.0),
        ("highgamma", 80.0, 500.0),
    ]


@schema
class SpectrogramParameters(dj.Lookup):
    definition = """
    param_idx: int
    ---
    window_size:     float    # Time in seconds
    overlap_size=0:  float    # Time in seconds
    description="":  varchar(64)
    """
    contents = [(0, 2.0, 0.0, "Default 2s time segments without overlap.")]


@schema
class LFPSpectrogram(dj.Computed):
        """Calculate spectrogram at each channel.
        
        Assumes the LFP is:
            1. Resampled to 2500 Hz.
            2. Notch filtered at 50/60 Hz.
            3. Low-pass filtered at 1000 Hz.
        """
    definition = """
    -> ephys.LFP.Trace
    -> SpectrogramParameters
    """

    class ChannelSpectrogram(dj.Part):
        definition = """
        -> master
        ---
        spectrogram: longblob # Power with dimensions (frequecy, time).
        time: longblob        # Timestamps
        frequency: longblob   # Fourier frequencies
        """

    class ChannelPower(dj.Part):
        definition = """
        -> master
        -> SpectralBand
        ---
        power: longblob   # Mean power in spectral band as a function of time
        mean_power: float # Mean power in a spectral band for a time window.
        std_power: float  # Standard deviation of the power in a spectral band for a time window.
        """

    def make(self, key):
        self.insert1(key)

        window_size, overlap_size = (SpectrogramParameters & key).fetch1(
            "window_size", "overlap_size"
        )

        lfp_sampling_rate = (ephys.LFP & key).fetch1("lfp_sampling_rate")

        lfp = (ephys.LFP.Trace & key).fetch1("lfp")
        frequency, time, Sxx = signal.spectrogram(
            lfp,
            fs=int(lfp_sampling_rate),
            nperseg=int(window_size * lfp_sampling_rate),
            noverlap=int(overlap_size * lfp_sampling_rate),
            window="boxcar",
        )

        self.ChannelSpectrogram.insert1(
            {**key, "spectrogram": Sxx, "frequency": frequency, "time": time}
        )
        band_keys, lower_frequencies, upper_frequencies = SpectralBand.fetch(
            "KEY", "lower_freq", "upper_freq"
        )
        for power_key, fl, fh in zip(band_keys, lower_frequencies, upper_frequencies):
            freq_mask = np.logical_and(frequency >= fl, frequency < fh)
            power = Sxx[freq_mask, :].mean(axis=0)  # mean across freq domain
            self.ChannelPower.insert1(
                dict(
                    **power_key,
                    **key,
                    power=power,
                    mean_power=power.mean(),
                    std_power=power.std(),
                )
            )
