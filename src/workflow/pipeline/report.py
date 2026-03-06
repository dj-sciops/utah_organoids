import tempfile
from datetime import datetime, timezone
from pathlib import Path

import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np

from workflow import DB_PREFIX
from workflow.pipeline import analysis, ephys, ephys_sorter
from workflow.pipeline.patch_clamp_ephys import schema_ephys as patch_clamp

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
                filename_spectrogram = f"organoid_{key['organoid_id']}_ch{electrode}_{key['start_time']}_{key['end_time']}_spectrogram.png"
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


@schema
class PatchClampReport(dj.Computed):
    """
    Convert patch-clamp plot file paths to dashboard-compatible attachments.

    This table reads PNG files from existing patch_clamp plot tables and stores
    them as binary attachments for use with the dashboard PlotGrid component.
    """

    definition = """
    -> patch_clamp.APandIntrinsicProperties
    """

    class FICurve(dj.Part):
        """F-I curve plot attachment."""
        definition = """
        -> master
        ---
        fi_plot: attach
        """

    class FirstSpike(dj.Part):
        """First spike waveform plot attachment."""
        definition = """
        -> master
        ---
        spike_plot: attach
        """

    class PhasePlane(dj.Part):
        """Phase plane (dV/dt vs V) plot attachment."""
        definition = """
        -> master
        ---
        phase_plot: attach
        """

    class CurrentStep(dj.Part):
        """Current step traces plot attachment."""
        definition = """
        -> master
        ---
        istep_plot: attach
        """

    class VICurve(dj.Part):
        """V-I curve (input resistance) plot attachment."""
        definition = """
        -> master
        ---
        vi_plot: attach
        """

    class FirstSpikeDerivative(dj.Part):
        """First spike dV/dt plot attachment."""
        definition = """
        -> master
        ---
        spike_dvdt_plot: attach
        """

    class FirstSpikeSecondDerivative(dj.Part):
        """First spike d²V/dt² plot attachment."""
        definition = """
        -> master
        ---
        spike_2nd_deriv_plot: attach
        """

    class FirstSpikeTrough(dj.Part):
        """First spike with trough marker annotations."""
        definition = """
        -> master
        ---
        spike_trough_plot: attach
        """

    class CombinedPlot(dj.Part):
        """Combined multi-panel plot (istep + FI + spike + phase)."""
        definition = """
        -> master
        ---
        combined_plot: attach
        """

    class AnimatedTrace(dj.Part):
        """Animated current step trace (GIF)."""
        definition = """
        -> master
        ---
        animated_trace: attach
        """

    def make(self, key):
        """
        Read plot file paths from patch_clamp tables and store as attachments.
        """
        # Get the directory from experiment metadata
        ephys_exp = (patch_clamp.EphysExperimentsForAnalysis & key).fetch1()
        directory = Path(ephys_exp.get('directory', '')).expanduser()

        # Insert master record
        self.insert1(key)

        # F-I Curve
        fi_query = patch_clamp.FICurvePlots & key
        if fi_query:
            fi_path = fi_query.fetch1('fi_png_path')
            if fi_path:
                full_path = directory / fi_path
                if full_path.exists():
                    self.FICurve.insert1({**key, 'fi_plot': str(full_path)})
                else:
                    logger.warning(f"F-I plot not found: {full_path}")

        # First Spike
        spike_query = patch_clamp.FirstSpikePlots & key
        if spike_query:
            spike_path = spike_query.fetch1('spike_png_path')
            if spike_path:
                full_path = directory / spike_path
                if full_path.exists():
                    self.FirstSpike.insert1({**key, 'spike_plot': str(full_path)})
                else:
                    logger.warning(f"First spike plot not found: {full_path}")

        # Phase Plane
        phase_query = patch_clamp.PhasePlanes & key
        if phase_query:
            phase_path = phase_query.fetch1('phase_png_path')
            if phase_path:
                full_path = directory / phase_path
                if full_path.exists():
                    self.PhasePlane.insert1({**key, 'phase_plot': str(full_path)})
                else:
                    logger.warning(f"Phase plane plot not found: {full_path}")

        # Current Step Traces
        istep_query = patch_clamp.CurrentStepPlots & key
        if istep_query:
            istep_path = istep_query.fetch1('istep_png_large_path')
            if istep_path:
                full_path = directory / istep_path
                if full_path.exists():
                    self.CurrentStep.insert1({**key, 'istep_plot': str(full_path)})
                else:
                    logger.warning(f"Current step plot not found: {full_path}")

        # V-I Curve
        vi_query = patch_clamp.VICurvePlots & key
        if vi_query:
            vi_path = vi_query.fetch1('vi_png_path')
            if vi_path:
                full_path = directory / vi_path
                if full_path.exists():
                    self.VICurve.insert1({**key, 'vi_plot': str(full_path)})
                else:
                    logger.warning(f"V-I plot not found: {full_path}")

        # First Spike Derivative (dV/dt)
        dvdt_query = patch_clamp.FirstSpikeFirstDerivativePlots & key
        if dvdt_query:
            dvdt_path = dvdt_query.fetch1('spike_dvdt_png_path')
            if dvdt_path:
                full_path = directory / dvdt_path
                if full_path.exists():
                    self.FirstSpikeDerivative.insert1({**key, 'spike_dvdt_plot': str(full_path)})
                else:
                    logger.warning(f"First spike dV/dt plot not found: {full_path}")

        # First Spike Second Derivative (d²V/dt²)
        d2vdt2_query = patch_clamp.FirstSpikeSecondDerivativePlots & key
        if d2vdt2_query:
            d2vdt2_path = d2vdt2_query.fetch1('spike_2nd_derivative_png_path')
            if d2vdt2_path:
                full_path = directory / d2vdt2_path
                if full_path.exists():
                    self.FirstSpikeSecondDerivative.insert1({**key, 'spike_2nd_deriv_plot': str(full_path)})
                else:
                    logger.warning(f"First spike d²V/dt² plot not found: {full_path}")

        # First Spike Trough Markers
        trough_query = patch_clamp.FirstSpikePlotsMarkersTrough & key
        if trough_query:
            trough_path = trough_query.fetch1('spike_other_markers_png_path')
            if trough_path:
                full_path = directory / trough_path
                if full_path.exists():
                    self.FirstSpikeTrough.insert1({**key, 'spike_trough_plot': str(full_path)})
                else:
                    logger.warning(f"First spike trough plot not found: {full_path}")

        # Combined Plot
        combined_query = patch_clamp.CombinedPlotsWithText & key
        if combined_query:
            combined_path = combined_query.fetch1('large_fi_vi_spike_phase')
            if combined_path:
                full_path = directory / combined_path
                if full_path.exists():
                    self.CombinedPlot.insert1({**key, 'combined_plot': str(full_path)})
                else:
                    logger.warning(f"Combined plot not found: {full_path}")

        # Animated Trace (GIF)
        anim_query = patch_clamp.AnimatedCurrentStepPlots & key
        if anim_query:
            anim_path = anim_query.fetch1('istep_gif_path')
            if anim_path:
                full_path = directory / anim_path
                if full_path.exists():
                    self.AnimatedTrace.insert1({**key, 'animated_trace': str(full_path)})
                else:
                    logger.warning(f"Animated trace not found: {full_path}")
