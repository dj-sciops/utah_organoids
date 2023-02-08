import pathlib

import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, ErrorLog, WorkerLog

from workflow import db_prefix, worker_max_idled_cycle
from workflow.pipeline import ephys, ephys_report, get_session_status, session
from workflow.support import ephys_support
from workflow.utils.paths import get_session_directory

logger = dj.logger

__all__ = ["standard_worker", "spike_sorting_worker", "WorkerLog", "ErrorLog"]


def auto_generate_probe_insertions():
    for skey in (
        session.Session & ephys_support.PreProbeInsertion - ephys.ProbeInsertion
    ).fetch("KEY"):
        try:
            logger.debug(
                f"Making {skey} -> {ephys.ProbeInsertion.full_table_name}"
            )
            ephys.ProbeInsertion.auto_generate_entries(skey)
            logger.debug(
                f"Success making {skey} -> {ephys.ProbeInsertion.full_table_name}"
            )
        except Exception as error:
            logger.debug(
                f"Error making {skey} -> {ephys.ProbeInsertion.full_table_name} - {str(error)}"
            )
            ErrorLog.log_exception(
                skey, ephys.ProbeInsertion.auto_generate_entries, error
            )


def auto_generate_clustering_tasks():
    for rkey in (ephys.EphysRecording - ephys.ClusteringTask).fetch("KEY"):
        try:
            ephys.ClusteringTask.auto_generate_entries(rkey, paramset_idx=0)
        except Exception as error:
            logger.error(str(error))
            ErrorLog.log_exception(
                rkey, ephys.ClusteringTask.auto_generate_entries, error
            )


def remove_completed_sessions_local_files():
    """
    For sessions that are fully completed with processing - remove any inbox files that exists locally
    """
    session_status = get_session_status()
    for session_key in (session_status & "all_done = 1").fetch("KEY"):
        sess_dir = pathlib.Path(get_session_directory(session_key))
        if sess_dir.exists():
            logger.info(
                f"All processing done for session: {session_key} - removing local files"
            )
            files = [f for f in sess_dir.rglob("*") if f.is_file()]
            for file in files:
                file.unlink()  # delete local output files


# -------- Define process(s) --------
org_name, workflow_name, _ = db_prefix.split("_")

worker_db_prefix = f"{org_name}_support_{workflow_name}_"
worker_schema_name = worker_db_prefix + "workerlog"
autoclear_error_patterns = ["%CalledProcessError%median_subtraction%"]

# standard process for non-GPU jobs
standard_worker = DataJointWorker(
    "standard_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    max_idled_cycle=worker_max_idled_cycle,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

standard_worker(ephys_support.PreProbeInsertion)
standard_worker(auto_generate_probe_insertions)
standard_worker(ephys_support.PreProbeInsertion.clean_up)

standard_worker(ephys_support.PreEphysRecording)
standard_worker(ephys.EphysRecording, max_calls=10)
standard_worker(ephys_support.PreEphysRecording.clean_up)

standard_worker(auto_generate_clustering_tasks)

standard_worker(ephys_support.PreCuratedClustering)
standard_worker(ephys.CuratedClustering, max_calls=10)
standard_worker(ephys_support.PreCuratedClustering.clean_up)

standard_worker(ephys_support.PreQualityMetrics)
standard_worker(ephys.QualityMetrics, max_calls=10)
standard_worker(ephys_support.PreQualityMetrics.clean_up)

standard_worker(ephys_support.PreWaveformSet)
standard_worker(ephys.WaveformSet, max_calls=10)
standard_worker(ephys_support.PreWaveformSet.clean_up)

standard_worker(ephys_support.PreLFP)
standard_worker(ephys.LFP, max_calls=1)
standard_worker(ephys_support.PreLFP.clean_up)

standard_worker(ephys_report.ProbeLevelReport, max_calls=10)
standard_worker(ephys_report.UnitLevelReport, max_calls=100)

standard_worker(ephys_support.ClusteringFinish, max_calls=10)
standard_worker(remove_completed_sessions_local_files)

# spike_sorting process for GPU required jobs

spike_sorting_worker = DataJointWorker(
    "spike_sorting_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    max_idled_cycle=worker_max_idled_cycle,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

spike_sorting_worker(ephys_support.PreClustering)
spike_sorting_worker(ephys.Clustering, max_calls=6)
spike_sorting_worker(ephys_support.PostClustering)
spike_sorting_worker(ephys_support.PreClustering.clean_up)
