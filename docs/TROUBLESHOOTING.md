# Troubleshooting

## Debugging

Debugging `populate` function: If you encounter issues with the `populate` function in your DataJoint pipeline, refer to the [RUN Debugging Guide](../notebooks/RUN_debugging_guide.ipynb) notebook. This resource provides useful insights for troubleshooting and resolving common problems during data population.

## Local Installation Troubleshooting

If you encounter errors during [Running the Workflow Computations Locally](RUN_LOCALLY_GUIDE.md), follow these steps:

- ```ERROR: Could not build wheels for datajoint```

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