# Organoids DataJoint Workflows

DataJoint workflow for the Organoids project at the University of Utah.

## Initial configuration instructions

1. Install [git](https://git-scm.com/download/win)
1. Install [conda](https://docs.conda.io/en/latest/miniconda.html)
1. Create conda environment
    ```bash
    conda create --name djutah python=3.8
    ```
1. Activate conda environment
    ```bash
    conda activate djutah
    ```
1. Clone `utah_organoids` repository
    ```bash
    git clone https://github.com/dj-sciops/utah_organoids.git
    ```
1. Within `utah_organoids` directory install the package
    ```bash
    pip install -e .
    ```
1. Configure database connection
    ```python
    import datajoint as dj
    import getpass
    dj.config["custom"]={}
    dj.config["custom"]["database.prefix"]="utah_organoids"
    dj.config["database.host"]="rds.datajoint.io"
    dj.config["database.user"]="arifneuro"
    dj.config["database.password"]=getpass.getpass()
    dj.config.save_global()
    ```
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

## Data upload

1. On Windows, open the command prompt application by searching for the following:
    ```
    Anaconda Prompt (miniconda3)
    ```

1. Activate the conda environment by typing the following in the command prompt:
    ```bash
    conda activate djutah
    ```

1. Open a python interpreter by typing the following in the command prompt:
    ```bash
    ipython
    ```

1. Run data upload for a single session.
    ```python
    from workflow import upload_session_data
    upload_session_data('<Relative path of data>')
    ```
