from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from typing import List, Dict, Tuple
import requests
import os
import hashlib
import bisect
import aiohttp
from aiohttp import FormData
import asyncio

app = FastAPI()

LEADER_URL = os.getenv("LEADER_URL", "http://host.docker.internal:8000")
CHUNK_SIZE = 1024

def hash_chunk(chunk):
    return hashlib.md5(chunk).hexdigest()

def get_chunk_server_position(chunk_hash, chunk_servers):
    position = int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16)
    idx = bisect.bisect([int(server['position']) for server in chunk_servers], int(position))
    return chunk_servers[idx % len(chunk_servers)]

async def fetch_chunk(session, url, chunk_hash):
    async with session.get(url, params={"chunk_hash": chunk_hash}) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise HTTPException(status_code=response.status, detail=f"Error fetching chunk {chunk_hash}")

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), name: str = Form(...), path: str = Form(...)):
    file_location = f"/tmp/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    chunk_hashes = []
    chunk_positions = []
    with open(file_location, 'rb') as f:
        while chunk := f.read(CHUNK_SIZE):
            chunk_hash = hash_chunk(chunk)
            position = str(int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16))
            chunk_hashes.append(chunk_hash)
            chunk_positions.append((chunk_hash, position))

    # Get the list of chunk servers from the leader
    response = requests.get(f"{LEADER_URL}/chunk_servers/")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error getting chunk servers")

    chunk_servers = response.json()

    if not chunk_servers:
        raise HTTPException(status_code=503, detail="No chunk servers are currently connected. Please try again later.")

    # Send chunks to the appropriate servers (pending)
    async with aiohttp.ClientSession() as session:
        for chunk_hash, position in chunk_positions:
            server = get_chunk_server_position(chunk_hash, chunk_servers)
            url = f"{server['url']}/store_chunks_pending/"
            with open(file_location, 'rb') as f:
                while chunk := f.read(CHUNK_SIZE):
                    current_chunk_hash = hash_chunk(chunk)
                    if current_chunk_hash == chunk_hash:
                        data = FormData()
                        data.add_field('file', chunk, filename=chunk_hash)
                        data.add_field('chunk_hash', chunk_hash)
                        async with session.post(url, data=data) as response:
                            if response.status != 200:
                                raise HTTPException(status_code=response.status, detail=f"Failed to store chunk on server {server['url']}")

    # Notify the leader about the new file and its chunks
    name_mapping = {"full_path": os.path.join(path, name), "chunk_hashes": chunk_positions}
    response = requests.post(f"{LEADER_URL}/namemappings/", json=name_mapping)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error creating name mapping")

    # Finalize chunks on the servers
    async with aiohttp.ClientSession() as session:
        for chunk_hash, position in chunk_positions:
            server = get_chunk_server_position(chunk_hash, chunk_servers)
            url = f"{server['url']}/finalize_chunks/"
            async with session.post(url, json={"chunks": [chunk_hash]}) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail=f"Failed to finalize chunk on server {server['url']}")

    os.remove(file_location)  # Cleanup the temporary file
    return {"message": "File uploaded and processed successfully"}

@app.get("/namemappings/{full_path:path}", response_model=Dict)
async def get_name_mapping(full_path: str):
    response = requests.get(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Error getting name mapping")

@app.delete("/namemappings/{full_path:path}")
async def delete_name_mapping(full_path: str):
    response = requests.delete(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return {"message": "Name deleted successfully"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Error deleting name mapping")

@app.put("/namemappings/")
async def rename_name_mapping(
    old_path: str = Query(..., description="The current full path of the name mapping"),
    new_path: str = Query(..., description="The new full path of the name mapping")
):
    params = {'old_path': old_path, 'new_path': new_path}
    response = requests.put(f"{LEADER_URL}/namemappings/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status, detail="Error renaming name mapping")

@app.get("/listfiles/", response_model=List[Dict])
async def list_files_in_folder(folder_path: str = Query(..., description="The path of the folder to list files from")):
    params = {'folder_path': folder_path}
    response = requests.get(f"{LEADER_URL}/listfiles/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status, detail="Error listing files")

@app.get("/readfile/")
async def read_file_by_name(full_path: str = Query(..., description="The full path of the file to read")):
    # Get chunk information from the leader
    response = requests.get(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching file info")

    file_info = response.json()
    chunk_hashes = file_info['chunk_hashes']

    # Get the list of chunk servers
    response = requests.get(f"{LEADER_URL}/chunk_servers/")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching chunk servers info")

    chunk_servers = response.json()

    # Organize chunks by server
    server_chunks = {}
    for chunk_hash, position in chunk_hashes:
        server = get_chunk_server_position(chunk_hash, chunk_servers)
        if server['url'] not in server_chunks:
            server_chunks[server['url']] = []
        server_chunks[server['url']].append(chunk_hash)

    # Fetch chunks from servers
    file_data = bytearray()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for server_url, chunks in server_chunks.items():
            for chunk_hash in chunks:
                tasks.append(fetch_chunk(session, f"{server_url}/get_chunk", chunk_hash))
        
        results = await asyncio.gather(*tasks)
        for chunk_data in results:
            file_data.extend(chunk_data)

    return {"file_data": file_data.decode('utf-8')}

# Run the user FastAPI app on the specified port
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
