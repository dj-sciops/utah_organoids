import datajoint as dj
from .ephys import ephys, event
from workflow import db_prefix
from scipy import signal

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
class TimeWindow(dj.Lookup):
    definition = """
    time_window_idx: int
    ---
    window_start_time: float  # Time in milliseconds
    window_end_time: float    # Time in milliseconds
    description: varchar(32)
    """
    contents = [(0, 0, 1000, "Default 1s.")]


@schema
class Spectrogram(dj.Computed):
    definition = """
    -> ephys.LFP
    -> TimeWindow
    -> SpectralBand
    -> event.AlignmentEvent
    ---
    power: float
    """

    def make(self, key):
        sampling_rate, window_start_time, window_end_time, lower_freq, upper_freq = (
            ephys.LFP
            * ephys.EphysRecording
            * TimeWindow
            * SpectralBand
            * ephys.EphysRecording
            & key
        ).fetch(
            "sampling_rate",
            "window_start_time",
            "window_end_time",
            "lower_freq",
            "upper_freq",
        )

        f, t, Sxx = signal.spectrogram(
            A, fs=sampling_rate, nperseg=nperseg, window="boxcar"
        )

        power = Sxx
