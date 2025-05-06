# NoSQL-Database-Cluster-AISdata
 ASSINGMENT 3 Big Data Analysis

# TASK 1

To run the code for Task 1, it is important to have the correct folder setup so that Docker and MongoDB can cooperate.

## Folder setup:
BDSproject3/
├── docker-compose.yml
├── setup_mongo_cluster.sh
├── project3.py
├── aisdk-2023-05-01.csv
└── init-scripts/
   ├── initiate-config.js
   ├── initiate-shard1.js
   ├── initiate-shard2.js
   └── initiate-shards.js

Note: When running the Python script, an ais_clean.json file will be created. When running setup_mongo_cluster.sh, a folder named data with subfolders (config1, config2, config3, shard1, and shard2) will also be added to your setup.

## Steps to run:
Run the Python script project3.py
This will generate the ais_clean.json file.

In the terminal, run:
./setup_mongo_cluster.sh
This will set up the MongoDB sharded cluster with sharded AIS data.

### Troubleshooting:
If step 2 does not work, try the following command:
chmod +x setup_mongo_cluster.sh

This will ensure that you have execution permission for setup_mongo_cluster.sh. After running this command, retry 
./setup_mongo_cluster.sh

