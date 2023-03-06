import datajoint as dj

db_prefix = dj.config["custom"].get("database.prefix", "")
