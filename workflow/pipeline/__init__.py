import os

from . import induction, lineage, analysis
from .ephys import ephys, probe

os.environ["DJ_SUPPORT_FILEPATH_MANAGEMENT"] = "TRUE"
os.environ["EXTERN_STORE_PROTOCOL"] = "file"
