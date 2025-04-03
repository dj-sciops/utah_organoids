import datajoint as dj
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timezone
import numpy as np

from workflow import DB_PREFIX
from workflow.pipeline import ephys, ephys_sorter, analysis


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
    freq_min: float  # min frequency 
    freq_max: float  # max frequency
    execution_duration: float  # execution duration in hours
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> analysis.LFPSpectrogram.ChannelSpectrogram
        ---
        spectrogram_plot: attach  # Spectrogram visualization
        band_power_plot: attach   # Power in frequency bands over time
        """

    def make(self, key):
        execution_time = datetime.now(timezone.utc)

        FREQ_MIN, FREQ_MAX = 0.1, 200  # Match MATLAB highgamma2 upper limit

        self.insert1(
            {**key, "freq_min": FREQ_MIN, "freq_max": FREQ_MAX, "execution_duration": 0}
        )

        tmp_dir = tempfile.TemporaryDirectory()

        # Fetch all channel spectrograms for this recording
        spectrograms = (analysis.LFPSpectrogram.ChannelSpectrogram & key).fetch(
            as_dict=True
        )
        bands = analysis.SpectralBand.fetch()

        # MATLAB color scheme for frequency bands
        lfp_colors = [
            "#ad2bea",
            "#4d3ff8",
            "#39cabb",
            "#53e53a",
            "#e3e12c",
            "#f7a740",
            "#ed3838",
        ]

        # Process each electrode/channel separately
        for ch_data in spectrograms:
            electrode = ch_data["electrode"]
            Sxx, t, f = ch_data["spectrogram"], ch_data["time"], ch_data["frequency"]
            freq_mask = (f >= FREQ_MIN) & (f <= FREQ_MAX)

            # Create spectrogram plot similar to BU_Plots.m for this electrode
            fig_spectrogram, ax = plt.subplots(figsize=(12, 8))

            # Use log10 scale for power as in BU_Plots.m
            im = ax.pcolormesh(
                t, f[freq_mask], np.log10(Sxx[freq_mask, :]), shading="auto"
            )
            # t, f[freq_mask], np.log(Sxx[freq_mask, :]), shading="auto"
            fig_spectrogram.colorbar(im, ax=ax, label="log Power")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Frequency (Hz)")
            ax.set_title(
                f"Spectrogram \n Organoid {key['organoid_id']} | {key['start_time']} - {key['end_time']} \n Ch {electrode}"
            )

            # Add frequency band visualization
            for i, band in enumerate(bands):
                color = lfp_colors[i % len(lfp_colors)]
                ax.axhspan(
                    band["lower_freq"],
                    band["upper_freq"],
                    alpha=0.15,
                    color=color,
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

            filename_spectrogram = (
                f"organoid_{key['organoid_id']}_electrode_{electrode}_spectrogram.png"
            )
            filepath_spectrogram = Path(tmp_dir.name) / filename_spectrogram
            fig_spectrogram.savefig(filepath_spectrogram)
            plt.close(fig_spectrogram)

            # Create band power plot similar to BU_Plots.m for this electrode
            fig_band_power, ax = plt.subplots(figsize=(12, 8))

            # Plot each frequency band power for this electrode
            for i, band in enumerate(bands):
                band_data = (
                    analysis.LFPSpectrogram.ChannelPower
                    & {**key, "band_name": band["band_name"], "electrode": electrode}
                ).fetch1("power")

                # Normalize power (as in BU_Plots.m)
                normalized_power = (
                    band_data / np.nanmax(band_data)
                    if np.nanmax(band_data) > 0
                    else band_data
                )

                ax.plot(
                    t,
                    normalized_power,
                    "-",
                    color=lfp_colors[i % len(lfp_colors)],
                    label=f"{band['band_name']}",
                )

            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Normalized Power")
            ax.set_yscale("log")  # Log scale for power as in BU_Plots.m
            ax.set_title(
                f"Band Power Plot \n Organoid {key['organoid_id']} | {key['start_time']} - {key['end_time']} \n Ch {electrode}"
            )
            ax.legend(loc="upper left")
            ax.grid(True)

            filename_band_power = (
                f"organoid_{key['organoid_id']}_"
                f"start_{key['start_time']}_"
                f"end_{key['end_time']}_"
                f"channel_{electrode}_"
                f"band_power.png"
            )
            filepath_band_power = Path(tmp_dir.name) / filename_band_power

            # Save with optimized parameters
            fig_band_power.tight_layout()
            fig_band_power.savefig(
                filepath_band_power, bbox_inches="tight", dpi=100, format="png"
            )
            plt.close(fig_band_power)

            # Insert this electrode's plots into the Channel table
            self.Channel.insert1(
                {
                    **key,
                    "spectrogram_plot": filepath_spectrogram,
                    "band_power_plot": filepath_band_power,
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
