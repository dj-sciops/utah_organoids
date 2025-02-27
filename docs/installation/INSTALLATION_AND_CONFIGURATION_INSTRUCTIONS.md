# Installation of the Pipeline Codebase

1. GitHub account: [Sign up](http://github.com/signup) for a GitHub user account.
2. Fork the repository: Fork the main project repository to your GitHub account.
3. Install [Git](https://git-scm.com/download/win)
4. Install [Conda](https://docs.conda.io/en/latest/miniconda.html)
5. Clone the `utah_organoids` repository:

   ```bash
   git clone https://github.com/dj-sciops/utah_organoids.git && cd utah_organoids
   ```

6. Create and activate a Conda virtual environment:

   ```bash
   conda env create -f conda_env.yml
   ```

   ```bash
   conda activate utah_organoids
   ```

7. Install dependencies:

   ```bash
   pip install .
   ```

# Configuration Instructions: Credential Types

## Configuring DataJoint Credentials for Connecting to the Database (Guest, Experimenter, Power-User,Admin/Developer)

DataJoint requires a configuration file named `dj_local_conf.json`. This file should be located in the root directory of the codebase.

1. Generate the `dj_local_conf.json` file:
   - Make a copy of the `sample_dj_local_conf.json` file with the exact name `dj_local_conf.json`.
   - Update the file with your database credentials (username, password, and database host ID).
   - Ensure the file is kept secure and not leaked.
2. Specify the `database.prefix` in `dj_local_conf.json` to avoid conflicts with other databases.
3. Set up paths for raw and processed data directories in `dj_local_conf.json`:

   - Update the `raw_root_data_dir` and `processed_root_data_dir` in the `dj_local_conf.json` file
     - `raw_root_data_dir` is the root directory where the raw data files can be found
     - `processed_root_data_dir` is the root directory where the processed data files will be generated and stored
   - **_All data paths stored in the pipeline will be relative to these root directories._**

## Configuring AWS Credentials for Accessing External Data in the Notebook (Optional for Guest, Experimenter, Power-User,Admin/Developer)

To configure AWS functional user credentials in `dj.config`, follow this method:

2. Use a `.env` file for the AWS `access_key` and `secret_key`. Ensure these credentials remain confidential.
   Create a `.env` file in the root directory of your local repository with the following keys:

```

AWS_ACCESS_KEY=xxx
AWS_SECRET_ACCESS_KEY=xxx

```

3. To confirm that the AWS credentials are set up correctly, check the `stores` field in the `dj.config` in your notebook.

## Configuring Axon Credentials for Uploading/Downloading Data to the Cloud (Power-User,Admin/Developer)

Axon credentials are configured via `djsciops` for uploading and downloading data in the cloud. For detailed instructions, please follow the [RUN_ON_THE_CLOUD_GUIDE](RUN_ON_THE_CLOUD_GUIDE.md)
