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
    induction_culture_date: date
    induction_culture_plate: int unsigned
    ---
    induction_culture_wells: varchar(8)    # Ranges of wells occupied (e.g. 1-3)
    """


@schema
class InductionCultureCondition(dj.Manual):
    definition = """
    -> InductionCulture
    induction_condition_datetime: datetime
    ---
    induction_step: enum('ipsc_replate', 'induction_start', 'media_change')
    media_change=null: bool
    density=null: int unsigned          # units of percentage
    discontinued=null: bool
    induction_condition_note='': varchar(256)
    """


@schema
class InductionCultureSupplement(dj.Manual):
    definition = """
    -> InductionCultureCondition
    supplement: enum('Dorsomorphin', 'SB431542')
    ---
    concentration: int unsigned
    units: enum('micromolar', 'ng/mL')
    """


@schema
class InductionCultureMedia(dj.Manual):
    definition = """
    -> InductionCultureCondition
    media_name: varchar(32)
    ---
    percent_media_changed: int unsigned     # Percentage of the media used in the culture, 1-100
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
    post_induction_culture_date: date
    post_induction_culture_plate: int unsigned
    ---
    post_induction_culture_wells: varchar(8)    # Ranges of wells occupied (e.g. 1-3)
    """


@schema
class PostInductionCultureCondition(dj.Manual):
    definition = """
    -> PostInductionCulture
    post_induction_condition_datetime: datetime
    ---
    post_induction_step: enum('ipsc_replate', 'post_induction_start', 'media_change')
    media_change=null: bool
    density=null: int unsigned               # units of percentage
    discontinued=null: bool
    post_induction_condition_note='': varchar(256)
    """


@schema
class IsolatedRosetteCulture(dj.Manual):
    definition = """ # Plate contains 96 wells (12 columns, 8 rows)
    -> PostInductionCulture
    isolated_rosette_culture_date: date       # Date for isolating the rosette
    isolated_rosette_culture_plate: int unsigned
    ---
    isolated_rosette_culture_wells: varchar(8)        # Ranges of wells occupied (e.g. A1-B2)
    amplification_date=null: date    # Date of EGF+FGF treatment
    """


@schema
class RosetteCultureWell(dj.Manual):
    definition = """ # Plate contains 96 wells (12 columns, 8 rows)
    -> RosetteCulture
    rosette_well_id: varchar(4)
    """


@schema
class RosetteCultureCondition(dj.Manual):
    definition = """
    -> RosetteCulture
    rosette_condition_date: date
    ---
    rosette_relative_day=null: int unsigned # relative to date for picking rosette
    rosette_condition_note='': varchar(256)
    """


@schema
class OrganoidCulture(dj.Manual):
    definition = """ # Each organoid is embedded in a matrigel droplet, and multiple organoids are embedded in a 10cm dish for up to 5 months
    -> IsolatedRosetteCulture
    organoid_culture_date: date
    organoid_culture_plate: int unsigned
    ---
    isolated_rosette_culture_wells: varchar(8)    # Wells from the 96-well plate used to embed organoids
    """


@schema
class RosetteCultureMedia(dj.Manual):
    definition = """
    -> RosetteCultureCondition
    media_name: varchar(32)
    ---
    media_amount: int unsigned        # Percentage of the media used in the culture, 1-100
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
    organoid_id: varchar(4)               # e.g. O17
    experiment_datetime: datetime         # Experiment start date and time
    ---
    -> [nullable] User
    -> [nullable] IsolatedRosetteCulture
    -> [nullable] OrganoidCulture
    experiment_plan: varchar(64)          # e.g. mrna lysate, oct, protein lysate, or matrigel embedding, ephys, tracing
    experiment_directory='': varchar(256) # Path to the subject data directory
    """
