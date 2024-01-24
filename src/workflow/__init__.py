import os

import datajoint as dj

# from scripts.initiate_session import upload_session_data

os.environ["DJ_SUPPORT_FILEPATH_MANAGEMENT"] = "TRUE"

dj.config["filepath_checksum_size_limit"] = 1000000000

if "custom" not in dj.config:
    dj.config["custom"] = {}


dj.config["custom"]["database.prefix"] = os.getenv(
    "DATABASE_PREFIX", dj.config["custom"].get("database.prefix", "")
)

dj.config["custom"]["raw_root_data_dir"] = os.getenv(
    "RAW_ROOT_DATA_DIR", dj.config["custom"].get("raw_root_data_dir", "")
)

dj.config["custom"]["processed_root_data_dir"] = os.getenv(
    "PROCESSED_ROOT_DATA_DIR", dj.config["custom"].get("processed_root_data_dir", "")
)

DB_PREFIX: str = dj.config["custom"].get("database.prefix", "")
ORG_NAME, WORKFLOW_NAME, *_ = DB_PREFIX.split("_")
SUPPORT_DB_PREFIX = f"{ORG_NAME}_support_{WORKFLOW_NAME}_"
REL_PATH_INBOX = f"{ORG_NAME}_{WORKFLOW_NAME}/inbox"
REL_PATH_OUTBOX = f"{ORG_NAME}_{WORKFLOW_NAME}/outbox"
WORKER_MAX_IDLED_CYCLE = int(
    os.getenv(
        "WORKER_MAX_IDLED_CYCLE", dj.config["custom"].get("worker_max_idled_cycle", 3)
    )
)


def get_workflow_operation_overview():
    """Get the workflow operation overview

    Returns:
        pd.DataFrame: pandas dataframe
    """
    from datajoint_utilities.dj_worker.utils import (
        get_workflow_operation_overview as _get_workflow_operation_overview,
    )

    return (
        _get_workflow_operation_overview(
            db_prefixes=[DB_PREFIX, f"{DB_PREFIX}support_"],
            worker_schema_name=f"{ORG_NAME}_support_{WORKFLOW_NAME}_workerlog",
        )
        .sort_index()
        .reset_index()
    )
