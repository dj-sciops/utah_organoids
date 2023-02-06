from pathlib import Path
from workflow import db_prefix

import datajoint as dj

from workflow.pipeline import session, ephys, probe
from workflow.utils import get_ephys_root_data_dir

logger = dj.logger  
schema = dj.schema(db_prefix + "ingestion")


@schema
class EphysIngestion(dj.Imported):
    definition = """
    -> session.Session
    ---
    ingestion_time  : DATETIME    # Stores the start time of ephys data ingestion
    """

    def make(self, key):

        # Fetch data file
        data_path = (
                Path(get_ephys_root_data_dir()) / (session.SessionDirectory & key).fetch1("session_dir")
            )

        if not data_path.exists():
            raise FileNotFoundError(
            f"Ephys data path {data_path} doesn't exist."
            )

        
        # Populate ephys.AcquisitionSoftware
        ephys.AcquisitionSoftware.insert1(
            {"acq_software": "Intan"},
            skip_duplicates=True,
        )

        # Populate ephys.ProbeInsertion
        # Fill in dummy probe config
        probe_type = "NeuroNexus-01"
        probe_id = "001"

        logger.info(f"Populating ephys.ProbeInsertion for <{key}>")
        insertion_number = 0  # just for this session
        ephys.ProbeInsertion.insert1(
            {"insertion_number": insertion_number, "probe": probe_id} | key
        )

        # Read from probe.ProbeType.Electrode to get location of electrode site for the session probe.
        electrodes, x_coords, y_coords = (
            probe.ProbeType.Electrode & f"probe_type = '{probe_type}'"
        ).fetch("electrode", "x_coord", "y_coord")

        location_to_electrode_site_map: dict[tuple, int] = dict(
            zip(zip(x_coords, y_coords), electrodes)
        )  # {(0, 0) : 10}



def insert_clustering_parameters() -> None:
    """This is for SpyKingCircus"""
    clustering_method = "SpyKingCircus"

    ephys.ClusteringMethod.insert1(
        {
            "clustering_method": clustering_method,
            "clustering_method_desc": f"{clustering_method} clustering method",
        },
        skip_duplicates=True,
    )

    # Populate ephys.ClusterQualityLabel
    ephys.ClusterQualityLabel.insert1(
        {
            "cluster_quality_label": "n.a.",
            "cluster_quality_description": "quality label not available",
        },  # quality information does not exist
        skip_duplicates=True,
    )

    # Populate ephys.ClusteringParamSet
    ephys.ClusteringParamSet.insert_new_params(
        paramset_idx=0,
        clustering_method=clustering_method,
        paramset_desc=f"Default {clustering_method} parameter set",
        params={},  # currently, no clustering parameters available
    )
