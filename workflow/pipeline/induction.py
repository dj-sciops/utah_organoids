import datajoint as dj

from . import lineage

schema = dj.schema()
if "custom" not in dj.config:
    dj.config["custom"] = {}

db_prefix = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(db_prefix + "induction")


@schema
class User(dj.Manual):
    definition = """
    user: varchar(32)
    """


@schema
class InductionCulture(dj.Manual):
    definition = """
    -> lineage.Induction
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
    density=null: int           # units of percentage
    discontinued=null: bool
    induction_condition_note='': varchar(256)
    """


@schema
class InductionCultureSupplement(dj.Manual):
    definition = """
    -> InductionCultureCondition
    supplement: varchar(32)
    ---
    concentration: int 
    units: enum('micromolar', 'ng/mL')
    """


@schema
class InductionCultureMedia(dj.Manual):
    definition = """
    -> InductionCultureCondition
    media_name: varchar(32)
    ---
    media_amount: int        # Percentage of the media used in the culture, 1-100
    manufacturer='': varchar(32)
    catalog_number='': varchar(32)
    media_note='': varchar(256)
    """


@schema
class InductionCultureSubstrate(dj.Manual):
    definition = """
    -> InductionCultureCondition
    substrate: varchar(32)
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
    g_dna: bool # Was genomic DNA collected?
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
    rosette_condition_note='': varchar(256)
    """


@schema
class RosetteCultureSupplement(dj.Manual):
    definition = """
    -> RosetteCultureCondition
    supplement: varchar(32)
    ---
    concentration: int 
    units: enum('micromolar', 'ng/mL')
    """


@schema
class RosetteCultureMedia(dj.Manual):
    definition = """
    -> RosetteCultureCondition
    media_name: varchar(32)
    ---
    media_amount: int        # Percentage of the media used in the culture, 1-100
    manufacturer='': varchar(32)
    catalog_number='': varchar(32)
    media_note='': varchar(256)
    """


@schema
class RosetteCultureSubstrate(dj.Manual):
    definition = """
    -> RosetteCultureCondition
    substrate: varchar(32)
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
class Experiment(dj.Manual):
    definition = """
    experiment_id: varchar(8) # i.e. rosette id and organoid id, e.g. AS001
    """


@schema
class RosetteExperiment(dj.Manual):
    definition = """
    -> RosetteCulture
    ---
    -> [nullable] Experiment
    rosette_plan: varchar(64) # mrna lysate, oct, protein lysate, or matrigel embedding
    """


@schema
class OrganoidCulture(dj.Manual):
    definition = """ # Organoids embedded in matrigel 10cm dish for up to 5 months
    -> lineage.Induction
    matrigel_id: int
    ---
    organoid_embed_date: date
    """


@schema
class OrganoidEmbedding(dj.Manual):
    definition = """ # Each organoid is in a matrigel droplet, and multiple organoids are embedded in dish
    -> OrganoidCulture
    -> RosetteCulture
    """


@schema
class OrganoidCultureCondition(dj.Manual):
    definition = """
    -> OrganoidCulture
    organoid_condition_date: date
    ---
    organoid_relative_date: varchar(4)
    organoid_condition_note='': varchar(256)
    """


@schema
class OrganoidCultureSupplement(dj.Manual):
    definition = """
    -> OrganoidCultureCondition
    supplement: varchar(32)
    ---
    concentration: int 
    units: enum('micromolar', 'ng/mL')
    """


@schema
class OrganoidCultureMedia(dj.Manual):
    definition = """
    -> OrganoidCultureCondition
    media_name: varchar(32)
    ---
    media_amount: int        # Percentage of the media used in the culture, 1-100
    manufacturer='': varchar(32)
    catalog_number='': varchar(32)
    media_note='': varchar(256)
    """


@schema
class OrganoidCultureSubstrate(dj.Manual):
    definition = """
    -> OrganoidCultureCondition
    substrate: varchar(32)
    """


@schema
class OrganoidExperiment(dj.Manual):
    definition = """
    -> OrganoidCulture
    ---
    -> Experiment
    experiment_datetime: datetime    # Experiment start time
    ---
    experiment_dir:      varchar(256) # Path to the subject data directory
    experiment_plan:     varchar(64) # ephys, tracing
    """
