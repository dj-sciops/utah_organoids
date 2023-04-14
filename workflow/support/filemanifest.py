import os
import datajoint as dj

from workflow import ORG_NAME, WORKFLOW_NAME
from workflow.utils.paths import get_raw_root_data_dir

__all__ = ['FileManifest']

# ------------- Configure the "support-pipeline" -------------
org_vm = dj.create_virtual_module("org_vm", f"{ORG_NAME}_admin_workflow")

dj.config["stores"] = {
    "data-root": dict(
        protocol="s3",
        endpoint="s3.amazonaws.com:9000",
        bucket="dj-sciops",
        location=f"{ORG_NAME}_{WORKFLOW_NAME}",
        access_key=os.getenv("AWS_ACCESS_KEY", None),
        secret_key=os.getenv("AWS_ACCESS_SECRET", None),
        stage=get_raw_root_data_dir().parent,
    ),
}

FileManifest = org_vm.FileManifest