import datajoint as dj

schema = dj.schema()
if "custom" not in dj.config:
    dj.config["custom"] = {}

db_prefix = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(db_prefix + "protocol")


@schema
class User(dj.Manual):
    definition = """
    user: varchar(32)
    """


# Move to another schema
@schema
class Family(dj.Manual):
    definition = """
    family: varchar(8)
    """


# Move to another schema
@schema
class Line(dj.Manual):
    definition = """
    line: varchar(8)
    """


@schema
class Passage(dj.Manual):
    definition = """
    passage_no: int
    -> Line
    """


@schema
class Supplement(dj.Lookup):
    definition = """
    supplement: varchar(32)
    concentration: int # in units of micromolar or ng/mL
    """


# Move to another schema
@schema
class Induction(dj.Manual):
    definition = """
    code: varchar(8)
    ---
    -> Family
    -> Passage
    """

    class Sequence(dj.Part):
        definition = """
        -> master
        sequence: varchar(8)
        """


@schema
class Media(dj.LookUp):
    definition = """
    media: varchar(32)
    """


@schema
class Substrate(dj.LookUp):
    definition = """
    substrate: varchar(32)
    """


# new schema
@schema
class InductionNotes(dj.Manual):
    definition = """
    -> Induction
    note_datetime: datetime
    ---
    media_change: bool
    induction_step=null: enum('ipsc_thaw', 'ipsc_replate', 'induction_start')
    induction_note=null: varchar(256)
    density=null: int # in percentage in units
    """

    class InductionParameters(dj.Part):
        definition = """
        -> master
        ---
        -> Supplement
        -> Media
        -> Substrate
        """


# Images will be stored with "code_datetime" naming convention.


@schema
class InductionImages(dj.Manual):
    definition = """
    -> InductionNotes
    ---
    directory: varchar(256)
    """


@schema
class Organoid(dj.Manual):
    definition = """
    organoid_id: int
    """


@schema
class OrganoidFamily(dj.Manual):
    definition = """
    -> Organoid
    -> Family
    """


@schema
class Plate(dj.Manual):
    definition = """
    plate_id: varchar(8)
    ---
    dish: varchar(8)
    code1: varchar(8)
    code2: varchar(32)
    sr: date
    -> Line
    -> User
    """

    class OrganoidPlate(dj.Part):
        definition = """
        -> master
        -> Organoid
        """
