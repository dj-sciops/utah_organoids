# Standard Operating Procedure for Utah Organoids DataJoint pipeline

## Overview

This document provides a step-by-step guide to access and use the **Utah Organoids DataJoint pipeline**. The pipeline is designed to manage and analyze data from the Utah lab, focusing on cerebral organoids characterization and ephys data analysis.

- **Organoid Generation Pipeline**: This pipeline manages the protocols metadata for generating organoids, which includes inducing pluripotent stem cells (iPSCs) to form single neural rosettes (SNRs), followed by the development of these rosettes into organoids. 

- **Array Ephys Pipeline**: This pipeline handles array ephys data analysis, managing data and metadata related to probes and ephys recordings. It stores raw files and includes computations for preprocessing, spike sorting, curation, and quality metrics.

## Accessing the Utah Organoids DataJoint Pipeline

1. Request access and account at [DataJoint Works account](https://accounts.datajoint.com/).
     a. Contact DataJoint team for access & account
     b. Once approved, you’ll be provided with credentials

## Standard Operating Procedure for the Organoids Generation Pipeline

2. Enter metadata into the **Organoids Generation Pipeline** steps. Please manually input relevant data using the provided entry forms on the website, as follows:
     a. Visit the [Organoids SciViz website](https://organoids.datajoint.com/) and log in with your DataJoint credentials (username and password)
     b. Follow a series of data-entry steps in the "Form" sections of each tab to specify full details about your organoids generation protocol:
        i. `User` page → if you are a new experimenter, create new user
        ii. `Linage` page → create new “Linage” and submit; create new “Sequence” and submit
        iii. `Stem Cell` page → create new “Stem Cell”
        iv. `Induction` page → add new “Induction Culture” and “Induction Culture Condition”
        v. `Post Induction` page → add new “Post Induction Culture” and “Post Induction Culture Condition”
        vi. `Isolated Rossette` page → add new “Isolated Rossette Culture” and “Isolated Rossette Culture Condition”
        vii. `Organoid` page → add new “Organoid Culture” and “Organoid Culture Condition”
        viii. `Experiment` page → add new experiments performed on a particular organoid
            1. Include organoids ID, datetime, experimenter, condition, etc.
            2. Provide the experiment data directory - the relative path to where the acquired data is stored for this experiment.
Note: The "Table" sections in each tab display the data entries in a tabular format. These sections are not clickable, so if you click on them, the website may turn white, requiring you to log back in.

## Standard Operating Procedure for the Array Ephys Pipeline
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