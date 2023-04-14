import datajoint as dj
from element_array_ephys import ephys_organoids as ephys
from element_array_ephys import probe

from workflow import DB_PREFIX

from workflow.pipeline import induction
from workflow.utils.paths import (get_ephys_root_data_dir,
                                  get_processed_root_data_dir,
                                  get_subject_directory)

logger = dj.logger

__all__ = ["ephys", "probe"]


if not ephys.schema.is_activated():
    Subject = induction.OrganoidExperiment
    EPHYS_STORE = "ephys-store"
    FILE_STORE = "data-root"
    ephys.activate(DB_PREFIX + "ephys", DB_PREFIX + "probe", linking_module=__name__)

# insert into ProbeType, Probe and ElectrodeConfig
probe_type = "NeuroNexus-A4x16-Poly2-5mm"
probe_full_name = "A4X16-Poly2-5mm-23s-200-177-H64LP_30mm"
probe_SN = "111"

try:
    probe.ProbeType.insert1(
        {
            "probe_type": probe_type,
            "probe_full_name": probe_full_name,
        }
    )
    probe_config = {"probe_type": probe_type,
                    "site_count_per_shank": 4,
                    "col_spacing": None,
                    "row_spacing": 20,
                    "white_spacing": None,
                    "col_count_per_shank": 1,
                    "shank_count": 4,
                    "shank_spacing": 100
                    }
    with probe.ProbeType.connection.transaction:
        electrode_layouts = probe.build_electrode_layouts(**probe_config)
        probe.ProbeType.Electrode.insert(electrode_layouts)
except Exception as e:
    logger.warning(str(e))

try:
    channel_to_electrode_map = {
                                "D-000": 0,
                                "D-001": 1,
                                "D-002": 2,
                                "D-003": 3,
                                "D-004": 4,
                                "D-005": 5,
                                "D-006": 6,
                                "D-007": 7,
                                "D-008": 8,
                                "D-009": 9,
                                "D-010": 10,
                                "D-011": 11,
                                "D-012": 12,
                                "D-013": 13,
                                "D-014": 14,
                                "D-015": 15}
    electrode_keys = [
        {"probe_type": probe_type, "channel": c, "electrode": e}
        for c, e in channel_to_electrode_map.items()
    ]
    with probe.Probe.connection.transaction:
        probe.Probe.insert1(
        {
            "probe": probe_SN,
            "probe_type": probe_type,
            "probe_comment": "",
        })
        ephys.generate_electrode_config(
            probe_type=probe_type, electrode_keys=electrode_keys
        )   
except Exception as e:
    logger.warning(str(e))
    