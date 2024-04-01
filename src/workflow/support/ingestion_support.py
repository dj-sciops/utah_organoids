import re
from datetime import datetime
from pathlib import Path
import datajoint as dj
import numpy as np
import shutil
from element_interface.utils import find_full_path

from workflow import REL_PATH_INBOX, SUPPORT_DB_PREFIX
from workflow.pipeline import ephys
from workflow.support import FileManifest

from workflow.utils.paths import (
    get_raw_root_data_dir,
    get_processed_root_data_dir,
)

logger = dj.logger  # type: ignore

schema = dj.schema(f"{SUPPORT_DB_PREFIX}ingestion_support")


@schema
class FileProcessing(dj.Imported):
    definition = """
    -> FileManifest
    ---
    execution_time: datetime  # UTC time
    """

    def make(self, key):
        """
        For each new file in FileManifest, process the file to attempt to register new entries for ephys.EphysRawFile.
        """
        remote_fullpath = Path(key["remote_fullpath"])
        if Path(REL_PATH_INBOX) in remote_fullpath.parents:
            parent_dir = remote_fullpath.parent
            if remote_fullpath.suffix in [".rhd", ".rhs"]:
                filename_prefix, start_time = re.search(
                    r"(.*)_(\d{6}_\d{6})", remote_fullpath.as_posix()
                ).groups()
                start_time = np.datetime64(
                    datetime.strptime(start_time, "%y%m%d_%H%M%S")
                )  # start time based on the file name
                ephys.EphysRawFile.insert1(
                    {
                        "file_path": remote_fullpath.relative_to(
                            REL_PATH_INBOX
                        ).as_posix(),
                        "acq_software": {".rhd": "Intan", ".rhs": "Intan"}[
                            remote_fullpath.suffix
                        ],
                        "file_time": start_time,
                        "parent_folder": parent_dir.name,
                        "filename_prefix": filename_prefix,
                    }
                )
        self.insert1({**key, "execution_time": datetime.utcnow()})


@schema
class PostCalciumImaging(dj.Imported):
    definition = """ 
    -> ephys.WaveformSet
    ---
    file_count: int
    """

    @property
    def key_source(self):
        # entries in Fluorescence that has Activity populated completely
        return ephys.WaveformSet & ephys.QualityMetrics

    def make(self, key):
        output_relpath = (ephys.ClusteringTask & key).fetch1("clustering_output_dir")
        file_count = _move_files(output_relpath)
        self.insert1({**key, "file_count": file_count})


def _move_files(output_relpath):
    """Move processed result files from local outbox to remote outbox if not empty, and remove local output directory"""
    local_outbox = get_processed_root_data_dir()
    remote_outbox = Path(get_raw_root_data_dir()).parent / "outbox"

    local_output_dir = find_full_path(local_outbox, output_relpath)
    file_count = len([f for f in local_output_dir.rglob("*") if f.is_file()])

    if file_count:
        shutil.copytree(local_output_dir, remote_outbox / output_relpath)
        shutil.rmtree(local_output_dir)

    return file_count
