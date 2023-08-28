import pathlib
import djsciops.axon as dj_axon
import djsciops.settings as dj_settings
import djsciops.authentication as dj_auth

"""INSTRUCTIONS TO RUN THIS CODE
1. Install djsciops package: “pip install djsciops”
2. Run “djsciops config” on the terminal to get the path of config.yaml.
3. Make sure that config.yaml have the correct values for account_id, client_id, issuer, bucket, and role.
4. Make sure there is a local_outbox in the config.yaml.
"""

LOCAL_OUTBOX = pathlib.Path(dj_settings.get_config()["local_outbox"])
PROJECT_NAME = "utah_organoids"

config = dj_settings.get_config()
s3_session = dj_auth.Session(
    aws_account_id=config["aws"]["account_id"],
    s3_role=config["s3"]["role"],
    auth_client_id=config["djauth"]["client_id"],
)
s3_bucket = config["s3"]["bucket"]


def upload_session_data(session_dir_relpath):
    """Upload a session's data.

    Args:
        session_dir_relpath (str): Relative session path

    Example:
        If the data is located at "/Users/tolgadincer/DJRepos/utah_organoids/O6/..",
        where LOCAL_OUTBOX="/Users/tolgadincer/DJRepos/utah_organoids/", then run:
        >>> upload_session_data('O6')
    """
    session_dir_relpath = pathlib.Path(session_dir_relpath).as_posix()

    local_session_dir = LOCAL_OUTBOX / session_dir_relpath
    assert local_session_dir.exists(), f"{local_session_dir} does not exist"
    assert local_session_dir.is_dir(), f"{local_session_dir} is not a directory"

    dj_session_dir = f"{PROJECT_NAME}/inbox/{session_dir_relpath}/"
    dj_axon.upload_files(
        source=local_session_dir.as_posix(),
        destination=dj_session_dir,
        session=s3_session,
        s3_bucket=s3_bucket,
    )

    remote_files = [
        (
            pathlib.Path(x["key"]).relative_to(f"{PROJECT_NAME}/inbox").as_posix(),
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
    for f in local_session_dir.rglob("*"):
        if f.is_file():
            local_files.append(
                (f.relative_to(LOCAL_OUTBOX).as_posix(), f.stat().st_size)
            )

    if set(local_files) == set(remote_files):
        # create and upload an empty textfile named "upload_completed.txt" to signal the completion of this uploading round
        upload_completed_fp = local_session_dir / "upload_completed.txt"
        upload_completed_fp.touch()
        dj_axon.upload_files(
            source=upload_completed_fp.as_posix(),
            destination=dj_session_dir,
            session=s3_session,
            s3_bucket=s3_bucket,
        )
        return True
