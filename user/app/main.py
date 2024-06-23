from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from typing import List, Dict, Tuple
import hashlib
import requests
import os
import bisect
import logging

app = FastAPI()

LEADER_URL = os.getenv("LEADER_URL", "http://localhost:8000")
CHUNK_SIZE = 1024

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chunk_file(file_path, chunk_size=CHUNK_SIZE):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk

def hash_chunk(chunk):
    return hashlib.md5(chunk).hexdigest()

def get_chunk_server(chunk_hash, chunk_servers):
    position = int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16)
    idx = bisect.bisect([int(server['position']) for server in chunk_servers], int(position))
    return chunk_servers[idx % len(chunk_servers)]

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), name: str = Form(...), path: str = Form(...)):
    file_location = f"/tmp/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    chunk_hashes = []
    chunk_positions = []
    for chunk in chunk_file(file_location):
        chunk_hash = hash_chunk(chunk)
        position = str(int(hashlib.md5(chunk_hash.encode('utf-8')).hexdigest(), 16))  # Convert to string
        chunk_hashes.append(chunk_hash)
        chunk_positions.append((chunk_hash, position))

    # Get the list of chunk servers from the leader
    response = requests.get(f"{LEADER_URL}/chunk_servers/")
    if response.status_code != 200:
        logger.error(f"Error getting chunk servers: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error getting chunk servers")

    chunk_servers = response.json()

    if not chunk_servers:
        raise HTTPException(status_code=503, detail="No chunk servers are currently connected. Please try again later.")

    # Notify the leader about the new file and its chunks
    name_mapping = {"full_path": os.path.join(path, name), "chunk_hashes": chunk_positions}
    response = requests.post(f"{LEADER_URL}/namemappings/", json=name_mapping)

    if response.status_code != 200:
        logger.error(f"Error creating name mapping: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error creating name mapping")

    # Send chunks to the appropriate servers
    for chunk_hash, position in chunk_positions:
        server = get_chunk_server(chunk_hash, chunk_servers)
        with open(file_location, 'rb') as f:
            for chunk in chunk_file(file_location):
                current_chunk_hash = hash_chunk(chunk)
                if current_chunk_hash == chunk_hash:
                    files = {'file': chunk}
                    response = requests.post(f"{server['url']}/store_chunks_pending/", files=files, data={'chunk_hash': chunk_hash})
                    if response.status_code != 200:
                        logger.error(f"Error storing chunk on server {server['url']}: {response.text}")
                        raise HTTPException(status_code=response.status_code, detail=f"Failed to store chunk on server {server['url']}")
                    break

    os.remove(file_location)  # Cleanup the temporary file
    return {"message": "File uploaded and processed successfully"}

@app.get("/namemappings/{full_path:path}", response_model=Dict)
async def get_name_mapping(full_path: str):
    response = requests.get(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error getting name mapping: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error getting name mapping")

@app.delete("/namemappings/{full_path:path}")
async def delete_name_mapping(full_path: str):
    response = requests.delete(f"{LEADER_URL}/namemappings/{full_path}")
    if response.status_code == 200:
        return {"message": "Name deleted successfully"}
    else:
        logger.error(f"Error deleting name mapping: {response.text}")
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
        logger.error(f"Error renaming name mapping: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error renaming name mapping")

@app.get("/listfiles/", response_model=List[Dict])
async def list_files_in_folder(folder_path: str = Query(..., description="The path of the folder to list files from")):
    params = {'folder_path': folder_path}
    response = requests.get(f"{LEADER_URL}/listfiles/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error listing files: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error listing files")

# Run the user FastAPI app on the specified port
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
