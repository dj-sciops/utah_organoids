# Running the Workflow Computations Locally

## Configuration Instructions

1. [Installation of the Pipeline Codebase](INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#installation-of-the-pipeline-codebase): Install the necessary components of the pipeline codebase.
2. [Configuration Instructions](INSTALLATION_AND_CONFIGURATION_INSTRUCTIONS.md#configuration-instructions): Configure your environment to connect to the DataJoint database.
    + Ensure that the `raw_root_data_dir` and `processed_root_data_dir` in the `dj_local_conf.json` file are set to the local directories on your machine where the data will be stored and processed.

3. **Organize Data According to Lab's Hierarchy**: Ensure your data adheres to the [Lab's Consensus Hierarchy of Folders](DATA_ORGANIZATION.md). Proper data organization is essential for the pipeline to process data accurately.

4. **Create a New Session**: Start by inserting a new session into the pipeline.
    + Detailed instructions are available in [CREATE_new_session.ipynb](../notebooks/CREATE_new_session.ipynb).
    + Certain processing tasks for specific modalities require manual specification by the user. Further details are available in the designated `CREATE` notebooks.

5. **Execution**: Use the `populate` function in DataJoint to process and compute data for specific tables:
    + To execute computations locally, use the `populate` function of DataJoint within the designated `RUN` notebooks. These notebooks contain instructions to manually trigger the pipeline's processing steps.

5. **Explore the Results**: After processing and analysis, results are stored in the corresponding tables and schemas:
    + Explore and fetch results from the pipeline using the designated `EXPLORE` notebooks.

## Before Running a Notebook

- Set the Jupyter Server kernel to match the Conda environment created specifically for this project.
- Confirm the `dj_local_conf.json` configuration file is present and correctly configured.
