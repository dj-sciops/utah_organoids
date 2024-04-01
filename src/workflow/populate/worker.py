import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, ErrorLog, WorkerLog

from workflow import DB_PREFIX, SUPPORT_DB_PREFIX, WORKER_MAX_IDLED_CYCLE
from workflow.pipeline import analysis, ephys, ephys_sorter
from workflow.support import ingestion_support

logger = dj.logger

__all__ = [
    "standard_worker",
    "spike_processing_worker",
    "spike_sorting_worker",
    "WorkerLog",
    "ErrorLog",
]


# -------- Define worker(s) --------
autoclear_error_patterns = []
worker_schema_name = (f"{SUPPORT_DB_PREFIX}workerlog",)

# standard process for non-GPU jobs
standard_worker = DataJointWorker(
    "standard_worker",
    worker_schema_name,
    db_prefix=[DB_PREFIX, SUPPORT_DB_PREFIX],
    run_duration=-1,
    max_idled_cycle=WORKER_MAX_IDLED_CYCLE,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)
# spike_sorting process for nonGPU-required jobs
spike_processing_worker = DataJointWorker(
    "spike_processing_worker",
    worker_schema_name,
    db_prefix=[DB_PREFIX, SUPPORT_DB_PREFIX],
    run_duration=-1,
    max_idled_cycle=WORKER_MAX_IDLED_CYCLE,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)
# spike sorting process for GPU involved jobs
spike_sorting_worker = DataJointWorker(
    "spike_sorting_worker",
    worker_schema_name,
    db_prefix=[DB_PREFIX, SUPPORT_DB_PREFIX],
    run_duration=-1,
    max_idled_cycle=WORKER_MAX_IDLED_CYCLE,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

# -------- Define flow(s) --------

# ephys
standard_worker(ingestion_support.FileProcessing)
standard_worker(ephys.EphysSessionInfo, max_calls=200)
standard_worker(ephys.LFP, max_calls=10)
standard_worker(analysis.LFPSpectrogram, max_calls=10)
spike_processing_worker(ephys_sorter.PreProcessing, max_calls=6)
spike_sorting_worker(ephys_sorter.SIClustering, max_calls=6)
spike_processing_worker(ephys_sorter.PostProcessing, max_calls=6)
standard_worker(ephys.CuratedClustering, max_calls=5)
standard_worker(ephys.WaveformSet, max_calls=5)
standard_worker(ephys.QualityMetrics, max_calls=5)
