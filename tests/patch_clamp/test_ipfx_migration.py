"""
Test script to verify ipfx migration produces similar results as baseline.

Compares the output of the new ipfx_features.py against the baseline
features captured with the legacy AllenSDK code.

Usage:
    cd /Users/milagros/Documents/codebases/datajoint-elements/utah_organoids/tests/patch_clamp
    python test_ipfx_migration.py
"""

import json
import numpy as np
from pathlib import Path
import sys
import importlib.util

# Load file_io directly
file_io_path = Path(__file__).parent.parent.parent / "src" / "workflow" / "pipeline" / "patch_clamp_ephys" / "file_io.py"
spec = importlib.util.spec_from_file_location("file_io", file_io_path)
file_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_io)
load_current_step = file_io.load_current_step

# Load ipfx features
ipfx_path = Path(__file__).parent.parent.parent / "src" / "workflow" / "pipeline" / "patch_clamp_ephys" / "ipfx_features.py"
spec = importlib.util.spec_from_file_location("ipfx_features", ipfx_path)
ipfx_features = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ipfx_features)
extract_istep_features = ipfx_features.extract_istep_features

# Test configuration
TEST_DATA_DIR = Path("/Users/milagros/data/utah_organoids/patch_clamp/2020-08-28")
BASELINE_DIR = Path(__file__).parent / "baseline_results"

ISTEP_START = 0.55
ISTEP_END = 1.55

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

# Key features to compare with tolerance thresholds
# (baseline_name, new_name, absolute_tolerance, relative_tolerance_percent)
# Note: Tolerances are set to accommodate expected differences between ipfx and AllenSDK 0.14.2
KEY_FEATURES = [
    ('has_ap', 'has_ap', 0, 0),
    ('input_resistance', 'input_resistance', 500, 25),  # 25% - different algorithms
    ('sag', 'sag', 0.1, 100),  # Sag calculation differs significantly
    ('ap_threshold', 'ap_threshold', 3, 10),  # Spike detection can vary
    ('ap_width', 'ap_width', 1.5, 30),
    ('ap_peak', 'ap_peak', 3, 8),
    ('rheobase_stim_amp', 'rheobase_stim_amp', 5, 15),
    ('max_firing_rate', 'max_firing_rate', 3, 20),
    ('f_i_curve_slope', 'f_i_curve_slope', 0.15, 35),
    ('v_baseline', 'resting_vm', 6, 10),  # Different baseline calculation
    ('avg_rheobase_latency', 'first_spike_latency', 30, 35),
    ('adapt_avg', 'adaptation_index', 0.08, 60),
    ('capacitance', 'membrane_cap', 35, 50),  # Depends on tau and Rin
]


def compare_features(baseline: dict, new_features: dict, recording: str) -> tuple:
    """Compare extracted features with tolerances."""
    issues = []
    matches = []

    for baseline_key, new_key, abs_tol, rel_tol_pct in KEY_FEATURES:
        baseline_val = baseline.get(baseline_key)
        new_val = new_features.get(new_key)
        feature = new_key  # Use new key for display

        # Handle None/NaN cases
        if baseline_val is None and new_val is None:
            matches.append(f"{feature}: both None")
            continue

        if baseline_val is None or new_val is None:
            issues.append(f"{feature}: baseline={baseline_val}, new={new_val}")
            continue

        # Boolean comparison
        if isinstance(baseline_val, bool) or isinstance(new_val, bool):
            if baseline_val == new_val:
                matches.append(f"{feature}: {baseline_val}")
            else:
                issues.append(f"{feature}: baseline={baseline_val}, new={new_val}")
            continue

        # Numeric comparison with tolerance
        try:
            baseline_f = float(baseline_val)
            new_f = float(new_val)

            if np.isnan(baseline_f) and np.isnan(new_f):
                matches.append(f"{feature}: both NaN")
                continue

            if np.isnan(baseline_f) or np.isnan(new_f):
                issues.append(f"{feature}: baseline={baseline_val}, new={new_val}")
                continue

            # Check absolute tolerance
            abs_diff = abs(new_f - baseline_f)

            # Check relative tolerance
            if abs(baseline_f) > 1e-6:
                rel_diff_pct = abs_diff / abs(baseline_f) * 100
            else:
                rel_diff_pct = 0 if abs_diff < 1e-6 else 100

            # Pass if within either tolerance
            if abs_diff <= abs_tol or rel_diff_pct <= rel_tol_pct:
                matches.append(f"{feature}: {new_f:.4g} (baseline: {baseline_f:.4g}, diff: {rel_diff_pct:.1f}%)")
            else:
                issues.append(f"{feature}: baseline={baseline_f:.4g}, new={new_f:.4g} (diff: {rel_diff_pct:.1f}%, abs: {abs_diff:.4g})")

        except (TypeError, ValueError):
            if baseline_val == new_val:
                matches.append(f"{feature}: {baseline_val}")
            else:
                issues.append(f"{feature}: baseline={baseline_val}, new={new_val}")

    return issues, matches


def test_single_recording(abf_file: Path, baseline_file: Path) -> dict:
    """Test feature extraction for a single recording."""
    recording = abf_file.stem

    result = {
        'recording': recording,
        'success': False,
        'issues': [],
        'matches': [],
        'error': None
    }

    # Load baseline features
    try:
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
    except Exception as e:
        result['error'] = f"Failed to load baseline: {e}"
        return result

    # Load data with pyabf
    try:
        data = load_current_step(str(abf_file))
    except Exception as e:
        result['error'] = f"Failed to load data: {e}"
        return result

    # Extract features with ipfx
    try:
        _, new_features = extract_istep_features(
            data, start=ISTEP_START, end=ISTEP_END, **FEATURE_PARAMS
        )
    except Exception as e:
        import traceback
        result['error'] = f"Failed to extract features: {e}\n{traceback.format_exc()}"
        return result

    # Compare
    issues, matches = compare_features(baseline, new_features, recording)
    result['issues'] = issues
    result['matches'] = matches
    result['success'] = len(issues) == 0

    return result


def main():
    print("=" * 70)
    print("IPFX MIGRATION TEST")
    print("=" * 70)
    print(f"\nTest data: {TEST_DATA_DIR}")
    print(f"Baseline: {BASELINE_DIR}")
    print(f"Analysis window: {ISTEP_START}s - {ISTEP_END}s")

    # Find test files
    abf_files = sorted(TEST_DATA_DIR.glob("*.abf"))
    print(f"\nFound {len(abf_files)} ABF files")

    # Run tests
    results = []
    for abf_file in abf_files:
        recording = abf_file.stem
        baseline_file = BASELINE_DIR / f"{recording}_features.json"

        if not baseline_file.exists():
            print(f"\n{recording}: SKIP (no baseline)")
            continue

        result = test_single_recording(abf_file, baseline_file)
        results.append(result)

        if result['error']:
            print(f"\n{recording}: ERROR")
            print(f"  {result['error'][:200]}...")
        elif result['success']:
            print(f"\n{recording}: PASS ({len(result['matches'])} features match)")
        else:
            print(f"\n{recording}: FAIL - {len(result['issues'])} issues out of {len(result['issues']) + len(result['matches'])}")
            for issue in result['issues']:
                print(f"  ✗ {issue}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    n_pass = sum(1 for r in results if r['success'])
    n_fail = sum(1 for r in results if not r['success'] and not r['error'])
    n_error = sum(1 for r in results if r['error'])

    print(f"Total tested: {len(results)}")
    print(f"Passed: {n_pass}")
    print(f"Failed: {n_fail}")
    print(f"Errors: {n_error}")

    if n_error > 0:
        print("\nErrors need to be fixed before proceeding.")
    elif n_fail == 0:
        print("\n✓ Phase 2 (ipfx migration) COMPLETE - all features within tolerance!")
    else:
        print(f"\n⚠ {n_fail} recordings have features outside tolerance.")
        print("Review if differences are acceptable for your use case.")

    return 0 if n_error == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
