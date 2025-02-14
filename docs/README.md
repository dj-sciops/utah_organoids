# Start Guide

What are you aiming to achieve with the pipeline?

| User Type           | Description                                                                                                                                   | Relevant Notebooks         |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Guest**           | Explore the data without installing anything. [Guideline](#getting-started-as-a-guest).                                                       | `EXPLORE`                  |
| **Experimenter**    | Quickly run the pipeline with your new experiment without spending time inspecting the code. [Guideline](#getting-started-as-a-experimenter). | `EXPLORE`                  |
| **Power-User**      | Delve deeper and run specific pipeline computations on the cloud or locally. [Guideline](#getting-started-as-a-power-user).                   | `CREATE`, `RUN`, `EXPLORE` |
| **Developer/Admin** | Maintain and add new features to the pipeline codebase. [Guideline](#getting-started-as-a-developer-or-admin).                                | `CREATE`, `RUN`, `EXPLORE` |

## Getting Started as a `Guest`

- _Goal_: **Explore the current pipeline and results** without running new data or new analyses, and with no installation required.
- _Steps_:
  1. Run notebooks on [DataJoint platform](https://works.datajoint.com/) (no installation required) or locally (requires minimal local setup/installation, see [`Experimenter Guideline`](#getting-started-as-a-experimenter).
  2. Run the `EXPLORE` notebooks. These notebooks showcase each pipeline modality and its results, such as behavior ingestion and synchronization, pipeline architecture, and more.

## Getting Started as a `Experimenter`

- _Goal_: **Run the pipeline analysis for a new session** on the cloud. You want to run the analysis quickly without delving into the code or spending time on debugging, troubleshooting or monitoring.
- _Requirements_:
  - Minimal local setup and installation.
  - Upload data to the cloud.
- _Steps_:
  1. Upload your data and register a new session following these instructions: [Running the Workflow Computations on the Cloud](RUN_ON_THE_CLOUD_GUIDE.md).
  2. Note that processing the new session will take some time.
  3. Run the `EXPLORE` notebook once results are generated to explore the results for the new session.

## Getting Started as a `Power-User`

- _Goal_: **Gain a deeper understanding of the pipeline, explore relevant code sections, debug, and troubleshoot effectively** in local or cloud environments.
- _Requirements_:
  - Local setup and installation.
  - Familiarity with relevant computations and session datasets.
- _Steps_:
  1. [Running the Workflow Computations on the Cloud](RUN_ON_THE_CLOUD_GUIDE.md) or [Run the Workflow Computations Locally](RUN_LOCALLY_GUIDE.md).
  2. Execute a `CREATE` notebook to create new parameters and/or tasks, if necessary.
  3. Execute a `RUN` notebook to run each of the computations.
  4. Run the `EXPLORE` notebooks once the results are generated.
  5. May contribute to the project documentation.
  6. Refer to the [Troubleshooting guide](TROUBLESHOOTING.md) for assistance if needed.

## Getting Started as a `Developer` or `Admin`

- _Goal_: **Develop and maintain the pipeline**, implement new features, and extend the pipeline.
- _Requirements_:
  - Comfortable with local setup and installation.
  - Understanding of the pipeline codebase.
  - Maintaining, debugging, and monitoring.
  - Provide training/support to the lab.
- _Steps_:
  1. [Run the Workflow Computations Locally](RUN_LOCALLY_GUIDE.md).
  2. May contribute to the pipeline codebase and project documentation.
  3. Refer to the [Troubleshooting guide](TROUBLESHOOTING.md) for assistance if needed.


## Standard Operating Procedure for the Utah Organoids DataJoint pipeline
You can find the standard operating procedures for the Utah Organoids DataJoint pipeline [here](PROCEDURE.md). Please refer to this document for detailed instructions on how to use the pipeline.