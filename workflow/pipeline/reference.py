import datajoint as dj

from workflow import db_prefix

schema = dj.schema(db_prefix + "reference")


@schema
class SkullReference(dj.Lookup):
    definition = """
    reference   : varchar(60)
    """
    contents = zip(
        ["bregma", "lambda", "dura", "skull_surface", "sagittal_suture", "sinus"]
    )
