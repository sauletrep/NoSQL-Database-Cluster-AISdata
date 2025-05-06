#!/bin/bash

# Create required data directories for MongoDB volumes
echo "Creating necessary data directories..."
mkdir -p data/config1 data/config2 data/config3 data/shard1 data/shard2

# Start Docker containers using Docker Compose
echo "Starting Docker containers..."
docker-compose up -d

# Wait until MongoDB containers are fully up (adjust the sleep time if needed)
echo "Waiting for MongoDB containers to start..."
sleep 10  # Adjust the sleep time to ensure containers are up

# Run the init scripts for config servers
echo "Initializing config servers..."
docker exec -it config1 mongosh /init-scripts/initiate-config.js

# Wait until config servers are fully up 
echo "Waiting for config servers..."
sleep 10

# Initialize shard1 and shard2
echo "Initializing shard1..."
docker exec -it shard1 mongosh /init-scripts/initiate-shard1.js
echo "Initializing shard2..."
docker exec -it shard2 mongosh /init-scripts/initiate-shard2.js
# Wait until shards are fully up 
echo "Waiting for shards..."
sleep 20

# Initialize the mongos router
echo "Initializing mongos..."
docker exec -it mongos mongosh /init-scripts/initiate-shards.js
# Wait until mongos router is fully up 
echo "Waiting for mongos router..."
sleep 20

# Import and sort the AIS data
echo "5 steps to import and sort the AIS data"

# Create an empty database and collection
echo "Step 1: Create empty database and collection..."
docker exec -it mongos mongosh --eval 'use ais; db.createCollection("ais_data")'

# Enable sharding on the 'ais' database
echo "Step 2: Enable sharding on the database..."
docker exec -it mongos mongosh --eval 'sh.enableSharding("ais")'

# Create an index on the 'MMSI' field and shard the collection
echo "Step 3: Create index on MMSI for sharding..."
docker exec -it mongos mongosh --eval 'use ais; db.ais_data.createIndex({ MMSI: 1 })'

# Import the JSON data to the MongoDB container
echo "Step 4: Shard the collection on MMSI..."
docker exec -it mongos mongosh --eval 'sh.shardCollection("ais.ais_data", { MMSI: 1 })'

# Import the JSON data to the MongoDB container now that sharding is enabled
echo "Step 5: Import data to MongoDB..."
docker cp ais_clean.json mongos:/data/ais_clean.json
docker exec -it mongos bash -c 'mongoimport --host localhost --port 27017 --db ais --collection ais_data --file /data/ais_clean.json --type json'

# All done!
echo "MongoDB sharded cluster setup is complete!"
