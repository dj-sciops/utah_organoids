import datajoint as dj

from . import differentiation

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


@schema
class Supplement(dj.Lookup):
    definition = """
    supplement: varchar(32)
    concentration: int # units of micromolar or ng/mL
    """


@schema
class Media(dj.Lookup):
    definition = """
    media: varchar(32)
    """


@schema
class Substrate(dj.Lookup):
    definition = """
    substrate: varchar(32)
    """


@schema
class InductionCulture(dj.Manual):
    definition = """
    -> differentiation.InductionID
    dish_id: int
    """


@schema
class InductionCultureCondition(dj.Manual):
    definition = """
    -> InductionCulture
    induction_condition_date: date
    ---
    induction_step: enum('ipsc_replate', 'induction_start', 'media_change')
    media_change=null: bool
    density=null: int           # units of %
    discontinued=null: bool
    -> [nullable] Supplement
    -> [nullable] Media
    -> [nullable] Substrate
    induction_condition_note='': varchar(256)
    """


@schema
class InductionImage(dj.Manual):
    definition = """
    -> InductionCulture
    induction_image_date: date
    ---
    directory: varchar(256) # Images stored with "code_datetime" naming convention.
    """


@schema
class InductionDNA(dj.Manual):
    definition = """
    -> InductionCulture
    ---
    gDNA: bool # Was genomic DNA collected?
    """


@schema
class ExperimentID(dj.Manual):
    definition = """
    experiment_id: varchar(8) # i.e. rosette id and organoid id, e.g. AS001
    """


@schema
class RosetteCulture(dj.Manual):
    definition = """
    -> InductionCulture
    plate_id: varchar(4)
    well_id: varchar(4)
    ---
    -> User
    single_rosette_date: date
    induction_date: date
    amplification_date: date    # egf fgf treatment

    unique index (induction_id, dish_id, plate_id, well_id)
    """


@schema
class RosetteCultureCondition(dj.Manual):
    definition = """
    -> RosetteCulture
    rosette_condition_date: date
    ---
    rosette_relative_date: varchar(4)
    -> [nullable] Supplement
    -> [nullable] Media
    -> [nullable] Substrate
    rosette_condition_note='': varchar(256)
    """


@schema
class RosetteImage(dj.Manual):
    definition = """
    -> RosetteCulture
    rosette_image_date: date
    ---
    directory: varchar(256) # Images stored with "code_datetime" naming convention.
    """


@schema
class RosetteExperiment(dj.Manual):
    definition = """
    -> RosetteCulture
    ---
    -> [nullable] ExperimentID
    rosette_plan: varchar(64) # mrna lysate, oct, protein lysate, or matrigel embedding
    """


@schema
class OrganoidCulture(dj.Manual):
    definition = """ # Organoids embedded in matrigel 10cm dish for up to 5 months
    -> differentiation.InductionID
    matrigel_id: int
    ---
    organoid_embed_date: date
    """
    class Organoid(dj.Part):
        definition = """ # Each organoid is in a matrigel droplet, and multiple organoids are embedded in dish
        -> master
        -> RosetteCulture
        """


@schema
class OrganoidCultureCondition(dj.Manual):
    definition = """
    -> OrganoidCulture
    organoid_condition_date: date
    ---
    organoid_relative_date: varchar(4)
    -> [nullable] Supplement
    -> [nullable] Media
    -> [nullable] Substrate
    organoid_condition_note='': varchar(256)
    """


@schema
class OrganoidExperiment(dj.Manual):
    definition = """
    -> OrganoidCulture
    ---
    -> ExperimentID
    experiment_plan: varchar(64) # mrna lysate, oct, protein lysate
    """