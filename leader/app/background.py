from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from db import get_db, engine
from models import ChunkServer
from sqlalchemy.orm import Session


def check_health():
    db = Session(bind=engine)
    chunk_servers = db.query(ChunkServer).all()
    for server in chunk_servers:
        if not server.alive:
            server.alive_missed += 1
            if server.alive_missed >= 3:
                handle_removed_server(server, db)
        db.commit()


def get_chunk_server_list(db: Session):
    return db.query(ChunkServer).order_by(ChunkServer.id).all()


def find_server_index(servers, server_id):
    for index, server in enumerate(servers):
        if server.id == server_id:
            return index
    return -1


def handle_new_server(new_server: ChunkServer, db: Session):
    chunk_servers = get_chunk_server_list(db)
    new_index = find_server_index(chunk_servers, new_server.id)

    if new_index == -1:
        chunk_servers.append(new_server)
        chunk_servers.sort(key=lambda server: server.id)
        new_index = find_server_index(chunk_servers, new_server.id)

    # Replicate data from two preceding chunk servers
    preceding_1 = chunk_servers[new_index - 1]
    preceding_2 = chunk_servers[new_index - 2]
    replicate_data(preceding_1, new_server)
    replicate_data(preceding_2, new_server)

    # Provide half of the data from the succeeding chunk server
    succeeding = chunk_servers[(new_index + 1) % len(chunk_servers)]
    provide_half_data(succeeding, new_server)

    # Increase cleanense_need for chunk servers at positions [i+2] and [i+3]
    chunk_servers[(new_index + 2) % len(chunk_servers)].cleanense_need += 1
    chunk_servers[(new_index + 3) % len(chunk_servers)].cleanense_need += 1

    db.commit()


def handle_removed_server(removed_server: ChunkServer, db: Session):
    chunk_servers = get_chunk_server_list(db)
    removed_index = find_server_index(chunk_servers, removed_server.id)

    if removed_index == -1:
        return  # Server not found in the list

    # Remove the server from the list
    chunk_servers.pop(removed_index)

    # Order chunk-server[i-2] to provide its interval to the new position
    preceding_2 = chunk_servers[(removed_index - 2) % len(chunk_servers)]
    new_position = chunk_servers[removed_index % len(chunk_servers)]
    provide_interval(preceding_2, new_position)

    # Order chunk-server[i+1] to send the interval of the removed server to chunk-server[i+3]
    succeeding_1 = chunk_servers[removed_index % len(chunk_servers)]
    succeeding_3 = chunk_servers[(removed_index + 2) % len(chunk_servers)]
    send_interval(succeeding_1, succeeding_3)

    db.commit()


def replicate_data(source_server: ChunkServer, target_server: ChunkServer):
    # Logic to replicate data from source_server to target_server
    pass


def provide_half_data(source_server: ChunkServer, target_server: ChunkServer):
    # Logic to provide half of the data from source_server to target_server
    pass


def provide_interval(source_server: ChunkServer, target_server: ChunkServer):
    # Logic to provide the interval data from source_server to target_server
    pass


def send_interval(source_server: ChunkServer, target_server: ChunkServer):
    # Logic to send the interval data from source_server to target_server
    pass
