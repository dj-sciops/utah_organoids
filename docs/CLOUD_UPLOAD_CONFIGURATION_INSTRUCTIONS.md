# Instructions to Upload Raw Data to the Cloud

Follow these steps to configure and upload your raw data files to the cloud:

1. Install the necessary package `djsciops`:

   ```
   pip install djsciops
   ```

2. Configure djsciops credentials (`config.yaml`):

   - Locate the `config.yaml` file by running:

     ```
     djsciops config
     ```

   - Open the `config.yaml` file in any text editor and update the following fields with the project account details:
     1. `account_id`
     2. `client_id`
     3. `client_secret`
     4. `issuer`
     5. `bucket`
     6. `role`

3. Upload the data: Use the [CREATE_new_session_with_cloud_upload](../notebooks/CREATE_new_session_with_cloud_upload.ipynb) notebook to register and upload data for a single subject and session.
