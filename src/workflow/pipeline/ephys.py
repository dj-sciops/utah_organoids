import os
from typing import Any

import datajoint as dj
from element_array_ephys import ephys_no_curation as ephys
from element_array_ephys import ephys_report, probe
from element_array_ephys.spike_sorting import si_spike_sorting as ephys_sorter

from workflow import DB_PREFIX, ORG_NAME, WORKFLOW_NAME
from workflow.pipeline import culture
from workflow.utils.paths import (
    get_ephys_root_data_dir,
    get_organoid_directory,
    get_processed_root_data_dir,
)

__all__ = ["probe", "ephys", "ephys_report", "ephys_sorter"]

logger = dj.logger

# Set s3 stores configuration
datajoint_blob = dict(
    protocol="s3",
    endpoint="s3.amazonaws.com:9000",
    bucket="dj-sciops",
    location=f"{ORG_NAME}_{WORKFLOW_NAME}/datajoint/blob",
    access_key=os.getenv("AWS_ACCESS_KEY", None),
    secret_key=os.getenv("AWS_ACCESS_SECRET", None),
)

stores: dict[str, Any] = dj.config.get("stores", {})
stores.setdefault("datajoint-blob", datajoint_blob)
dj.config["stores"] = stores


if not ephys.schema.is_activated():
    ephys.activate(DB_PREFIX + "ephys", DB_PREFIX + "probe", linking_module=__name__)
    ephys_sorter.activate(DB_PREFIX + "ephys_sorter", ephys_module=ephys)


# Add "spykingcircus2" to ClusteringMethod
ephys.ClusteringMethod.insert1({"clustering_method": "spykingcircus2", "clustering_method_desc": ""}, skip_duplicates=True)

# Insert into ClusteringParamSet
# si.sorters.get_default_sorter_params('kilosort2_5') # api for getting default sorting parameters
params = {}
params["SI_PREPROCESSING_METHOD"] = "organoid_preprocessing"
params["SI_SORTING_PARAMS"] = {
    "general": {"ms_before": 2, "ms_after": 2, "radius_um": 100},
    "waveforms": {
        "max_spikes_per_unit": 200,
        "overwrite": True,
        "sparse": True,
        "method": "energy",
        "threshold": 0.25,
    },
    "filtering": {"freq_min": 150, "dtype": "float32"},
    "detection": {"peak_sign": "neg", "detect_threshold": 4},
    "selection": {
        "method": "smart_sampling_amplitudes",
        "n_peaks_per_channel": 5000,
        "min_n_peaks": 20000,
        "select_per_channel": False,
    },
    "clustering": {"legacy": False},
    "matching": {"method": "circus-omp-svd", "method_kwargs": {}},
    "apply_preprocessing": True,
    "shared_memory": True,
    "cache_preprocessing": {
        "mode": "memory",
        "memory_limit": 0.5,
        "delete_cache": True,
    },
    "multi_units_only": False,
    "job_kwargs": {"n_jobs": 0.8},
    "debug": False,
}
params["SI_POSTPROCESSING_PARAMS"] = {
    "extensions": {
        "random_spikes": {},
        "waveforms": {},
        "templates": {},
        "noise_levels": {},
        # "amplitude_scalings": {},
        "correlograms": {},
        "isi_histograms": {},
        "principal_components": {"n_components": 5, "mode": "by_channel_local"},
        "spike_amplitudes": {},
        "spike_locations": {},
        "template_metrics": {"include_multi_channel_metrics": True},
        "template_similarity": {},
        "unit_locations": {},
        "quality_metrics": {},
    },
    "job_kwargs": {"n_jobs": -1, "chunk_duration": "1s"},
    "export_to_phy": True,
    "export_report": True,
}

try:
    ephys.ClusteringParamSet.insert_new_params(
        clustering_method="spykingcircus2",
        paramset_desc="Default parameter set for spyking circus2 using SpikeInterface v0.101.*",
        params=params,
        paramset_idx=1,
    )
except Exception as e:
    logger.warning(f"Cannot create new paramset - {str(e)}")

