import os
import datajoint as dj
from pathlib import Path

from workflow import DB_PREFIX
from workflow.utils.paths import get_raw_root_data_dir, get_processed_root_data_dir

logger = dj.logger

s3_session, s3_bucket = None, None

"""INSTRUCTIONS TO RUN THIS CODE
1. Install djsciops package: “pip install djsciops”
2. Run “djsciops config” on the terminal to get the path of config.yaml.
3. Make sure that config.yaml have the correct values for account_id, client_id, issuer, bucket, and role.
4. Make sure there is a local_outbox in the config.yaml.
"""


def _get_axon_s3_session():
    import djsciops.authentication as dj_auth
    import djsciops.settings as dj_settings

    global s3_session, s3_bucket
    if s3_session is not None:
        return s3_session, s3_bucket

    dj_sciops_config = dj_settings.get_config()
    s3_session = dj_auth.Session(
        aws_account_id=dj_sciops_config["aws"]["account_id"],
        s3_role=dj_sciops_config["s3"]["role"],
        auth_client_id=dj_sciops_config["djauth"]["client_id"],
        auth_client_secret=dj_sciops_config["djauth"].get("client_secret"),
    )
    s3_bucket = dj_sciops_config["s3"]["bucket"]
    return s3_session, s3_bucket


def upload_session_data(session_dir_relpath):
    """Upload a session's data.

    Args:
        session_dir_relpath (str): Relative session path

    Example:
        If the data is located at "/Users/tolgadincer/DJRepos/utah_organoids/O6/..",
        where LOCAL_OUTBOX="/Users/tolgadincer/DJRepos/utah_organoids/", then run:
        >>> upload_session_data('O6')
    """
    import djsciops.axon as dj_axon

    s3_session, s3_bucket = _get_axon_s3_session()
    session_dir_relpath = Path(session_dir_relpath).as_posix()

    root_data_dir = get_raw_root_data_dir()
    local_session_dir = root_data_dir / session_dir_relpath
    assert local_session_dir.exists(), f"{local_session_dir} does not exist"
    assert local_session_dir.is_dir(), f"{local_session_dir} is not a directory"

    dj_session_dir = f"{DB_PREFIX[:-1]}/inbox/{session_dir_relpath}/"
    dj_axon.upload_files(
        source=local_session_dir.as_posix(),
        destination=dj_session_dir,
        session=s3_session,
        s3_bucket=s3_bucket,
    )

    remote_files = [
        (
            Path(x["key"]).relative_to(f"{DB_PREFIX[:-1]}/inbox").as_posix(),
            x["_size"],
        )
        for x in dj_axon.list_files(
            session=s3_session,
            s3_bucket=s3_bucket,
            s3_prefix=dj_session_dir,
            as_tree=False,
        )
    ]

    local_files = []
    for f in local_session_dir.rglob("[!.]*"):
        if f.is_file() and not f.name == "upload_completed.txt":
            local_files.append(
                (f.relative_to(root_data_dir).as_posix(), f.stat().st_size)
            )

    if set(local_files) != set(remote_files):
        raise AssertionError(f"Incomplete data upload - try again")
    else:
        # create and upload an empty textfile named "upload_completed.txt" to signal the completion of this uploading round
        upload_completed_fp = local_session_dir / "upload_completed.txt"
        upload_completed_fp.touch()
        dj_axon.upload_files(
            source=upload_completed_fp.as_posix(),
            destination=dj_session_dir,
            session=s3_session,
            s3_bucket=s3_bucket,
        )


def download_directory(relative_dir: str, dir_type: str = "outbox"):
    """Download data from S3 to local outbox.

    Args:
        relative_dir (str): path relative to the output directory.
    """
    import djsciops.axon as dj_axon

    if (
            not relative_dir
            and dj.utils.user_choice(f"Are you sure you want to download the entire '{dir_type}' directory?") != "yes"
    ):
        print("Canceled download.")
        return

    s3_session, s3_bucket = _get_axon_s3_session()

    if dir_type == "inbox":
        local_dir = get_raw_root_data_dir() / relative_dir
    elif dir_type == "outbox":
        local_dir = get_processed_root_data_dir() / relative_dir
    else:
        raise ValueError(f"Invalid dir_type: {dir_type}")

    dj_axon.download_files(
        session=s3_session,
        s3_bucket=s3_bucket,
        source=f"{DB_PREFIX[:-1]}/{dir_type}/{relative_dir}/",
        destination=f'{local_dir}{os.sep}',
    )
    return local_dir


def download_spike_sorted_results(clustering_key):
    """Download spike sorted results from S3 to local outbox.

    Args:
        clustering_key (dict): clustering key

    Returns:
        Path: local directory path
    """
    ephys = dj.create_virtual_module("ephys", DB_PREFIX + "ephys")

    output_relpath = (ephys.ClusteringTask & clustering_key).fetch1(
        "clustering_output_dir"
    )

    return download_directory(output_relpath)
