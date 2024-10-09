# Pipeline Deployment (On-Premises)

This page describes the processes and required resources to deploy and operate the data pipeline on your own infrastructure, off of the DataJoint Works platform.

## Guide Overview

- [Prerequisites](#prerequisites)
- [Data Migration from DataJoint Works to your Local Infrastructure](#data-migration-from-datajoint-works-to-your-local-infrastructure)
- [Compute](#compute)
- [Operation at Scale](#operation-at-scale)

## Prerequisites

On the most basic level, in order to deploy and operate a DataJoint pipeline, you will need:

1. a MySQL database server (version 8.0) with configured to be DataJoint compatible
   - see [here](https://github.com/datajoint/mysql-docker/blob/master/config/my.cnf) for configuration of the MySQL server to be DataJoint compatible
2. a GitHub repository with the codebase of the DataJoint pipeline
   - this repository is the codebase, no additional modifications are needed to deploy this codebase locally
3. file storage
   - the pipeline requires a location to store the data files (this can be a local directory or mounted network storage)
   - this file storage should have two directories: `raw` and `processed`
     - `raw` points to root directory where the raw data files can be found
     - `processed` points to root directory where the processed data files can be found
   - on DataJoint Works, these are stored on AWS S3 under `inbox` and `outbox` directories respectively (but this point is irrelevant for local deployment)
4. compute
   - you need some form of a compute environment with the right software installed to run the pipeline (this could be a laptop, local work station or a HPC cluster)

## Data Migration from DataJoint Works to your Local Infrastructure

Once you have a MySQL database server setup locally, you should have a new set of DB credentials for this new MySQL server. You can update this information in the `dj_local_conf.json` file in the codebase.

There are 2 main components of the data that need to be migrated from DataJoint Works to your local infrastructure:

1. the MySQL database
   - the MySQL database can be exported from DataJoint Works (in the form of MySQL dumps) and imported into your local MySQL server
   - **_the DataJoint team will perform this export step and provide you with the MySQL dumps_**
   - you can then import these dumps into your local MySQL server (contact your IT team for support on this step)
2. the data files
   - the data files can be downloaded from AWS S3 to your local file storage (`raw` and `processed`)
   - **_the DataJoint team will provide you with the script to download the data files_**

## Compute

In order to run the pipeline, the minimal setup is described in the README, "Installation" section

You may need to configure different environments to run the different parts of the pipeline (e.g. some requires GPU, some requires higher RAM, etc.)

## Operation at Scale

The pipeline operation is designed to be operated at scale via "worker" definition - see [here](../workflow/populate/worker.py)

For the Docker containerization details for the workers, see [here](../docker/)

After installing the pipeline, you can run a worker via the command

```bash
run_workflow <worker_name>
```

where `<worker_name>` is one of the worker types defined in the `worker.py` file

Workers are designed to be run in parallel, to speed up the processing, you can run multiple workers at the same time:

- on different terminal on the same computer
- on different computers
- on multiple Docker containers
- on the cloud

Parallelization and jobs distribution are built-in and fully handled by DataJoint.
