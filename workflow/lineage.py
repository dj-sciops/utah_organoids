import datajoint as dj

schema = dj.schema()
if "custom" not in dj.config:
    dj.config["custom"] = {}

db_prefix = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(db_prefix + "differentiation")


@schema
class Family(dj.Manual):
    definition = """
    family: varchar(8)
    """


@schema
class Line(dj.Manual):
    definition = """
    line: varchar(8)
    """


@schema
class Passage(dj.Manual):
    definition = """
    passage_id: int
    -> Line
    """


@schema
class Induction(dj.Manual):
    definition = """
    induction_id: varchar(8)     # de-identified code
    ---
    -> Family
    -> Passage
    """

    class Sequence(dj.Part):
        definition = """
        -> master
        sequence: varchar(8)
        """