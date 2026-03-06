"""Integration tests for patch-clamp feature extraction."""
import pytest


class TestAPandIntrinsicProperties:
    """Test AP and intrinsic property extraction from ABF recordings."""

    @pytest.fixture(autouse=True)
    def populate_features(self, pipeline, patch_clamp_populated):
        """Populate APandIntrinsicProperties for the test experiment."""
        pc = pipeline["patch_clamp"]
        pc.APandIntrinsicProperties.populate(patch_clamp_populated, display_progress=True)
        self.pc = pc
        self.key = patch_clamp_populated

    def test_features_populated(self):
        """Test that features are extracted for all recordings."""
        n_recordings = len(self.pc.EphysRecordings & self.key)
        n_features = len(self.pc.APandIntrinsicProperties & self.key)
        assert n_features == n_recordings, (
            f"Expected features for all {n_recordings} recordings, got {n_features}"
        )

    def test_has_ap_field_values(self):
        """Test that has_ap field is either 'Yes' or 'No'."""
        values = set(
            (self.pc.APandIntrinsicProperties & self.key).fetch("has_ap")
        )
        assert values.issubset({"Yes", "No"}), f"Unexpected has_ap values: {values}"

    def test_ap_recordings_have_threshold(self):
        """Test that recordings with APs have a valid AP threshold."""
        ap_query = self.pc.APandIntrinsicProperties & self.key & "has_ap = 'Yes'"
        if len(ap_query) == 0:
            pytest.skip("No recordings with APs in test data")
        thresholds = ap_query.fetch("ap_threshold")
        for t in thresholds:
            assert t is not None, "AP threshold should not be None for AP recordings"
            assert -100 < t < 0, f"AP threshold {t} mV is outside reasonable range"

    def test_ap_recordings_have_firing_rate(self):
        """Test that recordings with APs have a max firing rate."""
        ap_query = self.pc.APandIntrinsicProperties & self.key & "has_ap = 'Yes'"
        if len(ap_query) == 0:
            pytest.skip("No recordings with APs in test data")
        rates = ap_query.fetch("max_firing_rate")
        for r in rates:
            assert r is not None and r >= 0, f"Invalid max firing rate: {r}"

    def test_all_recordings_have_input_resistance(self):
        """Test that all recordings have input resistance."""
        resistances = (self.pc.APandIntrinsicProperties & self.key).fetch(
            "input_resistance"
        )
        for r in resistances:
            assert r is not None and r > 0, f"Invalid input resistance: {r}"

    def test_no_ap_recordings_have_null_slope(self):
        """Test that recordings without APs have null F-I slope."""
        no_ap_query = self.pc.APandIntrinsicProperties & self.key & "has_ap = 'No'"
        if len(no_ap_query) == 0:
            pytest.skip("No recordings without APs in test data")
        slopes = no_ap_query.fetch("f_i_curve_slope")
        for s in slopes:
            assert s is None, "F-I slope should be None for non-AP recordings"


class TestPlotGeneration:
    """Test plot file generation."""

    @pytest.fixture(autouse=True)
    def populate_plots(self, pipeline, patch_clamp_populated):
        """Populate feature extraction and plot tables."""
        pc = pipeline["patch_clamp"]
        pc.APandIntrinsicProperties.populate(patch_clamp_populated, display_progress=True)
        pc.CurrentStepPlots.populate(patch_clamp_populated, display_progress=True)
        self.pc = pc
        self.key = patch_clamp_populated

    def test_current_step_plots_populated(self):
        """Test that current step plots are generated for all recordings."""
        n_recordings = len(self.pc.EphysRecordings & self.key)
        n_plots = len(self.pc.CurrentStepPlots & self.key)
        assert n_plots == n_recordings, (
            f"Expected plots for all {n_recordings} recordings, got {n_plots}"
        )

    def test_plot_paths_not_empty(self):
        """Test that plot file paths are not empty strings."""
        paths = (self.pc.CurrentStepPlots & self.key).fetch("istep_png_large_path")
        for p in paths:
            assert p is not None and len(p) > 0, "Plot path should not be empty"

    def test_fi_curve_plots_for_ap_recordings(self):
        """Test that F-I curve plots exist for AP recordings."""
        self.pc.FICurvePlots.populate(self.key, display_progress=True)
        ap_count = len(self.pc.APandIntrinsicProperties & self.key & "has_ap = 'Yes'")
        fi_count = len(self.pc.FICurvePlots & self.key)
        assert fi_count == ap_count, (
            f"Expected F-I plots for all {ap_count} AP recordings, got {fi_count}"
        )
