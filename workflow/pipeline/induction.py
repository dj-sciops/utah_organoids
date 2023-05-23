import datajoint as dj

from . import lineage

if "custom" not in dj.config:
    dj.config["custom"] = {}

DB_PREFIX = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(DB_PREFIX + "induction")


@schema
class User(dj.Manual):
    definition = """
    user: varchar(32)
    """


@schema
class InductionCulture(dj.Manual):
    definition = """ # Plate contains 6 wells
    -> lineage.Lineage
    induction_plate_id: varchar(4)
    """


@schema
class InductionCultureWell(dj.Manual):
    definition = """ # Plate contains 6 wells
    -> InductionCulture
    induction_well_id: int
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
    supplement: enum('Dorsomorphin', 'SB431542')
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
    percent_media_changed: int        # Percentage of the media used in the culture, 1-100
    manufacturer='': varchar(32)
    catalog_number='': varchar(32)
    media_note='': varchar(256)
    """


@schema
class InductionCultureSubstrate(dj.Manual):
    definition = """
    -> InductionCultureCondition
    substrate: varchar(32) # matrigel
    """


@schema
class InductionCultureImage(dj.Manual):
    definition = """
    -> InductionCulture
    induction_image_date: date
    ---
    directory: varchar(256) # Images stored with "code_datetime" naming convention.
    """


@schema
class InductionCultureDNA(dj.Manual):
    definition = """
    -> InductionCulture
    ---
    genomic_dna: bool # Was genomic DNA collected?
    """


@schema
class PostInductionCulture(dj.Manual):
    definition = """ # Plate contains 6 wells
    -> InductionCulture
    post_induction_plate_id: varchar(4)
    """


@schema
class PostInductionCultureWell(dj.Manual):
    definition = """ # Plate contains 6 wells
    -> PostInductionCulture
    post_induction_well_id: int
    """


@schema
class PostInductionCultureCondition(dj.Manual):
    definition = """
    -> PostInductionCulture
    post_induction_condition_date: date
    ---
    post_induction_step: enum('ipsc_replate', 'post_induction_start', 'media_change')
    media_change=null: bool
    density=null: int               # units of percentage
    discontinued=null: bool
    post_induction_condition_note='': varchar(256)
    """


@schema
class PostInductionCultureSupplement(dj.Manual):
    definition = """
    -> PostInductionCultureCondition
    supplement: enum('EGF+FGF', 'EGF', 'FGF')
    ---
    concentration: int 
    units: enum('micromolar', 'ng/mL')
    """


@schema
class PostInductionCultureMedia(dj.Manual):
    definition = """
    -> PostInductionCultureCondition
    media_name: varchar(32)
    ---
    percent_media_changed: int      # Percentage of the media used in the culture, 1-100
    manufacturer='': varchar(32)
    catalog_number='': varchar(32)
    media_note='': varchar(256)
    """


@schema
class PostInductionCultureSubstrate(dj.Manual):
    definition = """
    -> PostInductionCultureCondition
    substrate: varchar(32)          # matrigel
    """


@schema
class RosetteCulture(dj.Manual):
    definition = """
    -> PostInductionCulture
    plate_id: varchar(4)
    well_id: varchar(4)
    ---
    -> User
    single_rosette_date: date   # date for picking rosette
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
class RosetteCultureImage(dj.Manual):
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
    experiment_datetime: datetime    # Experiment start time
    ---
    -> [nullable] Experiment
    experiment_plan: varchar(64) # mrna lysate, oct, protein lysate, or matrigel embedding
    experiment_directory='':      varchar(256) # Path to the subject data directory
    """


@schema
class OrganoidCulture(dj.Manual):
    definition = """ # Organoids embedded in matrigel 10cm dish for up to 5 months
    -> lineage.Lineage
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
    -> Experiment
    experiment_datetime: datetime    # Experiment start time
    ---
    experiment_directory:      varchar(256) # Path to the subject data directory
    experiment_plan:     varchar(64) # ephys, tracing
    """
