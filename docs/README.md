# Utah Organoids Pipelines Documentation

Welcome to the documentation for the **Utah Organoids Data Pipelines**. This guide will help different users get started, configure the system, troubleshoot, and test locally.

## Quick Start Guide

| User Type           | Description                                                                                                                                   | Relevant Notebooks         |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Guest**           | Explore data without installation. [Guideline](#getting-started-as-a-guest).                                                       | `EXPLORE` notebooks                  |
| **Experimenter**    | Run pipeline for new experiments without debugging. | [RUN_ON_CLOUD.md](./installation_and_configuration/RUN_ON_CLOUD.md)                  |
| **Power-User**      | Run specific computations, debugging locally and in the cloud.                  | [RUN_LOCALLY.md](./installation_and_configuration/RUN_LOCALLY.md), [RUN_ON_CLOUD.md](./installation_and_configuration/RUN_ON_CLOUD.md) |
| **Developer/Admin** | Extend, maintain, and debug pipeline.                                | [INSTALLATION_AND_CONFIGURATION.md](./installation_and_configuration/INSTALLATION_AND_CONFIGURATION.md), [TROUBLESHOOTING.md](./troubleshooting/TROUBLESHOOTING.md) |

## Documentation Structure

```
docs/
│── README.md (Main documentation entry point for users)
│── installation_and_configuration/
│   ├── INSTALLATION_AND_CONFIGURATION.md (Install pipeline and configure credentials)
│   ├── RUN_LOCALLY.md (Run computations locally)
│   ├── RUN_ON_CLOUD.md (Run computations on cloud)
│   ├── _ONPREMISE_DEPLOYMENT.md (On-premise deployment guide)
│   ├── CLOUD_UPLOAD_CONFIGURATION.md (Set up cloud upload via djsciops)
│   ├── DATA_ORGANIZATION.md (Folder hierarchy and data organization)
│── testing/
│   ├── LOCAL_TESTING_SCIVIZ.md (Testing data visualization locally)
│── troubleshooting/
│   ├── TROUBLESHOOTING.md (Common errors and debugging)
```
