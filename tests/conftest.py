"""A DataJoint `conftest.py` file for `pytest`.

Read more about `conftest.py` under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

from pathlib import Path

import datajoint as dj
import pytest


@pytest.fixture
def dj_config():
    if Path("./dj_local_conf.json").exists():
        dj.config.load("./dj_local_conf.json")

    dj.config["safemode"] = False
    dj.config["loglevel"] = "DEBUG"

    yield dj.config
