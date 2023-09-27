import datajoint as dj

from . import lineage

if "custom" not in dj.config:
    dj.config["custom"] = {}

DB_PREFIX = dj.config["custom"].get("database.prefix", "")

schema = dj.schema(DB_PREFIX + "culture")


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
    induction_culture_note='': varchar(256)
    """


@schema
class InductionCultureCondition(dj.Manual):
    definition = """
    -> InductionCulture
    induction_condition_datetime: datetime
    ---
    induction_step: enum('ipsc_replate', 'induction_start', 'media_change')
    -> [nullable] User
    density=null: int unsigned # Units of percentage
    quality='': varchar(32) # e.g. cell detach, cell death, color change, morphology change
    supplement=null: enum('','Dorsomorphin 10ng/mL + SB431542 4ng/mL', 'Dorsomorphin 10ng/mL', 'SB431542 4ng/mL') # Supplement, concentration, and units
    media=null: enum('','N2B27')
    media_percent_changed=null: int unsigned # Percent of the media changed, 1-100
    substrate=null: enum('','matrigel')
    induction_condition_image_directory='': varchar(256) # Images stored with "id_datetime" naming convention.
    genomic_dna=null: bool # Was genomic DNA collected?
    induction_condition_note='': varchar(256)
    discontinued=null: bool
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
    -> [nullable] User
    density=null: int unsigned               # units of percentage
    quality='': varchar(32) # e.g. cell detach, cell death, color change, morphology change
    supplement=null: enum('', 'EGF+FGF 10 ng/mL', 'EGF', 'FGF') # Supplement, concentration, and units
    media=null: enum('', 'N2B27')
    media_percent_changed=null: int unsigned  # Percent of the media changed, 1-100
    substrate=null: enum('', 'matrigel')
    post_induction_condition_image_directory='': varchar(256) # Images stored with "id_datetime" naming convention.
    post_induction_condition_note='': varchar(256)
    discontinued=null: bool
    """


@schema
class IsolatedRosetteCulture(dj.Manual):
    definition = """ # Plate contains 96 wells (12 columns, 8 rows)
    -> PostInductionCulture
    isolated_rosette_culture_date: date         # Date for isolating the rosette
    isolated_rosette_culture_plate: int unsigned
    ---
    isolated_rosette_culture_wells: varchar(8)  # Ranges of wells occupied (e.g. A1-B2)
    size=null: int unsigned   # Units of millimeters
    number_of_lumen=null: int unsigned
    isolated_rosette_culture_note='': varchar(256)
    """


@schema
class IsolatedRosetteCultureCondition(dj.Manual):
    definition = """
    -> IsolatedRosetteCulture
    isolated_rosette_condition_datetime: datetime
    ---
    -> [nullable] User
    quality='': varchar(32) # e.g. cell detach, cell death, color change, morphology change
    supplement=null: enum('', 'EGF+FGF 10 ng/mL', 'EGF', 'FGF') # Supplement, concentration, and units
    media=null: enum('', 'N2B27')
    media_percent_changed=null: int unsigned  # Percent of the media changed, 1-100
    substrate=null: enum('', 'matrigel')
    isolated_rosette_condition_image_directory='': varchar(256) # Images stored with "id_datetime" naming convention.
    isolated_rosette_condition_note='': varchar(256)
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
class OrganoidCultureCondition(dj.Manual):
    definition = """
    -> OrganoidCulture
    organoid_condition_datetime: datetime
    ---
    -> [nullable] User
    quality='': varchar(32) # e.g. cell detach, cell death, color change, morphology change
    supplement='': varchar(32)
    media='': varchar(32)
    media_percent_changed=null: int unsigned # Percent of the media changed, 1-100
    substrate=null: enum('', 'matrigel')
    organoid_condition_image_directory='': varchar(256) # Images stored with "id_datetime" naming convention.
    organoid_condition_note='': varchar(256)
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
    """


@schema
class ExperimentDirectory(dj.Manual):
    definition = """
    -> Experiment
    ---
    experiment_directory: varchar(256)   # Path to the subject data directory for long term recordings
    """
