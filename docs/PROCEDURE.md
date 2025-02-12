# Standard Operating Procedure for Utah Organoids DataJoint pipeline

## Overview

This document provides a step-by-step guide for accessing and using the **Utah Organoids DataJoint pipeline**. The pipeline is designed to manage and analyze data from the Utah lab, focusing on cerebral organoids characterization and electrophysiology (ephys) data analysis.

- **Organoid Generation Pipeline**: This pipeline manages metadata for organoid generation protocols, including inducing pluripotent stem cells (iPSCs) to form single neural rosettes (SNRs), which then develop into organoids.

- **Array Ephys Pipeline**: This pipeline handles the analysis of array ephys data, managing metadata and raw data related to probes and ephys recordings. It also includes preprocessing, spike sorting, curation, and quality metrics computations.

## Accessing the Utah Organoids DataJoint Pipeline

1. Request access to a **DataJoint Works** account:
     1. Contact a member of the DataJoint SciOps team (milagros@datajoint.com) to request a new account.
     2. Once approved, you will receive your **DataJoint credentials (username and password)** granting access to the DataJoint Works account, the Organoids SciViz website, and local database connections. 

## Standard Operating Procedure for the Organoids Generation Pipeline

2. Enter metadata into the **Organoids Generation Pipeline**. Please manually input relevant data using the provided entry forms on the website as follows:
     1. Visit the [Organoids SciViz website](https://organoids.datajoint.com/) and log in with your DataJoint credentials (username and password)
     2. Follow the data-entry steps in the "Form" sections of each tab to specify the details of your organoid generation protocol:
        - `User` page → if you are a new experimenter, create a new user
        - `Linage` page → create new “Linage” and submit; create new “Sequence” and submit
        - `Stem Cell` page → create new “Stem Cell”
        - `Induction` page → add new “Induction Culture” and “Induction Culture Condition”
        - `Post Induction` page → add new “Post Induction Culture” and “Post Induction Culture Condition”
        - `Isolated Rossette` page → add new “Isolated Rossette Culture” and “Isolated Rossette Culture Condition”
        - `Organoid` page → add new “Organoid Culture” and “Organoid Culture Condition”
        - `Experiment` page → add new experiments performed on a particular organoid
            - Include organoids ID, datetime, experimenter, condition, etc.
            - Provide the experiment data directory — the relative path to where the acquired data is stored.

*Note*: The "Table" sections in each tab display the data entries in a tabular format. These sections are not clickable. If you click on them, the website may turn white, requiring you to log back in.

## Standard Operating Procedure for the Array Ephys Pipeline

3. Select an organoid experiment and define a time-window for ephys analysis (referred to as `EphysSession` in the pipeline)
    1. Go to `works.datajoint.com` → `Notebook` tab
    2. Open [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_session.ipynb)  to create a new `EphysSession` and follow the instructions. Note that:
        - For LFP analysis, define the `session_type` as `lfp` (details are provided in the notebook). The `EphysSession` for LFP analysis will trigger the analysis automatically after creation.
        - For spike sorting analysis, define the `session_type` as `spike_sorting`, and also create a `EphysSessionProbe` to store probe information, including the channel mapping (details are provided in the notebook). The `EphysSession` and `EphysSessionProbe` will trigger probe insertion detection automatically. For spike sorting, you will need to manually select the spike sorting algorithm and parameter set to run (see the next step).
4. Ephys spike sorting analysis
    1. The user must manually select which spike-sorting algorithm and parameter set to run (this is called to create a `ClusteringTask` in the pipeline):
        - Go to `works.datajoint.com` → `Notebook` tab
        - Open [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_clustering_paramset.ipynb) to create a new spike sorting parameter set (clustering paramset) for an `EphysSession` and follow the instructions.
        - Open [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_clustering_task.ipynb) to select the spike sorting parameter set and the `EphysSession` (i.e., a `ClusteringTask` in the pipeline) and follow the instructions.
        - Spike sorting will trigger automatically after your selection.
5. Explore LFP/ spike sorting results 
    1. Go to `works.datajoint.com` → `Notebook` tab
    2. Open and follow the instructions in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/EXPLORE_array_ephys.ipynb) to explore the ephys results in the pipeline.
    3. Then, open and follow the instructions in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/EXPLORE_quality_metrics.ipynb) to explore the quality metrics for sorted units.

### Upload Data from your Local Machine to the Cloud
1. Ensure that the local folder you want to upload follows the [file structure guidelines here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/DATA_ORGANIZATION.md).
2. You need Axon credentials to upload raw data from you local machine to the cloud. If you don't have them yet:
    1. Request them from the DataJoint team.
    2. Once approved, you’ll be provided with Axon credentials (account_id, client_id, client_secret, issuer, bucket, role) to upload to the AWS S3 bucket.
3. Set up the following configurations on your local machine (if you haven't already):  
    1. Install the pipeline code on your computer. Follow the [installation instructions here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#installation-of-the-pipeline-codebase).  
    2. Set up the axon configuration by following the steps in this guide: [Add cloud upload configuration](https://github.com/dj-sciops/utah_organoids/blob/main/docs/CLOUD_UPLOAD_CONFIGURATION_INSTRUCTIONS.md).  
4. Once the setup is complete, you can upload your local raw data by following the steps in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_session_with_cloud_upload.ipynb)

### Download Data from the Cloud to your Local Machine
1. You need Axon credentials to download the spike sorting results from the cloud to your local machine. If you don't have them yet:
    1. Request them from the DataJoint team.
    2. Once approved, you’ll be provided with Axon credentials (account_id, client_id, client_secret, issuer, bucket, role) to download results from the AWS S3 bucket.
2. Set up the following configurations on your local machine (if you haven't already):  
    1. Install the pipeline code on your computer. Follow the [installation instructions here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#installation-of-the-pipeline-codebase).  
    2. Set up the axon configuration by following the steps in this guide: [Add cloud upload configuration](https://github.com/dj-sciops/utah_organoids/blob/main/docs/CLOUD_UPLOAD_CONFIGURATION_INSTRUCTIONS.md). 
3. Once the setup is complete, you can download the spike sorting results by following the steps in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/DOWNLOAD_spike_sorted_data.ipynb).