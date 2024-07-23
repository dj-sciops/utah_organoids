# Testing the Data Viewer Locally

1. After making the code changes locally, run the following command to start the application:

```
docker compose -f webapps/sciviz/docker-compose.yaml up -d
```

2. Access the application using the following URL in an incognito window: <https://localhost/login> and log in with your DataJoint Works credentials.

3. When you have finished testing, please ensure to stop and remove the Docker container by running the following command:

```
docker compose -f webapps/sciviz/docker-compose.yaml down
```
