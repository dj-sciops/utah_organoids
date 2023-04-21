import datajoint as dj

if "custom" not in dj.config:
    dj.config["custom"] = {}

DB_PREFIX = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(DB_PREFIX + "lineage")


@schema
class Lineage(dj.Manual):
    definition = """
    induction_id: varchar(8)     # de-identified code
    ---
    family: varchar(8)
    line: varchar(8)
    passage_id: int
    """

@schema
class LineageSequence(dj.Manual):
    definition = """
    -> Lineage
    sequence: varchar(8)
    """
