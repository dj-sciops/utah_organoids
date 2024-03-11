import os
from typing import Any

import datajoint as dj
from element_array_ephys import ephys_organoids as ephys
from element_array_ephys import ephys_report, probe
from element_array_ephys.spike_sorting import si_preprocessing as ephys_preprocessing
from element_array_ephys.spike_sorting import si_spike_sorting as ephys_sorter

from workflow import DB_PREFIX, ORG_NAME, WORKFLOW_NAME
from workflow.pipeline import culture
from workflow.utils.paths import (
    get_ephys_root_data_dir,
    get_organoid_directory,
    get_processed_root_data_dir,
)

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

# Modify key_source
ephys.Clustering.key_source = (
    ephys.Clustering.key_source - ephys_sorter.PreProcessing.key_source
).proj() + ephys_sorter.PostProcessing.proj()


# Insert into ClusteringParamSet
# si.sorters.get_default_sorter_params('kilosort2_5') # api for getting default sorting parameters
params = {}
params["SI_SORTING_PARAMS"] = {
    "general": {"ms_before": 2, "ms_after": 2, "radius_um": 100},
    "waveforms": {
        "max_spikes_per_unit": 200,
        "overwrite": True,
        "sparse": True,
        "method": "ptp",
        "threshold": 1,
    },
    "filtering": {"freq_min": 150, "dtype": "float32"},
    "detection": {"peak_sign": "neg", "detect_threshold": 5},
    "selection": {"n_peaks_per_channel": 5000, "min_n_peaks": 20000},
    "localization": {},
    "clustering": {},
    "matching": {},
    "apply_preprocessing": True,
    "shared_memory": True,
    "job_kwargs": {"n_jobs": -1},
}

params["SI_PREPROCESSING_METHOD"] = "organoid"
params["SI_WAVEFORM_EXTRACTION_PARAMS"] = {
    "ms_before": 1.0,
    "ms_after": 2.0,
    "max_spikes_per_unit": 500,
}
params["SI_QUALITY_METRICS_PARAMS"] = {"n_components": 5, "mode": "by_channel_local"}
params["SI_JOB_KWARGS"] = {"n_jobs": -1, "chunk_size": 30000}

ephys.ClusteringParamSet.insert_new_params(
    clustering_method="spykingcircus2",
    paramset_desc="Default parameter set for spyking circus2",
    params=params,
    paramset_idx=0,
)
