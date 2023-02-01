import datajoint as dj

from workflow import db_prefix

schema = dj.schema(db_prefix + "reference")
