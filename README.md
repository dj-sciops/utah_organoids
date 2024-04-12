# Organoids DataJoint Workflows

DataJoint workflow for the Organoids project at the University of Utah.

## Organoids Creation Protocol Flowchart

<img src=./images/culture_diagram.png width="50%">

## Organoids DataJoint Diagram Experiment

<img src=./images/datajoint_diagram_experiment.svg>

## Organoids DataJoint Diagram Ephys Session

<img src=./images/datajoint_diagram_ephys_session.svg>

## SciViz website

Data viewer for the Utah Organoids DataJoint pipeline. Please use the entry forms provided on the website to manually input relevant data entries.

<https://organoids.datajoint.com/>

#### Testing the Data Viewer Locally

1. After making the code changes locally, run the following command to start the application:

```
docker compose -f webapps/sciviz/docker-compose.yaml up -d
```

1. Access the application using the following URL in an incognito window: <https://localhost/login> and log in with your DataJoint Works credentials.
1. When you have finished testing, please ensure to stop and remove the Docker container by running the following command:

```
docker compose -f webapps/sciviz/docker-compose.yaml down
```

## DataJoint Codebook for Organoids (JupyterHub)

Online coding environment:

<http://sciops-codebook.datajoint.com/>

+ Use your DataJoint Works credentials
+ Select the "Utah - Organoids" server, then press "Start"
+ Please, make sure to halt the server and log out if you access the codebook on a different day: `File/Hub Control Panel/ Stop My Server` and `Logout`

## Helpful References and Resources

+ Explore **interactive tutorials written in Python** covering various aspects of DataJoint. Access the tutorials [here](https://github.com/datajoint/datajoint-tutorials).
+ Notebook focusing on **logical operators in DataJoint tables** [here](https://github.com/datajoint-company/db-programming-with-datajoint/blob/master/notebooks/SQL%20Syntax%20for%20DataJoint%20Querying.ipynb)

+ Additional resources: DataJoint documentation references
  + Documentation on **DataJoint Table Tiers**: Access it [here](https://datajoint.com/docs/core/datajoint-python/0.13/reproduce/table-tiers/)
  + Documentation on **DataJoint Common Commands**: Access it [here](https://datajoint.com/docs/core/datajoint-python/0.13/query-lang/common-commands/)
  + Documentation on **DataJoint Operators**: Access it [here] (https://datajoint.com/docs/core/datajoint-python/0.13/query-lang/operators/)
  + Documentation regarding the **`update` operation**: Access it [here](https://datajoint.com/docs/core/datajoint-python/0.14/manipulation/update/)
  + Documenation on **DataJoint-to-SQL Transpilation**: Access it [here](https://datajoint.com/docs/core/datajoint-python/0.14/internal/transpilation/)
  + Documentation on **Quality Assurance and Code Reviews**: Access it [here](https://datajoint.com/docs/elements/management/quality-assurance/)

## Initial Installation & Configuration Instructions

Get started with the Utah Organoids project by following these steps:

1. Install [git](https://git-scm.com/download/win)
2. Install [conda](https://docs.conda.io/en/latest/miniconda.html)
3. Clone `utah_organoids` repository
    ```bash
    git clone https://github.com/dj-sciops/utah_organoids.git && cd utah_organoids
    ```
4. Create conda virtual environment
    ```bash
    conda env create -f conda_env.yml --force && conda activate utah_organoids
    ```
5. Install dependencies
    ```bash
    pip install -e . # on MacOS, quotes are needed: pip install -e '.[pipeline]'
    ```
6. To create the `dj_local_conf.json` file, execute the command below. Input your username and password when prompted:
    ```bash
    chmod +x ./create_dj_config.sh && ./create_dj_config.sh
    ```
7. Insert the AWS functional user credentials to fetch data from the s3 bucket to the notebook:
    + By inserting the credentials in the `dj_local_conf.json` file
    + By creating a `.env` file containing these credentials as environment variables

## Troubleshooting
- If you encounter the following error during the (5) step in the `Initial Configuration Instructions` on MacOS with an M2 processor:

```ERROR: Could not build wheels for datajoint, which is required to install pyproject.toml-based projects```

- Please follow these steps:
1. Install datajoint using the following command:
    ```bash
    pip install datajoint
    ``` 
2. Retry the step (5) by executing:
    ```bash
    pip install -e .[pipeline] # on MacOS, quotes are needed: pip install -e '.[pipeline]'
    ```
If you continue to experience any issues, feel free to reach out to us for assistance.

## Uploading Raw Data

Please follow these steps to upload your raw data files:

1. Configure `config.yaml` file
    1. Run the following to locate `config.yaml` file

        ```
        djsciops config
        ```

    2. Update the following values
        1. `account_id`
        4. `client_id`
        5. `issuer`
        6. `bucket`
        7. `role`
        8. `local_outbox`

1. On Windows, open the command prompt application by searching for the following:
    ```
    Anaconda Prompt (miniconda3)
    ```
2. Activate the conda environment by typing the following in the command prompt:
    ```bash
    conda activate utah_organoids
    ```
3. Open a python interpreter by typing the following in the command prompt:
    ```bash
    ipython
    ```
4. Change directories to where the raw data is stored
    ```python
    cd "D:\"
    ```
5. Run data upload for a single subject and a single recording session.
    ```python
    from workflow.utils.initiate_session import upload_session_data
    upload_session_data('<Relative path of data>')
    ```
