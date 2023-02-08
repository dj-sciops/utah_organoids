from workflow.pipeline import ephys, session


def get_session_status():
    """Determine which tables have been autopopulated.
    Returns:
        A joined table indicating the number of entries several database tables starting at the session level.
    """
    session_process_status = session.Session

    session_process_status *= session.Session.aggr(
        ephys.ProbeInsertion,
        insertion="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.EphysRecording,
        ephys_recording="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.LFP, lfp="count(insertion_number)", keep_all_rows=True
    )
    session_process_status *= session.Session.aggr(
        ephys.ClusteringTask,
        clustering_task="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.Clustering,
        clustering="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.CuratedClustering,
        curated_clustering="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.QualityMetrics,
        qc_metrics="count(insertion_number)",
        keep_all_rows=True,
    )
    session_process_status *= session.Session.aggr(
        ephys.WaveformSet,
        waveform="count(insertion_number)",
        keep_all_rows=True,
    )

    return session_process_status.proj(
        ..., all_done="insertion > 0 AND waveform = clustering_task"
    )
