# NoSQL Database Cluster with AISdata
 ASSINGMENT 3 - Big Data Analysis

# TASK 1

To run the code for Task 1, it is important to have the correct folder setup so that Docker and MongoDB can cooperate.

## Folder setup:
BDSproject3

* docker-compose.yml
* setup_mongo_cluster.sh
* project3.py
* aisdk-2023-05-01.csv
* init-scripts
  * initiate-config.js
  * initiate-shard1.js
  * initiate-shard2.js
  * initiate-shards.js

Note: When running the Python script, an ais_clean.json file will be created. When running setup_mongo_cluster.sh, a folder named data with subfolders (config1, config2, config3, shard1, and shard2) as well as folders db and configdb, will be added to your setup.

## Steps to run:
Step 1:
Run the Python script project3.py

This will generate the ais_clean.json file.

Step 2:
In the terminal, run:
```
./setup_mongo_cluster.sh
```
This will set up the MongoDB sharded cluster with sharded AIS data.

### Troubleshooting:
If step 2 does not work, try the following command:
```
chmod +x setup_mongo_cluster.sh
```
This will ensure that you have execution permission for setup_mongo_cluster.sh. After running this command, retry 
./setup_mongo_cluster.sh

# Documentation of the process for task 1

## Table of contents
* 1.0 MongoDB Sharded Cluster Setup
* 1.1 Config Servers and Mongos Router
* 1.2 Shards
* 1.3 Registering Shards with Mongos
* 1.4 Testing Sharding
* 1.5 Cleanup
* 2.0 Loading the Data
* 2.1 Sharding Configuration in MongoDB
* 2.2 Automating with setup_mongo_cluster.sh
* 3.0 Testing final setup
* 3.1 Check the shards status

# 1.0 MongoDB sharded cluster setup

## 1.1 Config servers and mongos router
The first step was to define the MongoDB sharded cluster using Docker Compose. We created a docker-compose.yml file with the following components:

* Config Servers (config1, config2, config3): Each running MongoDB as a config server with replica sets. These manage the metadata and routing information for the sharded cluster. Three config servers are necessary for redundancy and fault tolerance.
* Mongos Router: Entry point for routing queries, connected to the config servers. When setup is finished, the mongos router will handle client requests and forwards them to the appropriate shard. 

The docker-compose.ylm file looked like this:
```
version: '3.8' 

services: # Define all the containers you want to run
  config1:
    image: mongo:5 # Use the official MongoDB image
    container_name: config1
    ports:
      - "26001:27017" # Map the container port to the host port
    networks: 
      - mongo-cluster # Connect to the custom network
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--port", "27017"] # Start as a config server
    volumes: 
      - ./data/config1:/data/db # Save data in a local folder on computer
      - ./init-scripts:/init-scripts # Mount init scripts to the container

  config2:
    image: mongo:5
    container_name: config2
    ports:
      - "26002:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--port", "27017"]
    volumes:
      - ./data/config2:/data/db
      - ./init-scripts:/init-scripts 

  config3:
    image: mongo:5
    container_name: config3
    ports:
      - "26003:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--port", "27017"]
    volumes:
      - ./data/config3:/data/db
      - ./init-scripts:/init-scripts 

  mongos:       # Router (entrypoint for queries)
    image: mongo:5 
    container_name: mongos
    ports:
      - "27018:27017"
    networks:
      - mongo-cluster
    command: ["mongos", "--configdb", "configReplSet/config1:27017,config2:27017,config3:27017"]
    depends_on:
      - config1
      - config2
      - config3

networks:  # Define a custom network for the containers
  mongo-cluster:
```

Once the docker-compose.yml file was set up, we ran docker-compose up -d to bring up the containers. We then made the folder init-scripts and added the first initialising script: initiate-config.js. This script initialises the config servers and sets up the replica set configReplSet:

```
rs.initiate({
    _id: "configReplSet",
    configsvr: true,
    members: [
        { _id: 0, host: "config1:27017" },
        { _id: 1, host: "config2:27017" },
        { _id: 2, host: "config3:27017" }
    ]
});
```
This script sets up the config servers as a replica set and prepares them to manage the cluster’s metadata. We checked the replica set status using rs.status() and verified that config1 was PRIMARY, and config2 and config3 were SECONDARY.

## 1.2 Shards
After initializing the config servers, the next step was to add shards to the cluster. Each shard is a replica set in itself, and we used the following configuration for two shards (shard1 and shard2) between config3 and mongos:
```
  shard1:
    image: mongo:5
    container_name: shard1
    ports:
      - "27019:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--shardsvr", "--replSet", "shard1ReplSet", "--port", "27017"]
    volumes:
      - ./data/shard1:/data/db
      - ./init-scripts:/init-scripts

  shard2:
    image: mongo:5
    container_name: shard2
    ports:
      - "27020:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--shardsvr", "--replSet", "shard2ReplSet", "--port", "27017"]
    volumes:
      - ./data/shard2:/data/db
      - ./init-scripts:/init-scripts
```
This config defines the two shard containers, each with a replica set shard1ReplSet and shard2ReplSet. I then ran docker-compose down followed by docker-compose up -d to restart the containers and apply the changes.

Then, as with the config servers, the shards need to be initiated. Inside init-scripts we make a initiate-shards.js containing
```
sh.addShard("shard1ReplSet/shard1:27017");
sh.addShard("shard2ReplSet/shard2:27017");
```
But different from the config servers the shards in our MongoDB sharded cluster are essentially both separate replica sets. Therefore they need to be initiated seperatly. This is the reason we needed to add two scripts, initiate-shard1.js and initiate-shard2.js. They initialise each shard’s replica set individually, and then adds them to the cluster. Each shard will have its own replica set (shard1ReplSet and shard2ReplSet), so these scripts contain the necessary commands to set them up and configure them properly. We used the following scripts for each shard:
```
rs.initiate({
    _id: "shard1ReplSet",
    members: [
        { _id: 0, host: "shard1:27017" }
    ]
});
```
```
rs.initiate({
    _id: "shard2ReplSet",
    members: [
        { _id: 0, host: "shard2:27017" }
    ]
});
```
We ran these scripts by executing the following commands:
```
docker exec -it shard1 mongosh /init-scripts/initiate-shard1.js
docker exec -it shard2 mongosh /init-scripts/initiate-shard2.js
```
We checked the status of each shard using rs.status(), confirming that both shard1 and shard2 were PRIMARY meaning the nodes are properly configured and should be part of the cluster, and each shard is correctly initialized with its own replica set (shard1ReplSet for shard 1 and shard2ReplSet for shard 2).

## 1.3 Registering shards with mongos
Next, we wanted to register the shards with the mongos router using the initiate-shards.js script. Since the mongos container did not initially have access to the initialization scripts, we added the init-scripts volume to the mongos service in the docker-compose.yml file
```
    volumes:
      - ./init-scripts:/init-scripts
      - /Users/sauletrep/Documents/VU/BDA/BDSproject3:/data
```

After restarting the containers, we executed:
```
docker exec -it mongos mongosh /init-scripts/initiate-shards.js
```
Again we checked the status of the sharded cluster by running sh.status() inside the mongos container. The status showed that the shards were successfully added and the balancer was enabled, although no data had been distributed yet. But obviously this was expected due to not having loaded any data inthe containers. Here are some of the outputs from when we cheked the status:

state: 1 means both shards are healthy and available.

Balancer is enabled and idle, which is expected when there’s no data yet.

Autosplit is enabled, which is good for managing chunk sizes.

Mongos is connected and active.

OBS! shardedDataDistribution: undefined. This is ok for now as we had not sharded any collections yet, nor enabled sharding on any user database. 
Also, collections: {}, which  means the config database has no sharded collections either, but again this is expected for now.

## 1.4 Testing sharding
To test the sharding functionality, we created a sharded collection. First we enabled sharding on the database myTestDB and then created a collection myColl with a hashed _id field:
```
sh.enableSharding("myTestDB");

db = db.getSiblingDB("myTestDB");
db.myColl.createIndex({ _id: "hashed" });
sh.shardCollection("myTestDB.myColl", { _id: "hashed" });
```
Next, we inserted 10,000 documents into the collection:
```
for (let i = 0; i < 10000; i++) {
  db.myColl.insert({ _id: i, value: "test" + i })
}
```
We verified the sharded collection with sh.status(), and saw that our MongoDB sharded cluster was configured and working correctly. 
To further test the sharding, we inserted additional documents into myColl and checked the shard distribution. The documents were distributed evenly between the two shards, confirming that the sharded collection was functioning correctly.

We insert multiple documents to trigger chunk distribution (especially with a hashed _id) with
```
for (let i = 0; i < 1000; i++) {
    db.myColl.insertOne({ name: "doc_" + i, value: Math.floor(Math.random() * 1000) });
}
```
Since this should populate the sharded collection myColl, we could count the documents by db.myColl.countDocuments(), and sure enough had 11000 documents in myColl. We then checked the distribution with db.myColl.getShardDistribution() and found that the data is distributed evenly between shard1ReplSet and shard2ReplSet (50.2% and 49.8%).

We also performed range queries to ensure the data was accessible across the shards:
```
db.myColl.findOne({ name: "doc_500" })
db.myColl.find({ value: { $gt: 900 } }).limit(5).pretty()
```
The queries returned results as expected, confirming that the data was distributed and accessible across shards.

## 1.5 Cleanup
To remove the data, we used the following commands:
```
docker exec -it mongos mongosh
use myTestDB
db.myColl.drop()
```
To delete the entire database:
```
docker exec -it mongos mongosh
use myTestDB
db.dropDatabase()
```
We verified the deletion by running show dbs in the mongos container.

# 2.0 Loading the Data

The initial step was to load the raw AIS data into a suitable format for MongoDB. The df.to_json("ais_clean.json", orient="records", lines=True) command was used to convert the data frame to JSON format. JSON is a natural fit for MongoDB since MongoDB stores data as BSON (Binary JSON), making it easy to map data in this format directly to collections in MongoDB.

Once the data was converted into the ais_clean.json file, it was transferred into the Docker container running the MongoDB router (mongos) using the docker cp command:
```
docker cp ais_clean.json mongos:/data/ais_clean.json
```
This command places the data into the /data directory inside the mongos container. It's important that this directory matches what was defined in the docker-compose.yml file, ensuring proper placement inside the container. 

To insert the AIS data into the MongoDB instance, the mongoimport tool was used inside the mongos container:
```
mongoimport --host localhost --port 27017 \
  --db ais --collection ais_data \
  --file /data/ais_clean.json --type json
```

This command imports the JSON data into the ais database, specifically into the ais_data collection. The mongoimport tool is ideal for batch importing large datasets like this.

After the import, the output confirmed that 10 million documents were successfully inserted into the database, and no documents failed to import.


## 2.1 Sharding configuration in MongoDB

Sharding is essential for managing large datasets by distributing data across multiple servers (shards). It helps scale the database horizontally. In MongoDB, we need to configure sharding explicitly. 

First, we enabled sharding for the entire ais database:
```
mongosh
sh.enableSharding("ais")
```
Then we created an index on the MMSI field. With an index on the sharded field (which in our case was MMSI), MongoDB can efficiently partition data across shards:
```
use ais
db.ais_data.createIndex({ MMSI: 1 }) 
```
We then told MongoDB to shard the ais_data collection on the MMSI field:
```sh.shardCollection("ais.ais_data", { MMSI: 1 })```

## 2.2 Automating with setup_mongo_cluster.sh
Since we had now seen that everything was working as expected we streamlined the entire setup process by creaeing a script: setup_mongo_cluster.sh. This script automates the sequence of commands, making it easier to set up the MongoDB sharded cluster and load the data. Without this a user would have to write all these commands themselves in the terminal:
```
start up docker desktop
docker exec -it config1 mongosh /init-scripts/initiate-config.js
docker exec -it config1 mongosh
rs.status()
exit

docker exec -it shard1 mongosh /init-scripts/initiate-shard1.js
docker exec -it shard2 mongosh /init-scripts/initiate-shard2.js

docker exec -it mongos mongosh /init-scripts/initiate-shards.js
docker exec -it mongos mongosh
sh.status()
exit

docker cp ais_clean.json mongos:/data/ais_clean.json

docker exec -it mongos bash

mongoimport --host localhost --port 27017 \
  --db ais --collection ais_data \
  --file /data/ais_clean.json --type json

mongosh
sh.enableSharding("ais")

use ais
db.ais_data.createIndex({ MMSI: 1 }) 
sh.shardCollection("ais.ais_data", { MMSI: 1 })
# wait untill sh.getBalancerState() = False
exit
```
So to streamline we just rewrote the code above in the script. We made some minor changes to the format and added echo strings to tell the user what was going on. Also we had to add some timers to alow for the container startup as well as config server and shards setup. These timers may be too long some places but for hte other tasks this will anyway be changed so we didnt put too much thought into it for now. 

# 3.0 Testing final setup
To check that everything would go smoothly we had to make sure nothing was saved in the background on the computer we were working on. We cleaned all containers, images, networks, and volumes with
```
docker-compose down -v
docker system prune -af --volumes
rm -rf ./data/
```
as well as manually deleteing all folders and files created (ais_clean.json, db and configdb)

Then we ran the python code, to generate the ais_clean.json file. We cheked that the script was executable by:
```
chmod +x setup_mongo_cluster.sh
```
and then ran the script with:
```
./setup_mongo_cluster.sh
```
## 3.1 Check the shards status
We cheked the shards with sh.status(), and saw that the shards were initialised corretly, ais_data collection was successfully sharded by the MMSI field and balancer was running. The balancing process was ongoing due to our choice of importing the data before sharding it. After relising this made the balancer take way too long to finish, we just simply reordered the data imorting and sharding. 


# 4.0 Adding replica sets to the shards
To make the MongoDB sharded cluster resilient against container failures, we replaced the single-node shard containers with 3-node replica sets for each shard. This ensures that if one node in a shard fails, the remaining replicas can take over. Previously, we only had shard1 and shard2, each running a standalone mongod instance and both as primary. If either container failed, the corresponding shard became unavailable.


## 4.1 Summary of adding replica sets

We replaced each shard with three containers (replica set members):

* shard1 was replaced by shard1a, shard1b, shard1c,

* shard2 was replaced by shard2a, shard2b, shard2c.

This gave us two full 3-node replica sets, one for each shard.


## 4.2 Docker compose modifications

First we updated docker-compose by remoing services shard1 and shard to, and adding:
```
shard1a:
    image: mongo:5
    container_name: shard2a
    ports:
      - "27020:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--shardsvr", "--replSet", "shard2ReplSet", "--port", "27017"]
    volumes:
      - ./data/shard2a:/data/db
      - ./init-scripts:/init-scripts

  shard1b:
    image: mongo:5
    container_name: shard2b
    ports:
      - "27120:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--shardsvr", "--replSet", "shard2ReplSet", "--port", "27017"]
    volumes:
      - ./data/shard2b:/data/db
      - ./init-scripts:/init-scripts

  shard1c:
    image: mongo:5
    container_name: shard2c
    ports:
      - "27220:27017"
    networks:
      - mongo-cluster
    command: ["mongod", "--shardsvr", "--replSet", "shard2ReplSet", "--port", "27017"]
    volumes:
      - ./data/shard2c:/data/db
      - ./init-scripts:/init-scripts
```
as well as the same again for the three replicas of shard2. 

We also defined the network explicitly as a bridge. So still in docker-compose we added driver: bridge in
```
networks:  
  mongo-cluster:
    driver: bridge
```

## 4.3 Initialisation scripts modifications
We updated initiate-shard1.js from: 
```
rs.initiate({
    _id: "shard1ReplSet",
    members: [
        { _id: 0, host: "shard1:27017" }
    ]
});
```
to:
```
rs.initiate({
    _id: "shard1ReplSet",
    members: [
      { _id: 0, host: "shard1a:27017" },
      { _id: 1, host: "shard1b:27017" },
      { _id: 2, host: "shard1c:27017" }
    ]
  })
```
and same for in initiate-shard2.js with shard2a, shard2b and shard2c.

Then we added the new replicas in initiate-shards.js by extending to:
```
sh.addShard("shard1ReplSet/shard1a:27017,shard1b:27017,shard1c:27017");
sh.addShard("shard2ReplSet/shard2a:27017,shard2b:27017,shard2c:27017");
```
## 4.4 Shell script modifications
In setup_mongo_scluster.sh, we updated the data directories from:
```
mkdir -p data/config1 data/config2 data/config3 data/shard1 data/shard2
```
With this updated version that includes all replica members:
```
mkdir -p data/config1 data/config2 data/config3 \
         data/shard1a data/shard1b data/shard1c \
         data/shard2a data/shard2b data/shard2c
```

