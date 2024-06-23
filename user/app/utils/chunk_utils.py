import hashlib
import bisect
from fastapi import HTTPException

def hash_chunk(chunk):
    return hashlib.md5(chunk).hexdigest()

def get_chunk_server_positions(chunk_hash, chunk_servers):
    position = int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16)
    idx = bisect.bisect([int(server['position']) for server in chunk_servers], int(position))
    servers = []
    for i in range(len(chunk_servers)):
        server = chunk_servers[(idx + i) % len(chunk_servers)]
        if server['fail_count'] == 0:
            servers.append(server)
        if len(servers) == 3:
            break
    return servers

async def fetch_chunk_with_retries(session, chunk_servers, chunk_hash):
    for server in chunk_servers[:3]:
        try:
            url = f"{server['url']}/get_chunk"
            async with session.get(url, params={"chunk_hash": chunk_hash}) as response:
                if response.status == 200:
                    return await response.read()
        except Exception:
            continue
    raise HTTPException(status_code=404, detail=f"Chunk {chunk_hash} not found on any server")

async def delete_chunks_from_servers(session, chunk_servers, chunk_hashes):
    for chunk_hash in chunk_hashes:
        servers = get_chunk_server_positions(chunk_hash[0], chunk_servers)
        for server in servers:
            url = f"{server['url']}/delete_chunks/"
            async with session.post(url, json={"chunks": [chunk_hash[0]]}) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail=f"Failed to delete chunk {chunk_hash[0]} on server {server['url']}")
