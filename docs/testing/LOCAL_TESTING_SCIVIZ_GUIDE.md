# Local Testing for SciViz

## Steps

1. Start SciViz with:

```bash
docker compose -f webapps/sciviz/docker-compose.yaml up -d
```

2. Open <https://localhost/login> and log in.

3. Shut down when done:

```bash
docker compose -f webapps/sciviz/docker-compose.yaml down
```
