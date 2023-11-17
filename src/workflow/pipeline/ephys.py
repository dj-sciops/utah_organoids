import os
from typing import Any

import datajoint as dj
from element_array_ephys import ephys_organoids as ephys
from element_array_ephys import ephys_report, probe

from workflow import DB_PREFIX, ORG_NAME, WORKFLOW_NAME
from workflow.pipeline import culture
from workflow.utils.paths import (
    get_ephys_root_data_dir,
    get_organoid_directory,
    get_processed_root_data_dir,
)

# Set s3 stores configuration
data_root = dict(
    protocol="s3",
    endpoint="s3.amazonaws.com:9000",
    bucket="dj-sciops",
    location=f"{ORG_NAME}_{WORKFLOW_NAME}",
    access_key=os.getenv("AWS_ACCESS_KEY", None),
    secret_key=os.getenv("AWS_ACCESS_SECRET", None),
    stage=get_processed_root_data_dir().parent,
)
datajoint_blob = dict(
    protocol="s3",
    endpoint="s3.amazonaws.com:9000",
    bucket="dj-sciops",
    location=f"{ORG_NAME}_{WORKFLOW_NAME}/datajoint/blob",
    access_key=os.getenv("AWS_ACCESS_KEY", None),
    secret_key=os.getenv("AWS_ACCESS_SECRET", None),
)

stores: dict[str, Any] = dj.config.get("stores", {})
stores.setdefault("data-root", data_root)
stores.setdefault("datajoint-blob", datajoint_blob)
dj.config["stores"] = stores


if not ephys.schema.is_activated():
    ephys.activate(DB_PREFIX + "ephys", DB_PREFIX + "probe", linking_module=__name__)

__all__ = ["ephys", "probe"]
