import tempfile
from datetime import datetime, timezone
from pathlib import Path

import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np

from workflow import DB_PREFIX
from workflow.pipeline import analysis, ephys, ephys_sorter

logger = dj.logger
schema = dj.schema(DB_PREFIX + "report")


@schema
class SpikeInterfaceReport(dj.Computed):
    definition = """
    -> ephys_sorter.SIExport
    """

    class Plot(dj.Part):
        definition = """
        -> master
        name: varchar(64)
        ---
        plot: attach
        """

    def make(self, key):
        png_query = ephys_sorter.SIExport.File & key & "file_name LIKE '%png'"

        self.insert1(key)

        for f in png_query.fetch("file"):
            f = Path(f)
            self.Plot.insert1({**key, "name": f.stem, "plot": f.as_posix()})


@schema
class SpectrogramAndPowerPlots(dj.Computed):
    """
    Generate spectrogram and power plots per channel.
    """

    definition = """
    -> analysis.LFPSpectrogram
    ---
    freq_min: float  # min frequency displayed
    freq_max: float  # max frequency displayed
    execution_duration: float  # execution duration in hours
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> analysis.LFPSpectrogram.ChannelSpectrogram
        ---
        spectrogram_plot: attach  # Spectrogram image
        band_power_plot: attach   # Normalized band power plot image
        """

    def make(self, key):
        execution_start = datetime.now(timezone.utc)

        # Frequency display range
        freq_min = analysis.SpectralBand.fetch("lower_freq").min()
        freq_max = analysis.SpectralBand.fetch("upper_freq").max()

        # Insert main entry
        self.insert1(
            {**key, "freq_min": freq_min, "freq_max": freq_max, "execution_duration": 0}
        )

        # Create temporary directory for plots
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Fetch all spectrograms for this recording
            spectrograms = (analysis.LFPSpectrogram.ChannelSpectrogram & key).fetch(
                as_dict=True
            )
            bands = analysis.SpectralBand.fetch(as_dict=True)

            # Color scheme for frequency bands
            lfp_colors = [
                "#ad2bea",
                "#4d3ff8",
                "#39cabb",
                "#53e53a",
                "#e3e12c",
                "#f7a740",
                "#ed3838",
            ]

            # Process each electrode separately
            for ch_data in spectrograms:
                electrode = ch_data["electrode"]
                Sxx, t, f = (
                    ch_data["spectrogram"],
                    ch_data["time"],
                    ch_data["frequency"],
                )
                freq_mask = (f >= freq_min) & (f <= freq_max)

                # Spectrogram plot
                spectrogram_fig, ax = plt.subplots(figsize=(12, 8))
                im = ax.pcolormesh(
                    t, f[freq_mask], np.log10(Sxx[freq_mask, :]), shading="auto"
                )
                spectrogram_fig.colorbar(im, ax=ax, label="log Power (μV²/Hz)")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Frequency (Hz)")
                ax.set_title(
                    f"Spectrogram\nOrganoid {key['organoid_id']} | {key['start_time']} - {key['end_time']}\nCh {electrode}"
                )

                # Highlight frequency bands
                for i, band in enumerate(bands):
                    color = lfp_colors[i % len(lfp_colors)]
                    ax.axhspan(
                        band["lower_freq"], band["upper_freq"], alpha=0.15, color=color
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

                # Save spectrogram plot
                filename_spectrogram = (
                    f"organoid_{key['organoid_id']}_ch{electrode}_{key['start_time']}_{key['end_time']}_spectrogram.png"
                )
                filepath_spectrogram = tmp_path / filename_spectrogram
                spectrogram_fig.savefig(
                    filepath_spectrogram, bbox_inches="tight", dpi=100
                )
                plt.close(spectrogram_fig)

                # Band Power Plot
                power_fig, ax = plt.subplots(figsize=(12, 8))

                for i, band in enumerate(bands):
                    # Fetch power time series for this band and channel
                    power_data = (
                        analysis.LFPSpectrogram.ChannelPower
                        & {
                            **key,
                            "band_name": band["band_name"],
                            "electrode": electrode,
                        }
                    ).fetch1("power_time_series")

                    # Robust normalization
                    if len(power_data) == 0 or np.nanmax(power_data) == 0:
                        normalized_power = np.zeros_like(t)
                    else:
                        normalized_power = power_data / np.nanmax(power_data)

                    ax.plot(
                        t,
                        normalized_power,
                        "-",
                        color=lfp_colors[i % len(lfp_colors)],
                        label=band["band_name"],
                    )

                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Normalized Band Power (unitless)")
                ax.set_yscale("log")
                ax.set_title(
                    f"Band Power Plot\nOrganoid {key['organoid_id']} | {key['start_time']} - {key['end_time']}\nCh {electrode}"
                )
                ax.legend(loc="upper left")
                ax.grid(True)

                # save power plot
                filename_band_power = (
                    f"organoid_{key['organoid_id']}_ch{electrode}_"
                    f"{key['start_time']}_{key['end_time']}_band_power.png"
                )
                filepath_band_power = tmp_path / filename_band_power
                power_fig.savefig(filepath_band_power, bbox_inches="tight", dpi=100)
                plt.close(power_fig)
                self.Channel.insert1(
                    {
                        **key,
                        "electrode": electrode,
                        "spectrogram_plot": filepath_spectrogram,
                        "band_power_plot": filepath_band_power,
                    }
                )

        # Update execution duration
        self.update1(
            {
                **key,
                "execution_duration": (
                    datetime.now(timezone.utc) - execution_start
                ).total_seconds()
                / 3600,
            }
        )
