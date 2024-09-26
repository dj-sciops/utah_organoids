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

# Configuration Instructions

DataJoint requires a configuration file named `dj_local_conf.json`. This file should be located in the root directory of the codebase.

1. Generate the `dj_local_config.json` file:
   - Make a copy of the `sample_dj_local_conf.json` file with the exact name `dj_local_config.json`.
   - Update the file with your database credentials (username, password, and database host ID).
   - Ensure the file is kept secure and not leaked.
2. Specify the `database.prefix` in `dj_local_conf.json` to avoid conflicts with other databases.
3. Set up paths for raw and processed data directories in `dj_local_conf.json`:

   - Update the `raw_root_data_dir` and `processed_root_data_dir` in the `dj_local_conf.json` file
     - `raw_root_data_dir` is the root directory where the raw data files can be found
     - `processed_root_data_dir` is the root directory where the processed data files will be generated and stored
   - **_All data paths stored in the pipeline will be relative to these root directories._**

4. Insert the AWS functional user credentials to fetch data from the s3 bucket to the notebook:
   - By inserting the credentials in the `dj_local_conf.json` file
   - By creating a `.env` file containing these credentials as environment variables
