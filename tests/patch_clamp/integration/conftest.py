"""Pytest fixtures for patch-clamp integration tests."""
import os
import pytest
from pathlib import Path
from datetime import datetime

import datajoint as dj


@pytest.fixture(scope="session")
def pipeline(dj_config):
    """
    Fixture providing access to patch-clamp pipeline modules.

    Imports pipeline modules INSIDE fixture to ensure MySQL is running
    before DataJoint tries to connect.
    """
    import matplotlib
    matplotlib.use("Agg")

    from workflow.pipeline.patch_clamp_ephys import schema_ephys as patch_clamp
    from workflow.pipeline import report

    return {
        "patch_clamp": patch_clamp,
        "report": report,
    }


@pytest.fixture(scope="session")
def sample_experiment_info():
    """
    Define the sample experiment for integration tests.

    Configure RAW_ROOT_DATA_DIR in .env.test.local to point to the
    directory containing patch-clamp session folders.

    Expected structure: {RAW_ROOT_DATA_DIR}/patch_clamp/{experiment}/{experiment}/
    """
    return {
        "experiment": "2020-08-28",
        "project": "utah_organoids",
        "directory": "patch_clamp/2020-08-28/",
        "istep_start": 0.55,
        "istep_duration": 1.0,
    }


@pytest.fixture(scope="session")
def sample_experiment_path(sample_experiment_info):
    """Get path to sample experiment data directory."""
    raw_dir = Path(os.environ["RAW_ROOT_DATA_DIR"])
    exp_path = raw_dir / sample_experiment_info["directory"] / sample_experiment_info["experiment"]
    return exp_path


@pytest.fixture(scope="function")
def require_sample_data(sample_experiment_path):
    """
    Ensure sample patch-clamp data exists. Skip test if not available.

    Tests using this fixture will be automatically skipped if the data
    directory doesn't exist.
    """
    if not sample_experiment_path.exists():
        pytest.skip(
            f"Sample data not found at: {sample_experiment_path}\n"
            "Configure RAW_ROOT_DATA_DIR in .env.test.local to enable integration tests."
        )

    # Check for ABF files
    abf_files = list(sample_experiment_path.glob("*.abf"))
    if not abf_files:
        pytest.skip(
            f"No ABF files found in: {sample_experiment_path}"
        )

    # Check for Excel metadata
    xlsx_files = list(sample_experiment_path.glob("*.xlsx"))
    if not xlsx_files:
        pytest.skip(
            f"No Excel metadata file found in: {sample_experiment_path}"
        )

    return sample_experiment_path


@pytest.fixture(scope="function")
def patch_clamp_experiment(pipeline, sample_experiment_info):
    """Register a patch-clamp experiment in the database."""
    pc = pipeline["patch_clamp"]

    experiment_entry = dict(
        experiment=sample_experiment_info["experiment"],
        project=sample_experiment_info["project"],
        use="Yes",
        directory=sample_experiment_info["directory"],
    )
    pc.EphysExperimentsForAnalysis.insert1(experiment_entry, skip_duplicates=True)

    istep_start = sample_experiment_info["istep_start"]
    istep_duration = sample_experiment_info["istep_duration"]
    timing_entry = dict(
        experiment=sample_experiment_info["experiment"],
        istep_start=istep_start,
        istep_end_1s=istep_start + 1.0,
        istep_end=istep_start + istep_duration,
        istep_duration=istep_duration,
    )
    pc.CurrentStepTimeParams.insert1(timing_entry, skip_duplicates=True)

    return {"experiment": sample_experiment_info["experiment"], "params_id": 1}


@pytest.fixture(scope="function")
def patch_clamp_populated(pipeline, patch_clamp_experiment, require_sample_data):
    """
    Populate metadata tables (Animals, PatchCells, EphysRecordings).

    Depends on require_sample_data to ensure ABF files are available.
    """
    pc = pipeline["patch_clamp"]
    key = patch_clamp_experiment

    pc.Animals.populate(key, display_progress=True)
    pc.PatchCells.populate(key, display_progress=True)
    pc.EphysRecordings.populate(key, display_progress=True)

    return key
