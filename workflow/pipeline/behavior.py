import datajoint as dj
from .ephys import ephys, event, Session, probe
from workflow import db_prefix

from pathlib import Path
import numpy as np

from element_interface.intan_loader import load_rhs
from workflow.utils.paths import get_ephys_root_data_dir, get_session_dir
from element_interface.utils import find_full_path, find_root_directory

schema = dj.schema(db_prefix + "behavior")


@schema
class BehaviorIngestion(dj.Imported):
    definition = """
    -> Session
    ---
    ingestion_time : datetime    # Stores the start time of ephys data ingestion
    """

    def make(self, key):
        import re
        from datetime import datetime, timedelta

        # Assuming there are subdirectories. Need to understand why some folders don't have subdirectories.
        session_dir = find_full_path(get_ephys_root_data_dir(), get_session_dir(key))

        sub_folders = list(session_dir.glob("*"))

        session_start_time = min(
            [
                datetime.strptime(
                    " ".join(re.findall(r"[0-9]{6}", sub_folder.name)),
                    "%Y%m%d %H%M%S",
                )
                for sub_folder in sub_folders
            ]
        )

        event.BehaviorRecording.insert1(
            dict(
                **key,
                recording_start_time=session_start_time,
                recording_duration=sum(
                    [
                        load_rhs(sub_folder, "time.dat")["timestamps"][-1]
                        for sub_folder in sub_folders
                    ]
                ),
                recording_notes="Duration not counting the gaps, if any.",
            )
        )

        event.BehaviorRecording.File.insert(
            [
                dict(
                    **key,
                    filepath=sub_folder.relative_to(
                        get_ephys_root_data_dir()
                    ).as_posix(),
                )
                for sub_folder in sub_folders
            ]
        )

        for sub_folder in sub_folders:
            event_type = sub_folder.name.split("_")[1]  # base
            event.EventType.insert(
                [(f"{event_type}_start", ""), (f"{event_type}_end", "")],
                skip_duplicates=True,
            )
            duration = load_rhs(sub_folder, "time.dat")["timestamps"][-1]
            start_time = datetime.strptime(
                " ".join(re.findall(r"[0-9]{6}", sub_folder.name)),
                "%Y%m%d %H%M%S",
            )
            event.Event.insert(
                [
                    dict(
                        **key,
                        event_type=f"{event_type}_start",
                        event_start_time=(
                            start_time - session_start_time
                        ).total_seconds(),
                    ),
                    dict(
                        **key,
                        event_type=f"{event_type}_end",
                        event_start_time=(
                            start_time
                            + timedelta(seconds=duration)
                            - session_start_time
                        ).total_seconds(),
                    ),
                ],
                allow_direct_insert=True,
            )


event.AlignmentEvent.insert1(
    dict(
        alignment_name=f"base",
        alignment_description="events start at base_start until base_end, centered at base_start",
        alignment_event_type="base_start",
        alignment_time_shift=0,
        start_event_type="base_start",
        start_time_shift=0,
        end_event_type="base_end",
        end_time_shift=0,
    )
)
