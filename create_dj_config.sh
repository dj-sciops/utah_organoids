#!/bin/bash

# Prompt for a user input
echo -e "\n"
read -p "Enter DataJoint username: " datajoint_username
read -s -p "Enter DataJoint password: " datajoint_password
echo -e "\n"

echo '{
  "database.host": "db.datajoint.com",
  "database.user": "'"$datajoint_username"'",
  "database.password": "'"$datajoint_password"'",
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
    "raw_root_data_dir": "",
    "processed_root_data_dir": ""
  }
}' >dj_local_conf.json

echo "dj_local_conf.json file created at : $(pwd)/dj_local_conf.json"
echo -e "\n"
