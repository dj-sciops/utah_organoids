# Utah Organoids DataJoint Pipelines

The **Utah Organoids DataJoint pipelines** facilitate **cerebral organoid characterization** and **electrophysiology (ephys) data analysis**.

### Pipeline Components

- **Organoid Generation Pipeline**: Manages metadata for organoid generation protocols, tracking the process from induced pluripotent stem cells (iPSCs) to single neural rosettes (SNRs) to mature organoids.

- **Array Ephys Pipeline**: Manages and analyzes ephys recordings, including spike sorting and quality metrics.

## Accessing the Pipelines

1. **Request Access**: Contact the DataJoint support team for an account.
2. **Log in**: Use your DataJoint credentials to access:
     - works.datajoint.com (run notebooks & manage computations)
     - Organoids SciViz (enter experimental metadata)
     - Database connections (access data through the pipeline)

## Exploring the Pipelines

  1. Log into [works.datajoint.com](https://works.datajoint.com)  and navigate to the `Notebook` tab.
  2. Run [EXPLORE_pipeline_architecture.ipynb](./notebooks/EXPLORE_pipeline_architecture.ipynb) to visualize the data pipeline structure, including key schemas, tables, and their relationships.

## Organoid Generation Pipeline

### **Metadata Entry**

  1. Log into [Organoids SciViz](https://organoids.datajoint.com/) with your DataJoint credentials (username and password).
  2. Enter data in the corresponding sections:
      - `User` page → if you are a new experimenter, register a new experimenter.
      - `Lineage` page → create new “Lineage” and “Sequence” and submit.
      - `Stem Cell` page → register new “Stem Cell” data.
      - `Induction` page → add new “Induction Culture” and “Induction Culture Condition”
      - `Post Induction` page → add new “Post Induction Culture” and “Post Induction Culture Condition”
      - `Isolated Rosette` page → add new “Isolated Rosette Culture” and “Isolated Rosette Culture Condition”
      - `Organoid` page → add new “Organoid Culture” and “Organoid Culture Condition”
      - `Experiment` page → log new experiments performed on a particular organoid
          - Include metadata: organoid ID, datetime, experimenter, condition, etc.
          - Provide the experiment data directory — the relative path to where the acquired data is stored.

## Array Ephys Pipeline

### **Upload Data to the Cloud**

  1. Ensure data follows the [file structure guidelines](./docs/installation_and_configuration/DATA_ORGANIZATION.md).
  2. Request Axon credentials from the DataJoint support team.
  3. Set up your local machine (if you haven't already):
      1. [Install the pipeline code](./docs/installation_and_configuration/INSTALLATION_AND_CONFIGURATION.md).  
      2. Configure axon settings ([Cloud upload configuration](./docs/installation_and_configuration/CLOUD_UPLOAD_CONFIGURATION.md)).  
  4. Upload data via the [cloud upload notebook](./notebooks/UPLOAD_session_data_to_cloud.ipynb) using either:
      1. Jupyter Notebook Server:
          - Open a terminal or command prompt.
          - Activate the `utah_organoids` environment with `conda activate utah_organoids`.
          - Ensure `Jupyter` is installed in the `utah_organoids` environment. If not, install it by running `conda install jupyter`.
          - Navigate to the `utah_organoids/notebooks` directory in the terminal.
          - Run `jupyter notebook` in the terminal which will open the Jupyter notebook web interface.
          - Click on the notebook there (`UPLOAD_session_data_to_cloud.ipynb`) and follow the instructions to upload your data to the cloud.
          - Note: to execute each code cell sequentially, press `Shift + Enter` on your keyboard or click "Run".
          - Close the browser tab and stop Jupyter with `Ctrl + C` in the terminal when you are done with the upload and notebook.
      2. Visual Studio Code (VS Code):
          - Install VS Code and the Python extension.
          - Select the kernel for the notebook by clicking on the kernel name `utah_organoids` in the top right corner of the notebook.
          - Open the `CREATE_new_session_with_cloud_upload.ipynb` notebook in VS Code.
          - Click on the "Run Cell" button in the top right corner of each code cell to execute the code.
          - Follow the instructions in the notebook to upload your data to the cloud.

### **Analyzing Multi-Unit Activity (MUA) in Raw Traces**  

1. Navigate to [works.datajoint.com](https://works.datajoint.com) and open the `Dashboard` tab.  
2. Click on `Plots` > `MUA Trace Plots`, then select a data entry to explore the MUA results. The interactive plot allows you to zoom in and out of the raw traces and examine detected peaks.  
3. (Optional) For a more detailed analysis, go to the `Notebook` tab on [works.datajoint.com](https://works.datajoint.com) and run the [EXPLORE_MUA_analysis.ipynb](./notebooks/EXPLORE_MUA_analysis.ipynb) notebook to inspect the `MUA` schema in depth.

### **Define an `EphysSession`** (i.e. a time-window for ephys analysis)

  1. Log into [works.datajoint.com](https://works.datajoint.com)  and navigate to the `Notebook` tab.
  2. Open and execute [CREATE_new_session.ipynb](./notebooks/CREATE_new_session.ipynb).
  3. Define a time window for analysis:
      - **For Spike Sorting Analysis**: Set `session_type` to `spike_sorting`, and create an `EphysSessionProbe` to store probe information, including the channel mapping. This triggers probe insertion detection automatically. For spike sorting, you will need to manually select the spike sorting algorithm and parameter set to run in the next step.

### **Run Spike Sorting Analysis**

  1. Create a `ClusteringTask` by selecting a spike-sorting algorithm and parameter set:
      - Go to [works.datajoint.com](works.datajoint.com) → `Notebook` tab
      - Run [CREATE_new_clustering_paramset.ipynb](./notebooks/CREATE_new_clustering_paramset.ipynb) to configure a new parameter set.
      - Assign parameters to an `EphysSession` using [CREATE_new_clustering_task.ipynb](./notebooks/CREATE_new_clustering_task.ipynb).
      - The pipeline will automatically run the spike sorting process.
      - Follow the [download spike sorting results](#download-spike-sorting-results-to-your-local-machine) to retrieve results.

### **Explore Spike Sorting Results**

  1. Go to [works.datajoint.com](https://works.datajoint.com) → `Notebook` tab
  2. Open [EXPLORE_spike_sorting.ipynb](./notebooks/EXPLORE_spike_sorting.ipynb) to inspect processed ephys data.

### **Download Spike Sorting Results to Your Local Machine**

  1. Request Axon credentials from the DataJoint support team.
  2. Set up your local machine (if you haven't already):
      1. [Install the pipeline code](./docs/installation_and_configuration/INSTALLATION_AND_CONFIGURATION.md#installation-of-the-pipeline-codebase).  
      2. Configure axon settings ([Cloud upload configuration](./docs/CLOUD_UPLOAD_CONFIGURATION.md)).  
  3. Download spike sorting results via the [DOWNLOAD_spike_sorted_data.ipynb](./notebooks/DOWNLOAD_spike_sorted_data.ipynb) using either:
      1. Jupyter Notebook Server:
          - Open a terminal or command prompt.
          - Activate the `utah_organoids` environment with `conda activate utah_organoids`.
          - Ensure `Jupyter` is installed in the `utah_organoids` environment. If not, install it by running `conda install jupyter`.
          - Navigate to the `utah_organoids/notebooks` directory in the terminal.
          - Run `jupyter notebook` in the terminal which will open the Jupyter notebook web interface.
          - Click on the notebook there (`DOWNLOAD_spike_sorted_data.ipynb`) and follow the instructions to download results.
          - Note: to execute each code cell sequentially, press `Shift + Enter` on your keyboard or click "Run".
          - Close the browser tab and stop Jupyter with `Ctrl + C` in the terminal when you are done with the upload and notebook.
      2. Visual Studio Code (VS Code):
          - Install VS Code and the Python extension.
          - Select the kernel for the notebook by clicking on the kernel name `utah_organoids` in the top right corner of the notebook.
          - Open the `DOWNLOAD_spike_sorted_data.ipynb` notebook in VS Code.
          - Click on the "Run Cell" button in the top right corner of each code cell to execute the code.
          - Follow the instructions in the notebook to download spike sorting results.

## Troubleshooting

For help, refer to the [Documentation](./docs/README.md), [Troubleshooting Guide](./docs/troubleshooting/TROUBLESHOOTING.md), or contact the DataJoint support team.

## Citation Policy

If your work uses DataJoint Python, DataJoint Elements, or any integrated tools within the pipeline, please cite the respective manuscripts and Research Resource Identifiers (RRIDs).

### DataJoint Python and MATLAB

Yatsenko D, Reimer J, Ecker AS, Walker EY, Sinz F, Berens P, Hoenselaar A, Cotton RJ, Siapas AS, Tolias AS.  
*DataJoint: managing big scientific data using MATLAB or Python.* bioRxiv. 2015 Jan 1:031658.  
[DOI: 10.1101/031658](https://doi.org/10.1101/031658)  
*Resource Identification (RRID):* [SCR_014543](https://scicrunch.org/resolver/SCR_014543)

### DataJoint Relational Model

Yatsenko D, Walker EY, Tolias AS.  
*DataJoint: a simpler relational data model.* arXiv:1807.11104. 2018 Jul 29.  
[DOI: 10.48550/arXiv.1807.11104](https://doi.org/10.48550/arXiv.1807.11104)  
*Resource Identification (RRID):* [SCR_014543](https://scicrunch.org/resolver/SCR_014543)

### DataJoint Elements

Yatsenko D, Nguyen T, Shen S, Gunalan K, Turner CA, Guzman R, Sasaki M, Sitonic D, Reimer J, Walker EY, Tolias AS.  
*DataJoint Elements: Data Workflows for Neurophysiology.* bioRxiv. 2021 Jan 1.  
[DOI: 10.1101/2021.03.30.437358](https://doi.org/10.1101/2021.03.30.437358)  
*Resource Identification (RRID):* [SCR_021894](https://scicrunch.org/resolver/SCR_021894)

### Citing Other Integrated Tools

- If your work uses **SpikeInterface**, please [cite the respective manuscript](https://spikeinterface.readthedocs.io/en/latest/references.html).  
- For other integrated tools within the pipeline, cite their respective **manuscripts** and **RRIDs**.
