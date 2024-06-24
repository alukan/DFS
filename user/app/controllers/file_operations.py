from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from collections import defaultdict
from typing import List, Dict
import os
import aiohttp
from aiohttp import FormData
from app.utils.chunk_utils import hash_chunk, get_chunk_server_positions
from app.utils.leader_utils import get_leader_chunk_servers
import requests
import hashlib

router = APIRouter()

CHUNK_SIZE = 1024
MAX_CHUNKS_PER_REQUEST = 2000

@router.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), name: str = Form(...), path: str = Form(...)):
    file_location = f"/tmp/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    file_size = os.path.getsize(file_location)

    # Get the list of chunk servers from the leader
    chunk_servers = get_leader_chunk_servers()

    chunk_hashes = []
    chunk_positions = []
    server_chunks = defaultdict(list)
    
    with open(file_location, 'rb') as f:
        while chunk := f.read(CHUNK_SIZE):
            chunk_hash = hash_chunk(chunk)
            position = str(int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16))
            chunk_hashes.append(chunk_hash)
            chunk_positions.append((chunk_hash, position))

            servers = get_chunk_server_positions(chunk_hash, chunk_servers)
            for server in servers:
                server_chunks[server['url']].append((chunk, chunk_hash))

    async with aiohttp.ClientSession() as session:
        for server_url, chunks in server_chunks.items():
            for i in range(0, len(chunks), MAX_CHUNKS_PER_REQUEST):
                batch_chunks = chunks[i:i + MAX_CHUNKS_PER_REQUEST]
                url = f"{server_url}/store_chunks_pending/"
                data = [
                    {"data": chunk.decode('utf-8'), "chunk_hash": chunk_hash} for chunk, chunk_hash in batch_chunks
                ]
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to store chunks on server {server_url}, status code: {response.status}")


    # Notify the leader about the new file and its chunks as temporary
    name_mapping = {"full_path": os.path.join(path, name), "chunk_hashes": chunk_positions, "size": file_size}
    response = requests.post(f"{os.getenv('LEADER_URL')}/temp_namemappings/", json=name_mapping)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error creating temporary name mapping")

    # Finalize chunks on the servers
    async with aiohttp.ClientSession() as session:
        for chunk_hash, position in chunk_positions:
            servers = get_chunk_server_positions(chunk_hash, chunk_servers)
            for server in servers:
                url = f"{server['url']}/finalize_chunks/"
                async with session.post(url, json={"chunks": [chunk_hash]}) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail=f"Failed to finalize chunk on server {server['url']}")

    # Finalize name mapping on the leader
    response = requests.post(f"{os.getenv('LEADER_URL')}/finalize_namemappings/", params={"full_path": os.path.join(path, name)})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error finalizing name mapping")

    os.remove(file_location)  # Cleanup the temporary file
    return {"message": "File uploaded and processed successfully"}

@router.get("/filesize/")
async def get_file_size(full_path: str = Query(..., description="The full path of the file to get the size of")):
    # Get the file size from the leader
    response = requests.get(f"{os.getenv('LEADER_URL')}/file/{full_path}/size")
    if response.status_code == 200:
        return {"file_size": str(response.json()) + " bytes"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Error fetching file size")
