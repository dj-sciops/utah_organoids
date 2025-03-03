# Cloud Data Upload Configuration

1. Install required package `djsciops`:

   ```
   pip install djsciops
   ```

2. Configure credentials (config.yaml) for cloud upload:

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

3. Expected output sample:

  ```
  aws:
    account_id: account_id
  boto3:
    max_concurrency: 100
    multipart_chunksize: 67108864
    multipart_threshold: 67108864
    use_threads: true
  djauth:
    client_id: client_id
    client_secret: client_secret
    issuer: issuer
  s3:
    bucket: bucket
    role: role
  version: 1.5.8
  ```

3. Upload data using [UPLOAD_session_data_to_cloud](../../notebooks/UPLOAD_session_data_to_cloud.ipynb) notebook.

**Security Warning:** _Never commit your `config.yaml` file containing cloud credentials to the repository. Always store sensitive information such as `account_id`, `client_secret`, and `AWS keys` in a secure location, such as environment variables or a secrets manager. To prevent accidental leaks, ensure that `config.yaml` is added to your `.gitignore` file._
