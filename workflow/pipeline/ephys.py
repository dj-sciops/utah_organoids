from element_array_ephys import ephys_organoids as ephys
from element_array_ephys import probe

from workflow import db_prefix

from workflow.utils.paths import (get_ephys_root_data_dir,
                                  get_processed_root_data_dir,
                                  get_subject_directory)


from .induction import OrganoidExperiment as Subject

__all__ = ["ephys", "probe"]


if not ephys.schema.is_activated():
    ephys.activate(db_prefix + "ephys", db_prefix + "probe", linking_module=__name__)
