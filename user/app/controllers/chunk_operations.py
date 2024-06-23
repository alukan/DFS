from fastapi import APIRouter, HTTPException, Query
import requests
import os
import aiohttp
from app.utils.chunk_utils import get_chunk_server_positions, fetch_chunk_with_retries, delete_chunks_from_servers

router = APIRouter()

@router.get("/readfile/")
async def read_file_by_name(
    full_path: str = Query(..., description="The full path of the file to read"),
    save_as: str = Query(None, description="The name of the file to save the text as")
):
    # Get chunk information from the leader
    response = requests.get(f"{os.getenv('LEADER_URL')}/namemappings/{full_path}")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching file info")

    file_info = response.json()
    chunk_hashes = file_info['chunk_hashes']

    # Get the list of chunk servers
    chunk_servers = requests.get(f"{os.getenv('LEADER_URL')}/chunk_servers/").json()

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

@router.delete("/namemappings/{full_path:path}")
async def delete_name_mapping(full_path: str):
    # Get chunk information from the leader
    response = requests.get(f"{os.getenv('LEADER_URL')}/namemappings/{full_path}")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching file info")

    file_info = response.json()
    chunk_hashes = file_info['chunk_hashes']

    # Get the list of chunk servers
    chunk_servers = requests.get(f"{os.getenv('LEADER_URL')}/chunk_servers/").json()

    # Delete chunks from the servers
    async with aiohttp.ClientSession() as session:
        await delete_chunks_from_servers(session, chunk_servers, chunk_hashes)

    # Delete the name mapping from the leader
    response = requests.delete(f"{os.getenv('LEADER_URL')}/namemappings/{full_path}")
    if response.status_code == 200:
        return {"message": "Name and associated chunks deleted successfully"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Error deleting name mapping")
