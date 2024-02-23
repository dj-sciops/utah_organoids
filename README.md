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

https://organoids.datajoint.com/

#### Testing the Data Viewer Locally
1. After making the code changes locally, run the following command to start the application:
```
docker compose -f webapps/sciviz/docker-compose.yaml up
```
1. Access the application using the following URL: https://localhost/login and log in with your DataJoint Works credentials.
1. When you have finished testing, please ensure to stop and remove the Docker container by running the following command:
```
docker compose -f webapps/sciviz/docker-compose.yaml down
```

## DataJoint Codebook for Organoids (JupyterHub)

Online coding environment:

http://sciops-codebook.datajoint.com/

+ Use your DataJoint Works credentials
+ Select the "Utah - Organoids" server, then press "Start"
+ Please, make sure to halt the server and log out if you access the codebook on a different day: `File/Hub Control Panel/ Stop My Server` and `Logout`

## Initial Configuration Instructions

Get started with the Utah Organoids project by following these steps:

1. Install [git](https://git-scm.com/download/win)
1. Install [conda](https://docs.conda.io/en/latest/miniconda.html)
1. Clone `utah_organoids` repository
    ```bash
    git clone https://github.com/dj-sciops/utah_organoids.git && cd utah_organoids
    ```
1. Create conda virtual environment
    ```bash
    conda env create -f env.yml --force && conda activate utah_organoids
    ```
1. Install dependencies
    ```bash
    pip install -e .
    ```
1. To create the `dj_local_conf.json` file, execute the command below. Input your username and password when prompted:
    ```bash
    chmod +x ./create_dj_config.sh && ./create_dj_config.sh
    ```
1. Insert the AWS functional user credentials to fetch data from the s3 bucket to the notebook:
    + By inserting the credentials in the `dj_local_conf.json` file
    + By creating a `.env` file containing these credentials as environment variables


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

1. Activate the conda environment by typing the following in the command prompt:
    ```bash
    conda activate utah_organoids
    ```

1. Open a python interpreter by typing the following in the command prompt:
    ```bash
    ipython
    ```

1. Change directories to where the raw data is stored
    ```python
    cd "D:\"
    ```

1. Run data upload for a single subject and a single recording session.
    ```python
    from workflow import upload_session_data
    upload_session_data('<Relative path of data>')
    ```
