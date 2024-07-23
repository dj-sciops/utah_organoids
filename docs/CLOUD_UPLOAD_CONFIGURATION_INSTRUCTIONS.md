# Instructions to Upload Raw Data to the Cloud

Follow these steps to configure and upload your raw data files:

1. pip install djsciops 

2. Locate and update the `config.yaml` file with your account details:
    + Run this command to locate the `config.yaml` file

        ```
        djsciops config
        ```

    + Update the following fields:
        1. `account_id`
        4. `client_id`
        5. `issuer`
        6. `bucket`
        7. `role`
        8. `local_outbox`

3. Use the [CREATE_new_session_with_cloud_upload](../notebooks/CREATE_new_session_with_cloud_upload.ipynb) notebook to register and upload data for a single subject and session.

