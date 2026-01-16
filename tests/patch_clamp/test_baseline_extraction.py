"""
Baseline Test Script for Patch-Clamp Feature Extraction

This script generates ground truth baseline results from real ABF recordings.
These baselines are used to validate that the pyabf + ipfx migration produces
consistent results compared to the original implementation.

Process:
    1. Loads ABF files from the test data directory (9 recordings from 2020-08-28)
    2. Uses legacy code (legacy_loader.py) with pyabf + vendored AllenSDK 0.14.2
    3. Extracts electrophysiology features using FeatureExtractionParams (params_id=1)
    4. Generates output files for each recording
    5. Saves summary to baseline_summary.json

Purpose:
    These baseline results serve as ground truth to validate that the new
    pyabf + ipfx implementation produces consistent results (<1% tolerance
    on 13 key features across 9 recordings).

Usage:
    python tests/patch_clamp/test_baseline_extraction.py

Input:
    ABF files from: /Users/milagros/data/utah_organoids/patch_clamp/2020-08-28/
    - 9 ABF recordings with current-clamp protocols

Outputs:
    tests/patch_clamp/baseline_results/
    ├── baseline_summary.json          # Summary with all results and parameters
    ├── {recording}_raw_data.json      # Metadata (sweep counts, voltage/current stats)
    ├── {recording}_features.json      # Extracted AP and intrinsic features
    ├── {recording}_fi_curve.png       # F-I curve plot
    ├── {recording}_first_spike.png    # First spike waveform
    ├── {recording}_phase_plane.png    # dV/dt vs V plot
    └── {recording}_traces.png         # Current clamp traces

Key Features Extracted:
    - has_ap: Whether action potentials were detected
    - input_resistance: Cell input resistance (MOhm)
    - sag: Voltage sag ratio
    - ap_threshold: Action potential threshold (mV)
    - ap_width: Action potential width (ms)
    - ap_peak: Action potential peak voltage (mV)
    - rheobase_stim_amp: Minimum current to elicit AP (pA)
    - max_firing_rate: Maximum firing rate (Hz)

Note:
    This script should only be run once to generate baselines. The resulting
    JSON files are committed to the repository. PNG files are gitignored.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime

# Import from our legacy loader module
from legacy_loader import load_current_step, extract_istep_features

# Test data configuration
TEST_DATA_DIR = Path("/Users/milagros/data/utah_organoids/patch_clamp/2020-08-28")
OUTPUT_DIR = Path(__file__).parent / "baseline_results"

# Current step time parameters - discovered from ABF file structure:
# Protocol has step at 0.55s-1.55s (1 second window)
ISTEP_START = 0.55  # seconds
ISTEP_END = 1.55    # 1 second window for analysis

# Feature extraction parameters (from FeatureExtractionParams, params_id=1)
FEATURE_PARAMS = {
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


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return {"__ndarray__": True, "data": obj.tolist(), "shape": list(obj.shape)}
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            if np.isnan(obj):
                return None
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def save_raw_data_metadata(data: dict, output_path: Path):
    """Save raw data metadata (not full arrays - too large)."""
    metadata = {
        "file_id": data.get("file_id"),
        "file_directory": data.get("file_directory"),
        "record_date": str(data.get("record_date")),
        "record_time": str(data.get("record_time")),
        "dt": data.get("dt"),
        "hz": data.get("hz"),
        "n_channels": data.get("n_channels"),
        "channel_names": data.get("channel_names"),
        "channel_units": data.get("channel_units"),
        "n_sweeps": data.get("n_sweeps"),
        "sweep_length": data.get("sweep_length"),
        # Store summary stats instead of full arrays
        "voltage_stats": {
            "n_sweeps": len(data.get("voltage", [])),
            "sweep_lengths": [len(v) for v in data.get("voltage", [])],
            "min_per_sweep": [float(np.min(v)) for v in data.get("voltage", [])],
            "max_per_sweep": [float(np.max(v)) for v in data.get("voltage", [])],
        },
        "current_stats": {
            "n_sweeps": len(data.get("current", [])),
            "min_per_sweep": [float(np.min(c)) for c in data.get("current", [])],
            "max_per_sweep": [float(np.max(c)) for c in data.get("current", [])],
        },
    }

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, cls=NumpyEncoder)

    return metadata


def save_features(summary_features: dict, output_path: Path):
    """Save extracted features to JSON."""
    with open(output_path, "w") as f:
        json.dump(summary_features, f, indent=2, cls=NumpyEncoder)


def plot_fi_curve(summary_features: dict, output_path: Path):
    """Generate F-I curve plot."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    stim_amp = summary_features.get("all_stim_amp")
    firing_rate = summary_features.get("all_firing_rate")

    if stim_amp is None or firing_rate is None:
        print(f"  Skipping F-I curve - no data")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(stim_amp, firing_rate, 'o-', color='steelblue', markersize=6)
    ax.set_xlabel("Current (pA)")
    ax.set_ylabel("Spikes per second")
    ax.set_title("F-I Curve")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_first_spike(data: dict, summary_features: dict, output_path: Path):
    """Generate first spike waveform plot."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    if not summary_features.get("has_ap"):
        print(f"  Skipping first spike - no AP detected")
        return

    # Get the rheobase sweep index
    rheobase_idx = summary_features.get("rheobase_index")
    if rheobase_idx is None:
        return

    # Get spike times
    spikes_peak_t = summary_features.get("spikes_peak_t")
    spikes_sweep_id = summary_features.get("spikes_sweep_id")

    if spikes_peak_t is None or len(spikes_peak_t) == 0:
        return

    # Find first spike in rheobase sweep
    rheobase_spike_mask = np.array(spikes_sweep_id) == rheobase_idx
    if not np.any(rheobase_spike_mask):
        return

    first_spike_t = np.array(spikes_peak_t)[rheobase_spike_mask][0]

    # Extract window around spike
    t = data["t"]
    v = data["voltage"][rheobase_idx]

    window_start = first_spike_t - 0.010  # 10ms before
    window_end = first_spike_t + 0.040    # 40ms after

    mask = (t >= window_start) & (t <= window_end)
    t_window = (t[mask] - first_spike_t) * 1000  # Convert to ms relative to spike
    v_window = v[mask]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(t_window, v_window, color='darkred', linewidth=1.5)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (mV)")
    ax.set_title("First Spike")
    ax.axhline(y=summary_features.get("ap_threshold", 0), color='gray', linestyle='--', alpha=0.5, label='Threshold')
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_phase_plane(data: dict, summary_features: dict, output_path: Path):
    """Generate phase plane (dV/dt vs V) plot."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.ndimage import gaussian_filter1d

    if not summary_features.get("has_ap"):
        print(f"  Skipping phase plane - no AP detected")
        return

    rheobase_idx = summary_features.get("rheobase_index")
    if rheobase_idx is None:
        return

    t = data["t"]
    v = np.array(data["voltage"][rheobase_idx])
    dt = data["dt"]

    # Smooth and compute derivative
    v_filt = gaussian_filter1d(v, sigma=5)
    dvdt = np.gradient(v_filt, dt) / 1000  # Convert to V/s

    # Find spike region
    spikes_peak_t = summary_features.get("spikes_peak_t")
    spikes_sweep_id = summary_features.get("spikes_sweep_id")

    rheobase_spike_mask = np.array(spikes_sweep_id) == rheobase_idx
    if not np.any(rheobase_spike_mask):
        return

    first_spike_t = np.array(spikes_peak_t)[rheobase_spike_mask][0]

    # Window around spike
    window_start = first_spike_t - 0.005
    window_end = first_spike_t + 0.015
    mask = (t >= window_start) & (t <= window_end)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(v_filt[mask], dvdt[mask], color='darkgreen', linewidth=1.5)
    ax.set_xlabel("Voltage (mV)")
    ax.set_ylabel("dV/dt (V/s)")
    ax.set_title("Phase Plane")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_traces(data: dict, summary_features: dict, output_path: Path):
    """Generate current clamp traces plot."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    t = data["t"]
    voltages = data["voltage"]
    currents = data["current"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                    gridspec_kw={'height_ratios': [3, 1]})

    # Plot voltage traces
    hero_idx = summary_features.get("hero_sweep_index")

    for i, v in enumerate(voltages):
        alpha = 0.3
        color = 'gray'
        lw = 0.5

        if hero_idx is not None and i == hero_idx:
            alpha = 1.0
            color = 'steelblue'
            lw = 1.5

        ax1.plot(t, v, color=color, alpha=alpha, linewidth=lw)

    ax1.set_ylabel("Membrane Voltage (mV)")
    ax1.set_title("Current Clamp Traces")
    ax1.axvline(x=ISTEP_START, color='red', linestyle='--', alpha=0.3)
    ax1.axvline(x=ISTEP_END, color='red', linestyle='--', alpha=0.3)

    # Plot current traces
    for i, c in enumerate(currents):
        alpha = 0.3
        color = 'gray'
        if hero_idx is not None and i == hero_idx:
            alpha = 1.0
            color = 'steelblue'
        ax2.plot(t, c, color=color, alpha=alpha, linewidth=0.5)

    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Current (pA)")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def process_single_file(abf_file: Path, output_dir: Path) -> dict:
    """Process a single ABF file and save all outputs."""
    recording_name = abf_file.stem
    print(f"\nProcessing: {recording_name}")

    results = {
        "recording": recording_name,
        "file": str(abf_file),
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Load raw data
        print(f"  Loading ABF file...")
        data = load_current_step(str(abf_file))

        # Save raw data metadata
        raw_data_path = output_dir / f"{recording_name}_raw_data.json"
        save_raw_data_metadata(data, raw_data_path)
        print(f"  Saved raw data metadata: {raw_data_path.name}")

        # Step 2: Extract features
        print(f"  Extracting features...")
        cell_features, summary_features = extract_istep_features(
            data, start=ISTEP_START, end=ISTEP_END, **FEATURE_PARAMS
        )

        # Save features
        features_path = output_dir / f"{recording_name}_features.json"
        save_features(summary_features, features_path)
        print(f"  Saved features: {features_path.name}")

        # Record key features in results
        results["features"] = {
            "has_ap": summary_features.get("has_ap"),
            "input_resistance": summary_features.get("input_resistance"),
            "sag": summary_features.get("sag"),
            "ap_threshold": summary_features.get("ap_threshold"),
            "ap_width": summary_features.get("ap_width"),
            "ap_peak": summary_features.get("ap_peak"),
            "rheobase_stim_amp": summary_features.get("rheobase_stim_amp"),
            "max_firing_rate": summary_features.get("max_firing_rate"),
        }

        # Step 3: Generate plots
        print(f"  Generating plots...")

        plot_fi_curve(summary_features, output_dir / f"{recording_name}_fi_curve.png")
        plot_first_spike(data, summary_features, output_dir / f"{recording_name}_first_spike.png")
        plot_phase_plane(data, summary_features, output_dir / f"{recording_name}_phase_plane.png")
        plot_traces(data, summary_features, output_dir / f"{recording_name}_traces.png")

        results["success"] = True
        print(f"  Done")

    except Exception as e:
        results["error"] = str(e)
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()

    return results


def main():
    """Run baseline extraction on all test ABF files."""
    print("=" * 60)
    print("BASELINE TEST: Patch-Clamp Feature Extraction")
    print("=" * 60)
    print(f"\nTest data directory: {TEST_DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Analysis window: {ISTEP_START}s to {ISTEP_END}s")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find all ABF files
    abf_files = sorted(TEST_DATA_DIR.glob("*.abf"))
    print(f"\nFound {len(abf_files)} ABF files")

    if not abf_files:
        print("ERROR: No ABF files found!")
        return

    # Process each file
    all_results = []
    for abf_file in abf_files:
        result = process_single_file(abf_file, OUTPUT_DIR)
        all_results.append(result)

    # Save summary
    summary_path = OUTPUT_DIR / "baseline_summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "test_data_dir": str(TEST_DATA_DIR),
        "n_files": len(abf_files),
        "n_success": sum(1 for r in all_results if r["success"]),
        "n_failed": sum(1 for r in all_results if not r["success"]),
        "parameters": {
            "istep_start": ISTEP_START,
            "istep_end": ISTEP_END,
            "feature_params": FEATURE_PARAMS,
        },
        "results": all_results,
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, cls=NumpyEncoder)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files: {len(abf_files)}")
    print(f"Successful: {summary['n_success']}")
    print(f"Failed: {summary['n_failed']}")
    print(f"\nResults saved to: {OUTPUT_DIR}")

    # Print feature summary for successful extractions
    print("\nKey Features Extracted:")
    print("-" * 60)
    for result in all_results:
        if result["success"] and result.get("features"):
            f = result["features"]
            print(f"\n{result['recording']}:")
            print(f"  Has AP: {f.get('has_ap')}")
            if f.get('input_resistance'):
                print(f"  Input Resistance: {f.get('input_resistance'):.1f} MOhm")
            if f.get('ap_threshold'):
                print(f"  AP Threshold: {f.get('ap_threshold'):.1f} mV")
            if f.get('rheobase_stim_amp'):
                print(f"  Rheobase: {f.get('rheobase_stim_amp'):.1f} pA")


if __name__ == "__main__":
    main()
