# Standard Operating Procedure for Utah Organoids data pipeline

## Overview

This document provides a step-by-step guide to access and use the **Utah Organoids DataJoint pipeline**. The pipeline is designed to manage and analyze data from the Utah lab, focusing on cerebral organoids characterization and electrophysiology data analysis.

- **Organoid Generation Pipeline**: This pipeline manages the protocols for generating organoids, which includes inducing pluripotent stem cells (iPSCs) to form single neural rosettes (SNRs), followed by the development of these rosettes into organoids.

- **Array Ephys Pipeline**: This pipeline handles array electrophysiology data analysis, managing data and metadata related to probes and ephys recordings. It stores raw files and includes computations for preprocessing, spike sorting, curation, and quality metrics.

## Procedure 

1. Request access and account at [DataJoint Works account](https://accounts.datajoint.com/).
     a. Contact DataJoint team for access & account
     b. Once approved, you’ll be provided with credentials

2. Enter metadata into the **Organoids Generation pipeline** by using the Data viewer for the Utah Organoids DataJoint pipeline. Please use the entry forms provided on the website to manually input relevant data entries.
     a. Go to the [SciViz website](https://organoids.datajoint.com/) and log in. 
     b. Follow a series of data-entry steps to specify full details about your organoids generation protocol
        i. `User` page → if you are a new experimenter, create new user
        ii. `Linage` page → create new “Linage” and “Sequence” 
        iii. `Stem Cell` page → create new “Stem Cell”
        iv. `Induction` page → add new “Induction Culture” and “Induction Culture Condition”
        v. `Post Induction` page → add new “Post Induction Culture” and “Post Induction Culture Condition”
        vi. `Isolated Rossette` page → add new “Isolated Rossette Culture” and “Isolated Rossette Culture Condition”
        vii. `Organoid` page → add new “Organoid Culture” and “Organoid Culture Condition”
        viii. `Experiment` page → add new experiments performed on a particular organoid
            1. organoids ID, datetime, experimenter, condition, etc.
            2. experiment data directory - relative path to where the acquired data is stored for this experiment

3. Data analysis in the **Array Ephys Pipeline** 
    a. Select an organoid experiment and define a time-window for ephys analysis (this is called `EphysSession` in the pipeline)
        i. Go to `works.datajoint.com` → `Notebook` tab
        ii. Follow the instruction/procedure in this notebook here <link>
    b. Ephys LFP analysis
        i. The LFP analysis will trigger automatically
        ii. See here <link> for further details on the analysis
        iii. See here <link> for how to work with the LFP analysis results
    c. Ephys spike sorting analysis
        i. User must manually select which spike-sorting algorithm and parameter set to run
            1. Go to `works.datajoint.com` → `Notebook` tab
            2. Follow the instruction/procedure in this notebook here <link> - to select which “Ephys Session” and which spike sorting parameter set to use
            3. Spike sorting will trigger automatically after your selection
        ii. see here <link> for further details on the spike sorting analysis
        iii. see here <link> for how to work with the LFP analysis results
        iv. see here <link> for how to download the spike sorting results to your local computer