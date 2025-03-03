# Running the Pipeline Locally

## Setup

1. Follow [`INSTALLATION_AND_CONFIGURATION.md`](INSTALLATION_AND_CONFIGURATION.md) to install dependencies and pipeline codebase, and configure your environment to connect to the database.
   - Ensure that the `raw_root_data_dir` and `processed_root_data_dir` in the `dj_local_conf.json` file are set to the local directories on your machine where the data will be stored and processed.

2. Organize data using the [`DATA_ORGANIZATION.md`](./DATA_ORGANIZATION.md) structure.

3. Create a new session using: [CREATE_new_session.ipynb](../../notebooks/CREATE_new_session.ipynb).

## Execute Computations

1. Run `populate` function in DataJoint designated `RUN` notebooks to manually trigger the pipeline's processing steps locally.
2. Use `CREATE`, `RUN`, and `EXPLORE` notebooks to interact with the pipeline.

## Debugging

- If issues arise, check the [`TROUBLESHOOTING.md`](../troubleshooting/TROUBLESHOOTING.md) guide.
