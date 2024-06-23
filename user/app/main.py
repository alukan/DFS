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
AMOUNT_OF_REPLICAS = 3

def hash_chunk(chunk):
    return hashlib.md5(chunk).hexdigest()

def get_chunk_server_positions(chunk_hash, chunk_servers):
    position = int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16)
    idx = bisect.bisect([int(server['position']) for server in chunk_servers], int(position))
    # Return the next AMOUNT_OF_REPLICAS active servers in the ring
    servers = []
    for i in range(len(chunk_servers)):
        server = chunk_servers[(idx + i) % len(chunk_servers)]
        if server['fail_count'] == 0:
            servers.append(server)
        if len(servers) == AMOUNT_OF_REPLICAS:
            break
    return servers

async def fetch_chunk_with_retries(session, chunk_servers, chunk_hash):
    for server in chunk_servers[:AMOUNT_OF_REPLICAS]:
        try:
            url = f"{server['url']}/get_chunk"
            async with session.get(url, params={"chunk_hash": chunk_hash}) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as e:
            continue
    raise HTTPException(status_code=404, detail=f"Chunk {chunk_hash} not found on any server")

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

    file_size = os.path.getsize(file_location)

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
            servers = get_chunk_server_positions(chunk_hash, chunk_servers)
            for server in servers:
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
    name_mapping = {"full_path": os.path.join(path, name), "chunk_hashes": chunk_positions, "size": file_size}
    response = requests.post(f"{LEADER_URL}/namemappings/", json=name_mapping)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error creating name mapping")

    # Finalize chunks on the servers
    async with aiohttp.ClientSession() as session:
        for chunk_hash, position in chunk_positions:
            servers = get_chunk_server_positions(chunk_hash, chunk_servers)
            for server in servers:
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


async def delete_chunks_from_servers(session, chunk_servers, chunk_hashes):
    for chunk_hash in chunk_hashes:
        servers = get_chunk_server_positions(chunk_hash[0], chunk_servers)
        for server in servers:
            url = f"{server['url']}/delete_chunks/"
            async with session.post(url, json={"chunks": [chunk_hash[0]]}) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail=f"Failed to delete chunk {chunk_hash[0]} on server {server['url']}")


@app.delete("/namemappings/{full_path:path}")
async def delete_name_mapping(full_path: str):
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

    # Delete chunks from the servers
    async with aiohttp.ClientSession() as session:
        await delete_chunks_from_servers(session, chunk_servers, chunk_hashes)

    # Delete the name mapping from the leader
    response = requests.delete(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return {"message": "Name and associated chunks deleted successfully"}
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
async def read_file_by_name(
    full_path: str = Query(..., description="The full path of the file to read"),
    save_as: str = Query(None, description="The name of the file to save the text as")
):
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
    file_data = bytearray()
    async with aiohttp.ClientSession() as session:
        for chunk_hash, position in chunk_hashes:
            servers = get_chunk_server_positions(chunk_hash, chunk_servers)
            chunk_data = await fetch_chunk_with_retries(session, servers, chunk_hash)
            file_data.extend(chunk_data)


    file_text = file_data.decode('utf-8')

    if save_as:
        # Save to file
        save_path = f"/tmp/{save_as}"
        with open(save_path, 'w') as f:
            f.write(file_text)
        return {"file_data": file_text, "saved_as": save_path}
    
    return {"file_data": file_text}

@app.get("/filesize/")
async def get_file_size(full_path: str = Query(..., description="The full path of the file to get the size of")):
    # Get the file size from the leader
    response = requests.get(f"{LEADER_URL}/file/{full_path}/size")
    if response.status_code == 200:
        return {"file_size": str(response.json()) + " bytes"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Error fetching file size")

# Run the user FastAPI app on the specified port
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
