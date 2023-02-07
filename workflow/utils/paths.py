import datajoint as dj
import pathlib


def get_ephys_root_data_dir():
    return dj.config.get("custom", {}).get("ephys_root_data_dir", None)


def get_session_directory(session_key: dict) -> str:
    data_dir = get_ephys_root_data_dir()

    from workflow.pipeline import session

    if not (session.SessionDirectory & session_key):
        raise FileNotFoundError(f"No session data directory defined for {session_key}")

    sess_dir = data_dir / (session.SessionDirectory & session_key).fetch1("session_dir")

    return sess_dir.as_posix()


def get_ephys_root_data_dir():
    return dj.config.get("custom", {}).get("ephys_root_data_dir", None)
