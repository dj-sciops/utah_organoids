import pathlib

import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, ErrorLog, WorkerLog

from workflow import DB_PREFIX, SUPPORT_DB_PREFIX, WORKER_MAX_IDLED_CYCLE
from workflow.pipeline import analysis, ephys
from workflow.support import ingestion_support

logger = dj.logger

__all__ = ["standard_worker", "WorkerLog", "ErrorLog"]


# -------- Define process(s) --------
autoclear_error_patterns = []

# standard process for non-GPU jobs
standard_worker = DataJointWorker(
    "standard_worker",
    worker_schema_name=f"{SUPPORT_DB_PREFIX}workerlog",
    DB_PREFIX=[DB_PREFIX, SUPPORT_DB_PREFIX],
    run_duration=-1,
    max_idled_cycle=WORKER_MAX_IDLED_CYCLE,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

standard_worker(ingestion_support.FileProcessing)
standard_worker(ephys.EphysSessionInfo, max_calls=5)
standard_worker(ephys.LFP, max_calls=5)
standard_worker(analysis.LFPSpectrogram, max_calls=5)
