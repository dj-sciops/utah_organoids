"""Unit tests for ABF file I/O and current-step loading."""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestLoadCurrentStep:
    """Tests for load_current_step() function."""

    @pytest.fixture
    def load_current_step(self):
        """Import the function under test."""
        from workflow.pipeline.patch_clamp_ephys.file_io import load_current_step
        return load_current_step

    def test_missing_abf_raises(self, load_current_step, tmp_path):
        """Test that missing ABF file raises an error."""
        with pytest.raises(Exception):
            load_current_step(tmp_path / "nonexistent.abf")


class TestFeatureNameDict:
    """Tests for feature_name_dict mapping."""

    @pytest.fixture
    def feature_names(self):
        """Import feature name dict."""
        from workflow.pipeline.patch_clamp_ephys.visualization.feature_annotations import (
            feature_name_dict,
        )
        return feature_name_dict

    def test_feature_names_is_dict(self, feature_names):
        """Test that feature_name_dict is a dictionary."""
        assert isinstance(feature_names, dict)

    def test_feature_names_has_required_keys(self, feature_names):
        """Test that essential feature names are present."""
        expected_keys = [
            "input_resistance",
            "ap_threshold",
            "max_firing_rate",
        ]
        for key in expected_keys:
            assert key in feature_names, f"Missing feature name: {key}"

    def test_feature_names_values_are_strings(self, feature_names):
        """Test that all display names are non-empty strings."""
        for key, value in feature_names.items():
            assert isinstance(value, str) and len(value) > 0, (
                f"Feature {key} has invalid display name: {value}"
            )
