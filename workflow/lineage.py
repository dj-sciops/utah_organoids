import datajoint as dj

schema = dj.schema()
if "custom" not in dj.config:
    dj.config["custom"] = {}

db_prefix = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(db_prefix + "lineage")


@schema
class Induction(dj.Manual):
    definition = """
    induction_id: varchar(8)     # de-identified code
    ---
    family: varchar(8)
    line: varchar(8)
    passage_id: int
    """

    class Sequence(dj.Part):
        definition = """
        -> master
        sequence: varchar(8)
        """