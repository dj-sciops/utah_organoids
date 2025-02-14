# DataJoint Workflow for the Utah Organoids Project

This is the central codebase for the **DataJoint Workflow for the Utah Organoids Project**. The pipeline supports **cerebral organoids characterization** and **electrophysiology (ephys) data analysis**.

### Pipeline Components

- **Organoid Generation Pipeline**: Manages metadata for organoid generation protocols, tracking the process from induced pluripotent stem cells (iPSCs) to single neural rosettes (SNRs), and mature organoids.

  - `lineage`: Handles lineage and sequence metadata.
  - `culture`: Manages metadata for iPSCs, SNRs, and organoids, covering culture conditions, induction and post-induction details, media used, experiment timelines and directories, and drug concentrations.

![Culture Diagram](./images/culture_diagram.png)

![Experiment Workflow](./images/workflow_lineage_culture.svg)

- **Array Ephys Pipeline**: Handles ephys data analysis, managing metadata and raw data related to probes and ephys recordings. It also includes preprocessing, spike sorting, curation, and quality metrics computations.

  - `probe`: Manages the probes and metadata used for the electrophysiology recordings.
  - `ephys`: Manages the electrophysiology data and analysis results, including spike sorting and quality metrics.
    - `EphysRecording`: Represents raw electrophysiological recordings linked to specific probe insertions. `EphysRecordingFile`: Represents the raw data files associated with each recording.
    - `Preprocessing`: Applies preprocessing steps like filtering and artifact removal to raw data.
    - `Clustering`: Stores the spike sorting results.
    - `Curation`: Facilitates manual or automated curation of sorted spike data.
    - `QualityMetrics`: Calculates and stores quality metrics after the spike sorting.
    - `Unit`: Final output of curated, high-quality single-unit data.

![Array Ephys Workflow](./images/workflow_array_ephys.svg)

## Accessing the Organoids DataJoint Pipeline

1. **Request access to a DataJoint account**:
     1. Request a new account from your DataJoint support team.
     2. Once approved, you will receive your **DataJoint credentials (username and password)** granting access to:
     - DataJoint platform
     - Organoids SciViz website
     - Database connections

## Quick Start Guide

What are you aiming to achieve with the pipeline?

| User Type           | Description                                                                                                                                                    | Relevant Notebooks         |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Guest**           | Explore the data without installing anything. [Learn more](./docs/README.md#getting-started-as-a-guest).                                                       | `EXPLORE`                  |
| **Experimenter**    | Run the pipeline for your new experiment efficiently without diving into the code, including **instructions on uploading data to the cloud**.[Learn more](./docs/README.md#getting-started-as-a-experimenter). | `EXPLORE`                  |
| **Power-User**      | Gain deeper insights by running specific pipeline computations on the cloud or locally, and **understand how the data is processed**. [Learn more](./docs/README.md#getting-started-as-a-power-user).                   | `CREATE`, `RUN`, `EXPLORE` |
| **Developer/Admin** | Maintain and enhance the pipeline codebase, implement new features, and contribute actively to the project. [Learn more](./docs/README.md#getting-started-as-a-developer-or-admin).                                | `CREATE`, `RUN`, `EXPLORE` | 

## Summary on Getting Started with Works App

- _Goal_: **Explore the current pipeline architecture and results** without running new data or new analyses, and with no installation required.

- _Steps_:
  1. Request access to a DataJoint account:
     1. Request a new account from your DataJoint support team.
     2. Once approved, you will receive your DataJoint credentials (username and password) to access:
     - DataJoint platform
     - Organoids SciViz website
     - Database connection  
  2. Log onto the [DataJoint platform](https://works.datajoint.com/) (no installation required).
  3. In the `Notebooks` tab, run the notebooks located under `utah_organoids/notebooks/`.
        - `EXPLORE` notebooks: Explore the current pipeline architecture and results. Please run the `EXPLORE_pipeline_architecture.ipynb` to examine the main schemas of the pipeline.
        - `CREATE` notebooks allow creating new experiments, parameter sets, and sessions. For example, `CREATE_new_clustering_paramset.ipynb` to create a new clustering parameter set for `spykingcircus2`.

The standard operating procedures for the Utah Organoids DataJoint pipeline is [here](PROCEDURE.md).

## SciViz website

Data viewer for the Utah Organoids DataJoint pipeline. Please use the entry forms provided on the website to manually input relevant data entries.

<https://organoids.datajoint.com/>

## Citations

- If your work uses [SpikeInterface within the pipeline](https://github.com/datajoint/element-array-ephys/tree/datajoint-spikeinterface), cite the respective manuscript. For details, visit [here](https://spikeinterface.readthedocs.io/en/latest/references.html).
- For other tools integrated within the pipeline, cite their respective manuscripts and Research Resource Identifiers (RRIDs).
- For work utilizing DataJoint Python and/or Elements, cite the respective manuscripts and RRIDs. For details, visit [here](https://datajoint.com/docs/about/citation/).

DataJoint promotes integration and interoperability across neuroscience ecosystems, encouraging transparency and collaboration in research.
