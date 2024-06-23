import requests
import os
from fastapi import HTTPException

def get_leader_chunk_servers():
    response = requests.get(f"{os.getenv('LEADER_URL')}/chunk_servers/")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error getting chunk servers")
    return response.json()
