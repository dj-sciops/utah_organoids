# Standard Operating Procedure for Utah Organoids DataJoint pipeline

## Overview

This document provides a step-by-step guide to accessing and using the **Utah Organoids DataJoint pipeline**. The pipeline supports **cerebral organoids characterization** and **electrophysiology (ephys) data analysis**.

### Pipeline Components

- **Organoid Generation Pipeline**: Manages metadata for organoid generation protocols, tracking the process from induced pluripotent stem cells (iPSCs) to single neural rosettes (SNRs), and mature organoids.

- **Array Ephys Pipeline**: Handles ephys data analysis, managing metadata and raw data related to probes and ephys recordings. It also includes preprocessing, spike sorting, curation, and quality metrics computations.

## Accessing the Utah Organoids DataJoint Pipeline

1. **Request access to a DataJoint account**:
     1. Request a new account at support@datajoint.com.
     2. Once approved, you will receive your **DataJoint credentials (username and password)** granting access to:
     - DataJoint platform
     - Organoids SciViz website
     - Database connections

## Standard Operating Procedure for the Organoids Generation Pipeline

2. **Enter metadata into the Organoids Generation Pipeline**: 
    1. Manually enter data through the forms on the SciViz website.
    2. Log into [Organoids SciViz](https://organoids.datajoint.com/) with your DataJoint credentials (username and password).
    3. Use the "Form" sections in each tab to enter details about your organoid generation protocol:
        - `User` page → if you are a new experimenter, create a new user
        - `Lineage` page → create new “Lineage” and submit; create new “Sequence” and submit
        - `Stem Cell` page → create new “Stem Cell”
        - `Induction` page → add new “Induction Culture” and “Induction Culture Condition”
        - `Post Induction` page → add new “Post Induction Culture” and “Post Induction Culture Condition”
        - `Isolated Rosette` page → add new “Isolated Rosette Culture” and “Isolated Rosette Culture Condition”
        - `Organoid` page → add new “Organoid Culture” and “Organoid Culture Condition”
        - `Experiment` page → add new experiments performed on a particular organoid
            - Include organoid ID, datetime, experimenter, condition, etc.
            - Provide the experiment data directory — the relative path to where the acquired data is stored.

**Note**: Clicking on read-only tables may cause the page to become unresponsive (white screen). This is a known issue currently being fixed. For now, please refresh and re-login.
## Standard Operating Procedure for the Array Ephys Pipeline

3. Follow these [instructions](#upload-data-from-your-local-machine-to-the-cloud) to upload the acquired data before proceeding.
4. Select an organoid experiment and define a time-window for ephys analysis (referred to as `EphysSession` in the pipeline)
    1. Log in to [works.datajoint.com](works.datajoint.com) → Navigate to `Notebook` tab
    2. Open [the CREATE_new_session.ipynb](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_session.ipynb) notebook to create a new `EphysSession`.
    3. Follow the instructions in the notebook:
        - For LFP analysis, set the `session_type` as `lfp` (details are provided in the notebook). This triggers automatic analysis.
        - For spike sorting analysis, set the `session_type` as `spike_sorting`, and create a `EphysSessionProbe` to store probe information, including the channel mapping (details are provided in the notebook). The `EphysSession` and `EphysSessionProbe` will trigger probe insertion detection automatically. For spike sorting, you will need to manually select the spike sorting algorithm and parameter set to run (see the next step).
5. Run spike sorting analysis
    1. Manually select a spike-sorting algorithm and parameter set (this is called to create a `ClusteringTask` in the pipeline):
        - Go to [works.datajoint.com](works.datajoint.com) → `Notebook` tab
        - Open [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_clustering_paramset.ipynb) to create a new spike sorting parameter set (clustering paramset) for an `EphysSession` and follow the instructions.
        - Open [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_clustering_task.ipynb) to select the spike sorting parameter set and the `EphysSession` (i.e., a `ClusteringTask` in the pipeline) and follow the instructions.
        - Spike sorting will run automatically after your selection.
        - Download spike sorting results to your local machine by following the [download instructions section](#download-spike-sorting-results-to-your-local-machine).
6. Explore LFP & spike sorting results 
    1. Go to [works.datajoint.com](works.datajoint.com) → `Notebook` tab
    2. Open and follow the instructions in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/EXPLORE_array_ephys.ipynb) to explore the ephys results in the pipeline.
    3. Then, open and follow the instructions in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/EXPLORE_quality_metrics.ipynb) to explore the quality metrics for sorted units.

### Upload Data from Your Local Machine to the Cloud

1. Ensure that the local folder you want to upload follows the [file structure guidelines here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/DATA_ORGANIZATION.md).
2. You need Axon credentials to upload raw data from you local machine to the cloud. If you don't have them yet:
    1. Request them from the DataJoint team.
    2. Once approved, you’ll be provided with Axon credentials (account_id, client_id, client_secret, issuer, bucket, role) to upload to the AWS S3 bucket.
3. Set up the following configurations on your local machine (if you haven't already):  
    1. Install the pipeline code on your computer. Follow the [installation instructions here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#installation-of-the-pipeline-codebase).  
    2. Set up your local machine with the axon configuration for cloud upload by following the steps in this guide: [Add cloud upload configuration](https://github.com/dj-sciops/utah_organoids/blob/main/docs/CLOUD_UPLOAD_CONFIGURATION_INSTRUCTIONS.md).  
4. Once the setup is complete, you can upload your local raw data by following the steps in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/CREATE_new_session_with_cloud_upload.ipynb). There are several ways to execute the notebook in your local machine, here are two options:
    1. Using the Jupyter Notebook Server. The notebook can be executed with `jupyter notebook` launched on your local machine.  
        - Open a terminal or command prompt.
        - Activate the `utah_organoids` environment with `conda activate utah_organoids`.
        - Ensure `Jupyter` is installed in the `utah_organoids` environment. If not, install it by running `conda install jupyter`.
        - Navigate to the `utah_organoids/notebooks` directory in the terminal.
        - Run `jupyter notebook` in the terminal which will open the Jupyter notebook web interface.
        - Click on the notebook there (`CREATE_new_session_with_cloud_upload.ipynb`) and follow the instructions to upload your data to the cloud.
        - Note: to execute each code cell sequentially, press `Shift + Enter` on your keyboard or click "Run". 
        - Close the browser tab and stop Jupyter with `Ctrl + C` in the terminal when you are done with the upload and notebook.
    2. Running in VS Code. The notebook can be executed in Visual Studio Code (VS Code) with the Python extension installed.
        - Install VS Code and the Python extension.
        - Open the `CREATE_new_session_with_cloud_upload.ipynb` notebook in VS Code.
        - Select the kernel for the notebook by clicking on the kernel name `utah_organoids` in the top right corner of the notebook.
        - Click on the "Run Cell" button in the top right corner of each code cell to execute the code.
        - Follow the instructions in the notebook to upload your data to the cloud.

### Download Spike Sorting Results to Your Local Machine

1. You need Axon credentials to download the spike sorting results from the cloud to your local machine. If you don't have them yet:
    1. Request them from the DataJoint team.
    2. Once approved, you’ll be provided with Axon credentials (account_id, client_id, client_secret, issuer, bucket, role) to download results from the AWS S3 bucket.
2. Set up the following configurations on your local machine (if you haven't already):  
    1. Install the pipeline code on your computer. Follow the [installation instructions here](https://github.com/dj-sciops/utah_organoids/blob/main/docs/INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#installation-of-the-pipeline-codebase).  
    2. Set up the axon configuration by following the steps in this guide: [Add cloud upload configuration](https://github.com/dj-sciops/utah_organoids/blob/main/docs/CLOUD_UPLOAD_CONFIGURATION_INSTRUCTIONS.md). 
3. Once the setup is complete, you can download the spike sorting results by following the steps in [this notebook](https://github.com/dj-sciops/utah_organoids/blob/main/notebooks/DOWNLOAD_spike_sorted_data.ipynb).There are several ways to execute the notebook in your local machine, here are two options:
    1. Using the Jupyter Notebook Server. The notebook can be executed with `jupyter notebook` launched on your local machine.  
        - Open a terminal or command prompt.
        - Activate the `utah_organoids` environment with `conda activate utah_organoids`.
        - Ensure `Jupyter` is installed in the `utah_organoids` environment. If not, install it by running `conda install jupyter`.
        - Navigate to the `utah_organoids/notebooks` directory in the terminal.
        - Run `jupyter notebook` in the terminal which will open the Jupyter notebook web interface.
        - Click on the notebook there (`DOWNLOAD_spike_sorted_data.ipynb`) and follow the instructions to download the results.
        - Note: to execute each code cell sequentially, press `Shift + Enter` on your keyboard or click "Run". 
        - Close the browser tab and stop Jupyter with `Ctrl + C` in the terminal when you are done with the download and notebook.
    2. Running in VS Code. The notebook can be executed in Visual Studio Code (VS Code) with the Python extension installed.
        - Install VS Code and the Python extension.
        - Open the `DOWNLOAD_spike_sorted_data.ipynb` notebook in VS Code.
        - Select the kernel for the notebook by clicking on the kernel name `utah_organoids` in the top right corner of the notebook.
        - Click on the "Run Cell" button in the top right corner of each code cell to execute the code.
        - Follow the instructions in the notebook to download results.


## Troubleshooting
For assistance, refer to the [Troubleshooting Guide](TROUBLESHOOTING.md), which provides solutions to common issues encountered during pipeline setup and execution. If you need further help, feel free to contact the DataJoint SciOps team.