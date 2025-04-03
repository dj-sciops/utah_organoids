import datajoint as dj
import numpy as np
from scipy import signal
from datetime import timedelta, datetime, timezone
import tempfile
import matplotlib.pyplot as plt
from pathlib import Path

from workflow import DB_PREFIX

from .ephys import ephys

schema = dj.schema(DB_PREFIX + "analysis")


@schema
class SpectralBand(dj.Lookup):
    definition = """
    band_name: varchar(16)
    ---
    lower_freq: float # (Hz)
    upper_freq: float # (Hz)
    """
    contents = [
        ("delta", 2.0, 4.0),
        ("theta", 4.0, 7.0),
        ("alpha", 8.0, 12.0),
        ("beta", 13.0, 30.0),
        ("gamma", 30.0, 50.0),
        ("highgamma1", 70.0, 110.0),
        ("highgamma2", 130.0, 500.0),
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
    contents = [(0, 0.5, 0.0, "Default 0.5s time segments without overlap.")]


@schema
class LFPSpectrogram(dj.Computed):
    """Calculate spectrogram at each channel.

    Assumes the LFP is:
        1. Low-pass filtered at 1000 Hz.
        2. Notch filtered at 50/60 Hz.
        3. Resampled to 2500 Hz.
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


@schema
class SpectrogramPlot(dj.Computed):
    """
    Generate spectrogram plots for each channel per electrode.
    """

    definition = """
    -> LFPSpectrogram
    ---
    freq_min: float  # min frequency
    freq_max: float  # max frequency
    execution_duration: float  # execution duration in hours
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> LFPSpectrogram.ChannelSpectrogram
        ---
        spectrogram_plot: attach
        """

    def make(self, key):
        execution_time = datetime.now(timezone.utc)

        # Find which frequencies are within 0.1–500 Hz
        FREQ_MIN, FREQ_MAX = 0.1, 500

        self.insert1(
            {**key, "freq_min": FREQ_MIN, "freq_max": FREQ_MAX, "execution_duration": 0}
        )

        tmp_dir = tempfile.TemporaryDirectory()

        spectrograms = (LFPSpectrogram.ChannelSpectrogram & key).fetch(as_dict=True)
        bands = SpectralBand.fetch()

        for ch_data in spectrograms:
            Sxx, t, f = ch_data["spectrogram"], ch_data["time"], ch_data["frequency"]
            freq_mask = (f >= FREQ_MIN) & (f <= FREQ_MAX)

            # Create spectrogram plot
            fig_spectrogram, ax = plt.subplots(figsize=(12, 8))
            im = ax.pcolormesh(
                t, f[freq_mask], np.log(Sxx[freq_mask, :]), shading="auto"
            )
            fig_spectrogram.colorbar(im, ax=ax, label="log Power")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Frequency (Hz)")
            ax.set_title(
                f"Spectrogram \n Organoid {key['organoid_id']} | {key['start_time']} - {key['end_time']} \n Ch {ch_data['electrode']}"
            )

            # Add frequency band lines
            for band in bands:
                ax.axhspan(
                    band["lower_freq"],
                    band["upper_freq"],
                    alpha=0.15,
                    color="royalblue",
                )
                ax.text(
                    -0.05,
                    (band["lower_freq"] + band["upper_freq"]) / 2,
                    band["band_name"],
                    va="center",
                    ha="right",
                    transform=ax.get_yaxis_transform(),
                    color="navy",
                    fontsize=9,
                )

            filename_spectrogram = f"organoid_{key['organoid_id']}_electrode_{ch_data['electrode']}_spectrogram.png"
            filepath_spectrogram = Path(tmp_dir.name) / filename_spectrogram
            fig_spectrogram.savefig(filepath_spectrogram)
            plt.close(fig_spectrogram)

            self.Channel.insert1(
                {
                    **key,
                    "electrode": ch_data["electrode"],
                    "spectrogram_plot": filepath_spectrogram,
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
