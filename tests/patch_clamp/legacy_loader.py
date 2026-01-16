"""
Legacy loader for patch-clamp baseline testing.

This module provides functions to load ABF files and extract features using the
legacy code path (pyabf + vendored AllenSDK 0.14.2). It is used by
test_baseline_extraction.py to generate ground truth baselines.

Functions:
    load_current_step: Load ABF file and return voltage/current arrays
    extract_istep_features: Extract AP and intrinsic features from current-step data

Note:
    This module handles the complex import setup required for the vendored
    AllenSDK which uses relative imports. The setup_legacy_imports() function
    must be called before using extract_istep_features().
"""

import sys
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
PATCH_CLAMP_PATH = REPO_ROOT / "src" / "workflow" / "pipeline" / "patch_clamp_ephys"
ALLENSDK_PATH = PATCH_CLAMP_PATH / "allensdk_0_14_2"


def setup_legacy_imports():
    """Set up Python path for legacy imports."""
    # Add paths in correct order
    paths_to_add = [
        str(PATCH_CLAMP_PATH),
        str(ALLENSDK_PATH),
    ]
    for p in reversed(paths_to_add):
        if p not in sys.path:
            sys.path.insert(0, p)


def load_current_step(abf_file: str, min_voltage: float = -140) -> dict:
    """
    Load ABF file using pyabf (modern replacement for stfio).

    This creates a data structure compatible with the legacy code format.

    Args:
        abf_file: Path to ABF file
        min_voltage: Minimum voltage threshold (sweeps below this are excluded)

    Returns:
        Dictionary with voltage, current, time arrays and metadata
    """
    import pyabf
    import numpy as np
    from collections import OrderedDict

    abf = pyabf.ABF(abf_file)

    data = OrderedDict()
    data['file_id'] = Path(abf_file).stem
    data['file_directory'] = str(Path(abf_file).parent)
    data['record_date'] = abf.abfDateTime.date() if abf.abfDateTime else None
    data['record_time'] = abf.abfDateTime.time() if abf.abfDateTime else None

    data['dt'] = 1.0 / abf.sampleRate  # seconds per sample
    data['hz'] = abf.sampleRate
    data['time_unit'] = 's'

    data['n_channels'] = abf.channelCount
    data['channel_names'] = abf.adcNames
    data['channel_units'] = abf.adcUnits
    data['n_sweeps'] = abf.sweepCount
    data['sweep_length'] = abf.sweepPointCount

    data['t'] = np.arange(0, abf.sweepPointCount) * data['dt']

    # Load all sweeps
    # For current clamp recordings:
    # - Voltage is the recorded signal (ADC)
    # - Current is the COMMAND signal (DAC), not the measured current
    voltage_list = []
    current_list = []

    # Find voltage channel (mV units) and current command channel (pA units)
    voltage_ch = None
    current_cmd_ch = None
    for ch in range(abf.channelCount):
        abf.setSweep(0, channel=ch)
        if 'mV' in abf.sweepUnitsY or abf.sweepUnitsY == 'mV':
            voltage_ch = ch
        # The command waveform is on the channel that controls current (pA)
        # Check DAC units for this channel

    # For current clamp, the command is typically on the DAC channel with pA units
    # DAC names/units tell us which channel has the current command
    for dac_idx, unit in enumerate(abf.dacUnits):
        if 'pA' in unit or unit == 'pA':
            current_cmd_ch = dac_idx
            break

    if voltage_ch is None:
        voltage_ch = 0  # Fallback
    if current_cmd_ch is None:
        current_cmd_ch = 0  # Fallback

    for sweep_idx in range(abf.sweepCount):
        # Get voltage data from the voltage channel
        abf.setSweep(sweep_idx, channel=voltage_ch)
        voltage_data = abf.sweepY.copy()

        # Get current command from the current command channel
        # sweepC gives the command waveform for the current channel setting
        abf.setSweep(sweep_idx, channel=current_cmd_ch)
        current_data = abf.sweepC.copy()  # Command/stimulus current from DAC

        voltage_list.append(voltage_data)
        current_list.append(current_data)

    # Filter out sweeps with voltage below min_voltage
    if min_voltage is not None:
        filtered_voltage = []
        filtered_current = []
        for v, c in zip(voltage_list, current_list):
            if np.min(v) >= min_voltage:
                filtered_voltage.append(v)
                filtered_current.append(c)
        voltage_list = filtered_voltage
        current_list = filtered_current
        data['n_sweeps'] = len(voltage_list)

    data['voltage'] = voltage_list
    data['current'] = current_list

    return data


def extract_istep_features(data: dict, start: float, end: float, **params) -> tuple:
    """
    Extract features using legacy AllenSDK 0.14.2.

    This function handles the complex import setup required for the
    vendored AllenSDK code with relative imports.

    Args:
        data: Dictionary from load_current_step
        start: Analysis window start time (seconds)
        end: Analysis window end time (seconds)
        **params: Feature extraction parameters

    Returns:
        Tuple of (cell_features, summary_features)
    """
    setup_legacy_imports()

    import numpy as np
    from collections import OrderedDict

    # Import the allensdk modules - need to handle relative imports
    # by reading and executing the code directly

    # First, load ephys_features (no relative imports)
    ephys_features_code = (ALLENSDK_PATH / "ephys_features.py").read_text()
    ephys_features_globals = {
        "__name__": "ephys_features",
        "__file__": str(ALLENSDK_PATH / "ephys_features.py"),
    }
    exec(compile(ephys_features_code, str(ALLENSDK_PATH / "ephys_features.py"), "exec"), ephys_features_globals)
    ft = type(sys)("ephys_features")
    ft.__dict__.update(ephys_features_globals)
    sys.modules["ephys_features"] = ft

    # Load ephys_extractor (imports ephys_features)
    ephys_extractor_code = (ALLENSDK_PATH / "ephys_extractor.py").read_text()
    # Replace relative import with absolute
    ephys_extractor_code = ephys_extractor_code.replace(
        "from . import ephys_features as ft",
        "import ephys_features as ft"
    )
    ephys_extractor_globals = {
        "__name__": "ephys_extractor",
        "__file__": str(ALLENSDK_PATH / "ephys_extractor.py"),
        "ft": ft,
    }
    exec(compile(ephys_extractor_code, str(ALLENSDK_PATH / "ephys_extractor.py"), "exec"), ephys_extractor_globals)
    efex = type(sys)("ephys_extractor")
    efex.__dict__.update(ephys_extractor_globals)
    sys.modules["ephys_extractor"] = efex

    # Now load current_clamp_features
    ccf_code = (PATCH_CLAMP_PATH / "current_clamp_features.py").read_text()
    # Replace relative imports with absolute
    ccf_code = ccf_code.replace(
        "from .allensdk_0_14_2 import ephys_extractor as efex",
        "import ephys_extractor as efex"
    )
    ccf_code = ccf_code.replace(
        "from .allensdk_0_14_2 import ephys_features as ft",
        "import ephys_features as ft"
    )

    ccf_globals = {
        "__name__": "current_clamp_features",
        "__file__": str(PATCH_CLAMP_PATH / "current_clamp_features.py"),
        "np": np,
        "OrderedDict": OrderedDict,
        "efex": efex,
        "ft": ft,
    }
    exec(compile(ccf_code, str(PATCH_CLAMP_PATH / "current_clamp_features.py"), "exec"), ccf_globals)

    # Call the extraction function
    return ccf_globals["extract_istep_features"](data, start, end, **params)


# Test if run directly
if __name__ == "__main__":
    import json

    print("Testing legacy loader...")

    # Test ABF loading - use file 0018 which has action potentials
    test_file = "/Users/milagros/data/utah_organoids/patch_clamp/2020-08-28/2020_08_28_0018.abf"
    print(f"\nLoading: {test_file}")

    data = load_current_step(test_file)
    print(f"  Sweeps: {data['n_sweeps']}")
    print(f"  Sample rate: {data['hz']} Hz")
    print(f"  Sweep length: {data['sweep_length']} samples")

    # Test feature extraction
    print("\nExtracting features...")
    params = {
        "filter": 10.0,
        "dv_cutoff": 4.0,
        "max_interval": 0.02,
        "min_height": 10.0,
        "min_peak": -20.0,
        "thresh_frac": 0.05,
        "baseline_interval": 0.1,
        "baseline_detect_thresh": 0.3,
        "subthresh_min_amp": -80.0,
        "n_subthres_sweeps": 4,
        "sag_target": -100.0,
        "sag_range_right": -89.0,
        "sag_range_left": -120.0,
        "adapt_avg_n_sweeps": 3,
        "adapt_first_n_ratios": 2,
        "spike_detection_delay": 0.001,
        "suprathreshold_target_delta_v": 15.0,
        "suprathreshold_target_delta_i": 15.0,
        "latency_target_delta_i": 5.0,
    }

    cell_features, summary_features = extract_istep_features(
        data, start=0.55, end=1.55, **params
    )

    print(f"\nResults:")
    print(f"  Has AP: {summary_features.get('has_ap')}")
    print(f"  Input Resistance: {summary_features.get('input_resistance')}")
    print(f"  AP Threshold: {summary_features.get('ap_threshold')}")
    print(f"  Rheobase: {summary_features.get('rheobase_stim_amp')}")

    print("\n✓ Legacy loader works!")
