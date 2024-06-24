import requests
from sqlalchemy.orm import Session
from .db import engine
from .models import ChunkServer


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

    # if new_index == -1: # Server already exists
    #     chunk_servers.append(new_server)
    #     chunk_servers.sort(key=lambda server: server.id)
    #     new_index = find_server_index(chunk_servers, new_server.id)

    # Replicate data all data from i+1 less the half of the data that he owns
    preceding_1 = chunk_servers[new_index + 1]
    order_send_interval(
        preceding_1,
        new_server,
        chunk_servers[new_index - 3].id,
        chunk_servers[new_index].id,
    )

    # Increase cleanness_need for chunk servers at positions [i+2] and [i+3]
    chunk_servers[(new_index + 2) % len(chunk_servers)].cleanness_need += 1
    chunk_servers[(new_index + 3) % len(chunk_servers)].cleanness_need += 1

    db.commit()


def handle_removed_server(removed_server: ChunkServer, db: Session):
    chunk_servers = get_chunk_server_list(db)
    removed_index = find_server_index(chunk_servers, removed_server.id)

    if removed_index == -1:
        return  # Server not found in the list

    # Order chunk-server[i-2] to provide its interval to the new position
    successor_1 = chunk_servers[(removed_index + 1) % len(chunk_servers)]
    successor_3 = chunk_servers[(removed_index + 3) % len(chunk_servers)]
    predecessor_1 = chunk_servers[(removed_index - 1) % len(chunk_servers)]
    predecessor_2 = chunk_servers[(removed_index - 2) % len(chunk_servers)]
    predecessor_3 = chunk_servers[(removed_index - 3) % len(chunk_servers)]

    order_send_interval(
        successor_1,
        successor_3,
        predecessor_1.id,
        removed_server.id,
    )
    order_send_interval(
        predecessor_2,
        successor_1,
        predecessor_3.id,
        predecessor_2.id,
    )

    # Remove the server from the list
    db.delete(removed_server)

    db.commit()


def order_send_interval(
    source_server: ChunkServer,
    target_server: ChunkServer,
    ini_chunk: int,
    end_chunk: int,
):
    two_intervals = False
    if end_chunk < ini_chunk:
        two_intervals = True
        second_interval_ini = 0
        second_interval_end = ini_chunk
        ini_chunk = end_chunk
        end_chunk = 2**30 - 1

    # Send the interval [ini_chunk, end_chunk] from source_server to target_server
    requests.post(
        f"http://{source_server.host}/send_interval",
        json={
            "target": target_server.host,
            "ini_chunk": ini_chunk,
            "end_chunk": end_chunk,
        },
    )
    if two_intervals:
        requests.post(
            f"http://{source_server.host}/send_interval",
            json={
                "target": target_server.host,
                "ini_chunk": second_interval_ini,
                "end_chunk": second_interval_end,
            },
        )
