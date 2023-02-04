from datajoint import config

db_prefix = config["custom"].get("database.prefix", "")
