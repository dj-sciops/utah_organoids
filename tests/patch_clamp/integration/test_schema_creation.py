"""Integration tests for patch-clamp schema creation and table relationships."""
import pytest


class TestSchemaCreation:
    """Test that patch-clamp schemas load and tables exist."""

    def test_patch_clamp_schema_loads(self, pipeline):
        """Test that patch_clamp module loads successfully."""
        assert pipeline["patch_clamp"] is not None

    def test_report_schema_loads(self, pipeline):
        """Test that report module loads successfully."""
        assert pipeline["report"] is not None

    def test_core_tables_exist(self, pipeline):
        """Test that all core patch-clamp tables exist."""
        pc = pipeline["patch_clamp"]
        assert hasattr(pc, "EphysExperimentsForAnalysis")
        assert hasattr(pc, "Animals")
        assert hasattr(pc, "PatchCells")
        assert hasattr(pc, "EphysRecordings")
        assert hasattr(pc, "CurrentStepTimeParams")
        assert hasattr(pc, "APandIntrinsicProperties")

    def test_plot_tables_exist(self, pipeline):
        """Test that all plot tables exist."""
        pc = pipeline["patch_clamp"]
        assert hasattr(pc, "CurrentStepPlots")
        assert hasattr(pc, "FICurvePlots")
        assert hasattr(pc, "VICurvePlots")
        assert hasattr(pc, "FirstSpikePlots")
        assert hasattr(pc, "PhasePlanes")
        assert hasattr(pc, "FirstSpikeFirstDerivativePlots")
        assert hasattr(pc, "FirstSpikeSecondDerivativePlots")
        assert hasattr(pc, "CombinedPlotsWithText")
        assert hasattr(pc, "AnimatedCurrentStepPlots")

    def test_report_part_tables_exist(self, pipeline):
        """Test that PatchClampReport part tables exist."""
        report = pipeline["report"]
        assert hasattr(report.PatchClampReport, "FICurve")
        assert hasattr(report.PatchClampReport, "VICurve")
        assert hasattr(report.PatchClampReport, "FirstSpike")
        assert hasattr(report.PatchClampReport, "PhasePlane")
        assert hasattr(report.PatchClampReport, "CurrentStep")
        assert hasattr(report.PatchClampReport, "FirstSpikeDerivative")
        assert hasattr(report.PatchClampReport, "FirstSpikeSecondDerivative")
        assert hasattr(report.PatchClampReport, "CombinedPlot")
        assert hasattr(report.PatchClampReport, "AnimatedTrace")


class TestExperimentRegistration:
    """Test experiment registration and metadata insertion."""

    def test_experiment_insertion(self, pipeline, patch_clamp_experiment):
        """Test that experiment can be registered."""
        pc = pipeline["patch_clamp"]
        assert len(pc.EphysExperimentsForAnalysis & patch_clamp_experiment) == 1

    def test_timing_params_insertion(self, pipeline, patch_clamp_experiment):
        """Test that timing parameters are registered."""
        pc = pipeline["patch_clamp"]
        assert len(pc.CurrentStepTimeParams & patch_clamp_experiment) == 1

    def test_timing_params_values(self, pipeline, patch_clamp_experiment):
        """Test that timing parameter values are correct."""
        pc = pipeline["patch_clamp"]
        params = (pc.CurrentStepTimeParams & patch_clamp_experiment).fetch1()
        assert params["istep_start"] == 0.55
        assert params["istep_duration"] == 1.0
        assert params["istep_end"] == 1.55


class TestMetadataPopulation:
    """Test metadata table population from Excel/ABF files."""

    def test_animals_populated(self, pipeline, patch_clamp_populated):
        """Test that Animals table is populated."""
        pc = pipeline["patch_clamp"]
        assert len(pc.Animals & patch_clamp_populated) == 1

    def test_animals_has_strain(self, pipeline, patch_clamp_populated):
        """Test that strain info is extracted from Excel."""
        pc = pipeline["patch_clamp"]
        strain = (pc.Animals & patch_clamp_populated).fetch1("strain")
        assert strain is not None and len(strain) > 0

    def test_patch_cells_populated(self, pipeline, patch_clamp_populated):
        """Test that PatchCells table is populated."""
        pc = pipeline["patch_clamp"]
        n_cells = len(pc.PatchCells & patch_clamp_populated)
        assert n_cells > 0, "Expected at least one patched cell"

    def test_recordings_populated(self, pipeline, patch_clamp_populated):
        """Test that EphysRecordings table is populated."""
        pc = pipeline["patch_clamp"]
        n_recordings = len(pc.EphysRecordings & patch_clamp_populated)
        assert n_recordings > 0, "Expected at least one recording"

    def test_recordings_have_abf_files(self, pipeline, patch_clamp_populated):
        """Test that recordings reference ABF file names."""
        pc = pipeline["patch_clamp"]
        recordings = (pc.EphysRecordings & patch_clamp_populated).fetch("recording")
        for rec in recordings:
            assert rec.endswith(
                tuple(str(i) for i in range(10))
            ), f"Recording {rec} doesn't look like an ABF file stem"
