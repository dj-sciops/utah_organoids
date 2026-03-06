"""Pytest configuration for utah_organoids tests."""
import os
import tempfile
import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load test configuration from .env.test.local (if it exists)
env_file = Path(__file__).parent.parent / ".env.test.local"
if env_file.exists():
    load_dotenv(env_file)
    logger.info(f"Loaded test configuration from {env_file}")

# Set environment variables before any DataJoint imports
if "RAW_ROOT_DATA_DIR" not in os.environ:
    raw_temp = Path(tempfile.gettempdir()) / "utah_organoids_test_raw"
    raw_temp.mkdir(exist_ok=True)
    os.environ["RAW_ROOT_DATA_DIR"] = str(raw_temp)

if "PROCESSED_ROOT_DATA_DIR" not in os.environ:
    processed_temp = Path(tempfile.gettempdir()) / "utah_organoids_test_processed"
    processed_temp.mkdir(exist_ok=True)
    os.environ["PROCESSED_ROOT_DATA_DIR"] = str(processed_temp)

if "DATABASE_PREFIX" not in os.environ:
    os.environ["DATABASE_PREFIX"] = "test_utah_organoids_"

if "DJ_HOST" not in os.environ:
    os.environ["DJ_HOST"] = "localhost"
if "DJ_USER" not in os.environ:
    os.environ["DJ_USER"] = "root"
if "DJ_PASS" not in os.environ:
    os.environ["DJ_PASS"] = "test_password"
if "DJ_PORT" not in os.environ:
    os.environ["DJ_PORT"] = "3306"

USE_EXTERNAL_MYSQL = os.getenv("DJ_USE_EXTERNAL_CONTAINERS", "").lower() in (
    "1", "true", "yes",
)


@pytest.fixture(scope="session")
def mysql_container():
    """Start MySQL container for testing (or use external)."""
    if USE_EXTERNAL_MYSQL:
        logger.info("Using external MySQL (docker-compose or local)")
        yield None
        return

    from testcontainers.mysql import MySqlContainer

    container = MySqlContainer(
        image="mysql:8.0",
        username="root",
        password="test_password",
        dbname="test_db",
    )
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(3306)
    os.environ["DJ_HOST"] = host
    os.environ["DJ_PORT"] = str(port)
    os.environ["DJ_USER"] = "root"
    os.environ["DJ_PASS"] = "test_password"

    logger.info(f"MySQL container started at {host}:{port}")
    yield container
    container.stop()
    logger.info("MySQL container stopped")


@pytest.fixture(scope="session")
def dj_config(mysql_container):
    """Configure DataJoint for testing."""
    import datajoint as dj

    if Path("./dj_local_conf.json").exists():
        dj.config.load("./dj_local_conf.json")

    dj.config.update(
        {
            "safemode": False,
            "database.host": os.environ.get("DJ_HOST", "localhost"),
            "database.port": int(os.environ.get("DJ_PORT", "3306")),
            "database.user": os.environ.get("DJ_USER", "root"),
            "database.password": os.environ.get("DJ_PASS", "test_password"),
        }
    )

    if "custom" not in dj.config:
        dj.config["custom"] = {}

    dj.config["custom"]["database.prefix"] = os.environ["DATABASE_PREFIX"]
    dj.config["custom"]["raw_root_data_dir"] = os.environ["RAW_ROOT_DATA_DIR"]
    dj.config["custom"]["processed_root_data_dir"] = os.environ["PROCESSED_ROOT_DATA_DIR"]

    yield dj.config

    # Cleanup: drop all test databases
    logger.info("Cleaning up test databases...")
    prefix = os.environ["DATABASE_PREFIX"]
    try:
        conn = dj.conn()
        conn.query("SET FOREIGN_KEY_CHECKS=0")
        cursor = conn.query(f'SHOW DATABASES LIKE "{prefix}%%"')
        test_dbs = [db[0] for db in cursor.fetchall()]
        for db_name in test_dbs:
            logger.info(f"Dropping database: {db_name}")
            conn.query(f"DROP DATABASE IF EXISTS `{db_name}`")
        conn.query("SET FOREIGN_KEY_CHECKS=1")
        logger.info(f"Cleaned up {len(test_dbs)} test databases")
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests as unit or integration based on fixtures."""
    integration_fixtures = {
        "mysql_container", "dj_config", "pipeline",
        "patch_clamp_experiment", "patch_clamp_populated",
    }

    for item in items:
        try:
            fixturenames = set(item.fixturenames)
        except AttributeError:
            continue

        if fixturenames & integration_fixtures:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
