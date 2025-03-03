# Installation & Configuration Guide

This guide helps users set up the **Organoids Data Pipeline**.

## Install Dependencies and Pipeline Codebase

1. GitHub account: [Sign up](http://github.com/signup) for a GitHub user account.
2. Install [Git](https://git-scm.com/download/win) and [Conda](https://docs.conda.io/en/latest/miniconda.html).
3. Fork the repository: Fork the main project repository to your GitHub account.
4. Clone the `utah_organoids` repository:

   ```bash
   git clone https://github.com/dj-sciops/utah_organoids.git && cd utah_organoids
   ```

5. Create and activate a Conda virtual environment:

   ```bash
   conda env create -f conda_env.yml
   conda activate utah_organoids
   ```

6. Install Python dependencies:

   ```bash
   pip install .
   ```

# Configure Credentials

## DataJoint Database Credentials

1. Copy `sample_dj_local_conf.json` to `dj_local_conf.json` in root directory.
2. Update with **username, password, and database host**.
   - Ensure the file is kept secure and not leaked.
3. Define paths for `raw_root_data_dir` and `processed_root_data_dir`:
     - `raw_root_data_dir` is the root directory where the raw data files can be found
     - `processed_root_data_dir` is the root directory where the processed data files will be generated and stored
   - **_All data paths stored in the pipeline will be relative to these root directories._**

4. Expected output sample:

```json
{
    "database.host": "db.datajoint.com",
    "database.user": "user123",
    "database.password": "password",
    "database.port": 3306,
    "connection.init_function": null,
    "database.reconnect": true,
    "database.use_tls": false,
    "enable_python_native_blobs": true,
    "loglevel": "INFO",
    "safemode": true,
    "display.limit": 20,
    "display.width": 40,
    "display.show_tuple_count": true,
    "custom": {
        "database.prefix": "utah_organoids_",
        "raw_root_data_dir": "/Users/user123/Documents/data/organoids/inbox",
        "processed_root_data_dir": "/Users/user123/Documents/data/organoids/outbox"
    }
}     
```

## AWS Credentials (Optional)

1. Create `.env` file in root directory:

```
AWS_ACCESS_KEY=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

2. To confirm that the AWS credentials are set up correctly, check the `stores` field in the `dj.config` in your notebook.

```python
import datajoint as dj
dj.config
```

3. Expected output sample:

```json
{
    "database.host": "db.datajoint.com",
    "database.user": "user123",
    "database.password": "password",
    "database.port": 3306,
    "connection.init_function": null,
    "database.reconnect": true,
    "database.use_tls": false,
    "enable_python_native_blobs": true,
    "loglevel": "INFO",
    "safemode": true,
    "display.limit": 20,
    "display.width": 40,
    "display.show_tuple_count": true,
    "custom": {
        "database.prefix": "utah_organoids_",
        "raw_root_data_dir": "/Users/user123/Documents/data/organoids/inbox",
        "processed_root_data_dir": "/Users/user123/Documents/data/organoids/outbox"
    },
    "stores": {
        "datajoint-blob": {
            "bucket": "dj-sciops",
            "endpoint": "s3.amazonaws.com:9000",
            "location": "utah_organoids/datajoint/blob",
            "protocol": "s3",
        }
    }
}
```

## Axon Credentials (Cloud Upload/Download)

1. Follow [CLOUD_UPLOAD_CONFIGURATION.md](./CLOUD_UPLOAD_CONFIGURATION.md) to set up the Axon credentials.

**Security Warning:** _Ensure that sensitive credentials, such as database passwords, API keys, and cloud authentication tokens, are never hardcoded in the repository. Use environment variables or secure configuration files (`.env`, `dj_local_conf.json`) and restrict access to authorized users only._
