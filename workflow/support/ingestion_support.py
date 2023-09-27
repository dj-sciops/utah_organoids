import datajoint as dj
import re
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

from workflow import REL_PATH_INBOX, SUPPORT_DB_PREFIX
from workflow.pipeline import ephys
from workflow.support import FileManifest

logger = dj.logger  # type: ignore

schema = dj.schema(f"{SUPPORT_DB_PREFIX}ingestion_support")


@schema
class FileProcessing(dj.Imported):
    definition = """
    -> FileManifest
    ---
    execution_time: datetime  # UTC time
    log_message='': varchar(1000)
    """

    def make(self, key):
        """
        For each new file in FileManifest, process the file to attempt to:
        1. register new entries for ephys.EphysRawFile (from .rhs files)
        2. attempt to create ephys.EphysSession
        """
        log_message = ""
        remote_fullpath = Path(key["remote_fullpath"])
        if Path(REL_PATH_INBOX) in remote_fullpath.parents:
            subject_key = {}      
            parent_dir = remote_fullpath.parent
            if remote_fullpath.suffix == ".rhs": 
                filename_prefix, start_time = re.search(r"(.*)_(\d{6}_\d{6})", remote_fullpath).groups()
                start_time = np.datetime64(
                    datetime.strptime(start_time, "%y%m%d_%H%M%S")
                )  # start time based on the file name
                ephys.EphysRawFile.insert1(
                    {
                    **subject_key,
                    "file_time": start_time,
                    "file_path": remote_fullpath.as_posix(),
                    "parent_folder": parent_dir.name,
                    "filename_prefix": filename_prefix,
                    "file": (FileManifest & key).fetch1('file'),
                    }
                )
                log_message += f"Added new raw ephys: {remote_fullpath.name}" + "\n"
            elif remote_fullpath.name == "upload_completed.txt":
                file_count = len(FileManifest & f'remote_fullpath LIKE "{parent_dir.as_posix()}%.rhs"')
                if len(ephys.EphysRawFile & {"parent_folder": parent_dir.name}) < file_count:
                    return
                # Attempt to create entries for ephys.EphysSession - the logic is as follows:
                # For all the files in the uploaded folder, create session(s) that is at most 1-hour long
                sess_config = {
                            "insertion_number": 0, 
                            "probe": "111", 
                            "electrode_config_hash": "f2b8cfac-94cd-2564-da65-60493543f043", 
                            "session_type": "lfp"                            
                }

                session_duration = timedelta(hours=1)
                file_times =  (ephys.EphysRawFile & {"parent_folder": parent_dir.name}).fetch('file_time', order_by='file_time')

                session_entries = []
                start = file_times.pop(0)
                previous = start
                while file_times:
                    current = file_times.pop(0)
                    if (current - start) >= session_duration:
                        session_entries.append((start, previous))
                        start = current
                    previous = current
                session_entries.append((start, previous))
                log_message += f"Creating {len(session_entries)} ephys session(s) for {subject_key}: {session_entries}" + "\n"
                
                ephys.EphysSession.insert({
                            **subject_key,
                            **sess_config,
                            "start_time": start, 
                            "end_time": end, 
                        } for start, end in session_entries)

        self.insert1(
            {**key, "execution_time": datetime.utcnow(), "log_message": log_message}
        )
