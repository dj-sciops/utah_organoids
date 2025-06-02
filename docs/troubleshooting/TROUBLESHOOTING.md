# Troubleshooting Guide

## Common Installation Errors

- `ERROR: Could not build wheels for datajoint`
  - Install datajoint using the following command:

    ```bash
    pip install datajoint
    ```

  - Retry the installation process:

    ```bash
    pip install .
    ```

- Updating your local environment

  - Ensure your local environment is up-to-date with the latest changes in the codebase:

    1. Pull the latest code from the repository
    2. In your activated conda environment, upgrade dependencies to the latest versions:

       ```bash
       pip install --upgrade --upgrade-strategy eager .
       ```

    These steps synchronize your development environment with the latest updates and fixes.

- Issue with installing `hdbscan`, a necessary dependency for running `spykingcircus2` sorter for `SpikeInterface` analysis:

  - If you encounter the following error during installation:
    `ERROR: Failed to build installable wheels for some pyproject.toml based projects (hdbscan)`

  - You can try installing `hdbscan` via `conda` instead of `pip` to resolve the issue:

  ```bash
  conda install -c conda-forge hdbscan
  ```

- Ensure you have correctly installed and activated the `utah_organoids` conda environment before pip installing the cloned repository.
  - Errors such as: `ModuleNotFoundError: No module named 'datajoint'`
    might indicate that the pip installation did not occur within the activated conda environment. Be sure to activate the environment correctly and reinstall the repository if needed.

- To run computations locally, please ensure to:
  - Set the Jupyter Server kernel to match the Conda environment created specifically for this project.
  - Confirm the `dj_local_conf.json` configuration file is present and correctly configured.
