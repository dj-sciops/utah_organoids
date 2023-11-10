# Organoids DataJoint Workflows

DataJoint workflow for the Organoids project at the University of Utah.

## Organoids Creation Protocol Flowchart

<img src=./images/culture_diagram.png width="50%">

## Organoids DataJoint Diagram Experiment

<img src=./images/datajoint_diagram_experiment.svg>

## Organoids DataJoint Diagram Ephys Session

<img src=./images/datajoint_diagram_ephys_session.svg>

## SciViz website
Data viewer for the Organoids DataJoint pipeline. Please use the entry forms provided on the website to manually input relevant data entries.

https://organoids.datajoint.com/

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
1. To generate the `dj_local_config.json` file, execute the command below. Input your username and password when prompted:
    ```bash
    ./create_dj_config.sh
    ```
If you encounter permission denial, use the following command:
    ```bash
    chmod +x create_dj_config.sh
    ```

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
