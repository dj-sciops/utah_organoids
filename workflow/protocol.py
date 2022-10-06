import datajoint as dj

schema = dj.schema()
if "custom" not in dj.config:
    dj.config["custom"] = {}

db_prefix = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(db_prefix + 'protocol')

@schema
class User(dj.Manual):
    definition = """
    user: varchar(32)
    """

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
class Induction(dj.Manual):
     definition = """
     code: varchar(8)
     ---
     -> Family
     -> Line
     """

     class Sequence(dj.Part):
          definition = """
          -> master
          sequence: varchar(8)
          """

@schema
class InductionNotes(dj.Manual):
     definition = """
     -> Induction
     note_datetime: datetime
     ---
     induction_step=null: enum('ipsc_start', 'ipsc_replate', 'induction_start')
     induction_note=null: varchar(256)
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
