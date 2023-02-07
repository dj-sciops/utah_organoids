from pathlib import Path
from workflow import db_prefix

import datajoint as dj
import numpy as np

from element_interface import intan_loader as intan
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
        
        # Load the data
        data = intan.load_rhs(data_path)
        
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

        # Fill in dummy parameters including probe config
        probe_type = "NeuroNexus-01"
        probe_id = "001"
        acq_software = "Intan"
        recording_datetime = (session.Session & key).fetch1("session_datetime")


        # Populate ephys.AcquisitionSoftware
        ephys.AcquisitionSoftware.insert1(
            {"acq_software": acq_software},
            skip_duplicates=True,
        )

        probe_config = dict(
                        probe_type=probe_type,
                        site_count_per_shank=16,
                        col_spacing=None,
                        row_spacing=20,
                        white_spacing=None,
                        col_count_per_shank=1,
                        shank_count=2,
                        shank_spacing=100,
                    )

        electrode_layouts = probe.build_electrode_layouts(**probe_config)
        probe.ProbeType.insert1(dict(probe_type=probe_type), skip_duplicates=True)
        probe.ProbeType.Electrode.insert(electrode_layouts, skip_duplicates=True)

        probe.Probe.insert1(dict(
                        probe=probe_id,
                        probe_type=probe_type,
                        probe_comment="dummy probe"
            ), skip_duplicates=True)


        # Get used electrodes for the session
        used_electrodes = [''.join(channel.split("-")[1:]) for channel in data["recordings"] if channel.startswith("amp")]
        [e for e in used_electrodes ]

        used_electrodes = [int(e[1:]) if e.startswith("B") else int(e[1:]) + 16 for e in used_electrodes]

        # Populate probe.ElectrodeConfig and probe.ElectrodeConfig.Electrode
        econfig = ephys.generate_electrode_config(
            probe_type=probe_type,
            electrode_keys=[
                {"probe_type": probe_type, "electrode": e}
                for e in used_electrodes
            ],
        )

        # Populate ephys.ProbeInsertion
        insertion_number = 0  # just for this session
        ephys.ProbeInsertion.insert1(
            {"insertion_number": insertion_number, "probe": probe_id} | key, skip_duplicates=True
        )

        # Populate ephys.EphysRecording
        ephys.EphysRecording.insert1(
            {
                "insertion_number": insertion_number,
                "acq_software": acq_software,
                "sampling_rate": data["header"]["sample_rate"],
                "recording_datetime": recording_datetime,
                "recording_duration": data["timestamps"][-1],
            }
            | key
            | econfig,
            allow_direct_insert=True,
        )
        
        # Populate ephys.LFP
        ephys_recording_key = (ephys.EphysRecording & key).fetch1("KEY")

        ephys.LFP.insert1(
        ephys_recording_key | 
            {
            "lfp_sampling_rate": data["header"]["sample_rate"],
            "lfp_time_stamps": data["timestamps"],
            "lfp_mean": np.mean(np.array([data["recordings"][d] for d in data["recordings"] if d.startswith("amp")]), axis=0)
            }, 
            allow_direct_insert=True
        )
        
        # Populate ephys.LFP.Electrode
        electrode_query = (
            probe.ProbeType.Electrode
            * probe.ElectrodeConfig.Electrode
            * ephys.EphysRecording
            & key 
        )
        
        lfp_channel_ind = [electrode for electrode in data["recordings"] if electrode.startswith("amp")]

        for recorded_site in lfp_channel_ind:
            ephys.LFP.Electrode.insert1(
                ephys_recording_key |
                ephys_recording_key |
                {"lfp": data["recordings"][recorded_site]},
            allow_direct_insert=True
            )


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
