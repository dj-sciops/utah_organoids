# DataJoint Workflow for Utah Lab

This is the central codebase for the **DataJoint Workflow for Utah Lab**. The pipelines are designed to manage and analyze data from the Utah lab, focusing on cerebral organoids characterization and electrophysiology data analysis.

The automated pipeline consists of several schemas and tables, covering multiple data modalities and/or DataJoint Elements.

- **Organoids generation pipeline**: The protocol for organoid generation includes inducing pluripotent stem cells (iPSCs) to form single neural rosettes (SNRs), which are then developed into organoids. 

![Culture Diagram](./images/culture_diagram.png)

This pipeline manages data from the organoid generation process, including iPSCs, SNRs, and organoids. It includes the following schemas:
  - `lineage`: Handles lineage and sequence metadata.
  - `culture`: Manages metadata for iPSCs, SNRs, and organoids, covering culture conditions, induction and post-induction details, media used, experiment timelines and directories, and drug concentrations.

![Experiment Workflow](./images/workflow_lineage_culture.svg)

- **Array Ephys pipeline**: This pipeline for array electrophysiology data analysis includes the following main steps:
  - `probe`: Manages the probes and metadata used for the electrophysiology recordings.
  - `ephys`: Manages the electrophysiology data and analysis results, including spike sorting and quality metrics.
    - `EphysRecording`: Represents raw electrophysiological recordings linked to specific probe insertions. `EphysRecordingFile`: Represents the raw data files associated with each recording.
    - `Preprocessing`: Applies preprocessing steps like filtering and artifact removal to raw data.
    - `Clustering`: Stores the spike sorting results.
    - `Curation`: Facilitates manual or automated curation of sorted spike data.
    - `QualityMetrics`: Calculates and stores quality metrics after the spike sorting.
    - `Unit`: Final output of curated, high-quality single-unit data.

![Array Ephys Workflow](./images/workflow_array_ephys.svg)

- For more details, you can explore the pipeline architecture and data in the `EXPLORE` notebooks as Guest following the [Quick Start Guide](#quick-start-guide) below.

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
     1. Send an email to support@datajoint.com requesting a new account.
     2. Once approved, you will receive your DataJoint credentials (username and password) to access:
     - DataJoint platform
     - Organoids SciViz website
     - Database connection  
  2. Log in to the [DataJoint platform](https://works.datajoint.com/) (no installation required).
  3. In the `Notebooks` tab, run the notebooks located under `utah_organoids/notebooks/`.
        - `EXPLORE` notebooks: Explore the current pipeline architecture and results. Please run the `EXPLORE_pipeline_architecture.ipynb` to examine the main schemas that compound the pipeline architecture for this project.
        - `CREATE` notebooks: Create new data entries, such as new experiments, parameter sets, or sessions. For example, you can run the `CREATE_new_clustering_paramset.ipynb` notebook to create and insert a new clustering parameter set entry to run `spykingcircus2`.

You can find the standard operating procedures for the Utah Organoids DataJoint pipeline [here](PROCEDURE.md). Please refer to this document for detailed instructions on how to use the pipeline.

## SciViz website

Data viewer for the Utah Organoids DataJoint pipeline. Please use the entry forms provided on the website to manually input relevant data entries.

<https://organoids.datajoint.com/>

## Citations

- If your work uses [SpikeInterface within the pipeline](https://github.com/datajoint/element-array-ephys/tree/datajoint-spikeinterface), cite the respective manuscript. For details, visit [here](https://spikeinterface.readthedocs.io/en/latest/references.html).
- For other tools integrated within the pipeline, cite their respective manuscripts and Research Resource Identifiers (RRIDs).
- For work utilizing DataJoint Python and/or Elements, cite the respective manuscripts and RRIDs. For details, visit [here](https://datajoint.com/docs/about/citation/).

DataJoint promotes integration and interoperability across neuroscience ecosystems, encouraging transparency and collaboration in research.
