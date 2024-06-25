# Start Everything
```
docker-compose up --build
```
User is running on 8010 port

# Start of leader
```
cd leader
docker-compose up --build
```
# Start of chunk servers

```
cd chunk_server
docker build -t chunk_server .
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8100 -p 8100:8100 --name chunk_server_1 chunk_server
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8101 -p 8101:8101 --name chunk_server_2 chunk_server
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8102 -p 8102:8102 --name chunk_server_3 chunk_server
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8103 -p 8103:8103 --name chunk_server_4 chunk_server
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8104 -p 8104:8104 --name chunk_server_5 chunk_server

```
starting 5 of them in this example

# Start of users
```
docker build -t user_app .
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8001 -p 8001:8001 --name user_app_1 user_app
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8002 -p 8002:8002 --name user_app_2 user_app
docker run -d -e LEADER_URL=http://host.docker.internal:8000 -e PORT=8003 -p 8003:8003 --name user_app_3 user_app

```
created 3 users this time


# Project Description

This project implements a distributed file system optimized for handling text documents within a company. The system utilizes FastAPI for its endpoints and Docker to containerize and deploy the Leader (main server), user interface, and chunk servers as distinct machines. Our approach is inspired by Google's GFS but tailored for smaller file sizes and more efficient metadata management.


# Assumptions and Design Choices


In-Company Solution: Given that this system is intended for storing text documents like documentation within a company, we expect to deal with smaller files and do not plan to handle very large files.

Small Chunk Size: We use 1KB chunks to optimize storage for small files and reduce metadata overhead.

Logic Delegation to User: The main logic resides in the User component to leverage horizontal scalability. While the number of users and chunk servers can increase indefinitely, the Leader is not easily scalable (only through expensive hardware upgrades).

For us it is improtant because amount of chunks is huge and if leader will handle all logic itself it will face serious perfomance problems.

We mainly want to have ability to read data fast. Documentation is usually writen once and read many times.

Our system has no updates to have consistency, but we still can delete and upload new files. Expected that people will use versioning for files.

# Architecture


### Key Differences from GFS


- Chunk Size: Our system uses 1KB chunks instead of GFS’s 64MB chunks to handle smaller files.

- Metadata Management: In GFS, metadata per chunk is 64 bytes, which is efficient for 64MB chunks but not for 1KB chunks. Therefore, we store only the mapping of file names to chunks in a database of leader.

## Main Components


### Leader (Main Server):


Role: Acts as the central coordinator managing chunk metadata, hash ring mappings, and chunk server information.

Function: Stores mappings from file names to chunk hashes and positions in a ring. Manages the list of connected chunk servers and their positions on the hash ring.

Metadata Storage: Metadata mapping file names to chunk hashes and ring positions are stored in a database connected to the Leader.


### Chunk Servers:


Data Storage: Store the 1KB data chunks.

Hash Ring Positioning: Positioned on specific values within a hash ring. Store chunks whose hash values fall between their position and the previous server’s position.

Replication: Configurable replication, currently set to replicate data to 2 servers. Positions and other critical information are held in the Leader’s main memory and are backed up in the database to ensure recoverability.

Health Checks: Receive health checks from the Leader every 10 seconds. If a server fails 1-4 checks, it is marked unhealthy. If it fails 5 consecutive checks, it is removed from the list of active chunk servers. This is done by leader. Unhealthy chunk servers attempt to reconnect if they miss health checks.


### User:


Role: Contains the main logic for interacting with the distributed file system, offloading computations from the Leader.

Function: Handles read, write, and delete operations using the chunk metadata provided by the Leader.

Scalability: Can be scaled horizontally to accommodate unlimited users.


## Operations



### Read Data:



#### Process:

- Connection: User connects to the Leader buy adress specified on start.

- Metadata Retrieval: Leader provides chunk hashes, hash ring positions, and the list of chunk servers.

- Server Selection: User identifies the appropriate chunk servers using a hash ring and binary search.

- Batch Requests: User requests chunks in batches rather than individually.

- Redundancy: Attempts to read from the next 3 servers on the hash ring if failed to read from closest to ensure data availability.


Write Data:
Two-Phase Commit Process:

Chunk Preparation: User chunks data into 1KB segments, obtaining their hashes and hash function results.

Pending Data Transmission:

- Step 1: User transmits data to the chunk servers in 'pending' mode.

- Step 2: User sends the name mapping to the Leader (main server) in 'pending' mode.



Persistence Confirmation:

- Step 3: Finalize writes on chunk servers by confirming the data should be saved permanently.

- Step 4: After confirming data persistence on chunk servers, finalize the name mapping on the Leader.


Automatic Cleanup: Any pending writes or name mappings not finalized within 10 minutes are automatically deleted to maintain consistency.

This 2 phase commit process allows us to ensure that:
- 1) Data is not saved if something happend during uploading
- 2) If something goes wrong on finalizing writes, we don't save it in the database and don't save it on leader.
- 3) If something goes wrong on finalizing name mappings, we lose space on chunk servers but we don't save data on leader. It is a trade-off between user expirience and saving space.
- 4) We cant get scenario when user thinks that data is saved but it isn't

Process:

Connection: User connects to the Leader and requests deletion.

Metadata Identification: Leader identifies chunk locations using the hash ring.

Batch Deletion: Sends batch deletion requests to the chunk servers.

Optional Optimization: Consider marking chunks as 'to delete' for deferred deletion to enable faster responses and potential undeletes.






Write Data:



Process:

Chunk Preparation: User chunks data into 1KB segments, obtaining their hashes and hash function results.

Server List Request: Requests the Leader for a list of chunk servers.

Data Transmission: Transmits data to the chunk servers in 'pending' mode.

Replication: Writes to all configured replica servers (currently 2), skipping any servers marked as unhealthy.

Persistence Confirmation: Servers receive a confirmation ping from the Leader to save data permanently. If no confirmation is received within a specified time frame, servers delete the data chunks.
