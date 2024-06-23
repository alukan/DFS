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
created 3 this time