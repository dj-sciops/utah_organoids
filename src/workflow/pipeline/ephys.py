import datajoint as dj
from element_array_ephys import ephys_organoids as ephys
from element_array_ephys import probe

from workflow import DB_PREFIX
from workflow.pipeline import culture
from workflow.utils.paths import (
    get_ephys_root_data_dir,
    get_organoid_directory,
    get_processed_root_data_dir,
)

__all__ = ["ephys", "probe"]


if not ephys.schema.is_activated():
    ephys.activate(DB_PREFIX + "ephys", DB_PREFIX + "probe", linking_module=__name__)
