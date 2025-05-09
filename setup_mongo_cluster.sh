#!/bin/bash

# Create required data directories for MongoDB volumes
echo "Creating necessary data directories..."
mkdir -p data/config1 data/config2 data/config3 \
         data/shard1a data/shard1b data/shard1c \
         data/shard2a data/shard2b data/shard2c

# Start Docker containers using Docker Compose
echo "Starting Docker containers..."
docker compose up -d

# Wait until MongoDB containers are fully up (adjust the sleep time if needed)
echo "Waiting for MongoDB containers to start..."
sleep 10  # Adjust the sleep time to ensure containers are up

# Run the init scripts for config servers
echo "Initialising config servers..."
docker exec -it config1 mongosh /init-scripts/initiate-config.js

# Wait until config servers are fully up 
echo "Waiting for config servers..."
sleep 10

# Initialise shard1 and shard2
echo "Initialising shard1..."
docker exec -it shard1a mongosh /init-scripts/initiate-shard1.js
sleep 20

echo "Initialising shard2..."
docker exec -it shard2a mongosh /init-scripts/initiate-shard2.js
sleep 20

# Wait until shards are fully up 
echo "Waiting for shards..."
sleep 100

# Initialise the mongos router
echo "Initialising mongos..."
docker exec -it mongos mongosh /init-scripts/initiate-shards.js
# Wait until mongos router is fully up 
echo "Waiting for mongos router..."
sleep 20
echo "NoSQL database cluster created"

# Import and sort the AIS data from CSV (limit: 1,000,000 rows)
echo "5 steps to import and sort the AIS data (CSV version, 1M rows)"

# Step 1: Create an empty database and collection
echo "Step 1: Create empty database and collection..."
docker exec -it mongos mongosh --eval 'use ais; db.createCollection("ais_data")'
docker exec -it mongos mongosh --eval 'use ais; db.createCollection("raw_vessels_limited")'
docker exec -it mongos mongosh --eval 'use ais; db.createCollection("clean_vessels")'

# Step 2: Enable sharding on the 'ais' database
echo "Step 2: Enable sharding on the database..."
docker exec -it mongos mongosh --eval 'sh.enableSharding("ais")'

# Step 3: Create an index on the 'MMSI' field and shard the collection
echo "Step 3: Create index on MMSI for sharding..."
docker exec -it mongos mongosh --eval 'use ais; db.ais_data.createIndex({ MMSI: 1 })'
docker exec -it mongos mongosh --eval 'use ais; db.raw_vessels_limited.createIndex({ MMSI: 1 })'
docker exec -it mongos mongosh --eval 'use ais; db.clean_vessels.createIndex({ MMSI: 1 })'

# Step 4: Shard the collection on MMSI
echo "Step 4: Shard the collection on MMSI..."
docker exec -it mongos mongosh --eval 'sh.shardCollection("ais.ais_data", { MMSI: 1 })'
docker exec -it mongos mongosh --eval 'sh.shardCollection("ais.raw_vessels_limited", { MMSI: 1 })'
docker exec -it mongos mongosh --eval 'sh.shardCollection("ais.clean_vessels", { MMSI: 1 })'

# Step 5: Extract first 1M rows (plus header), copy to container, import to MongoDB
echo "Step 5: Import first 1,000,000 rows from CSV into MongoDB..."
head -n 1000001 aisdk-2023-05-01.csv > ais_sample_1M.csv
docker cp ais_sample_1M.csv mongos:/data/ais_sample_1M.csv

docker exec -it mongos bash -c 'mongoimport --host localhost --port 27017 --db ais --collection ais_data --type csv --file /data/ais_sample_1M.csv --headerline'

# All done!
echo "MongoDB sharded cluster setup is complete!"
