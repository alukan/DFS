from fastapi import APIRouter, HTTPException, Query
import requests
import os
from typing import List, Dict

router = APIRouter()

@router.get("/namemappings/{full_path:path}", response_model=Dict)
async def get_name_mapping(full_path: str):
    response = requests.get(f"{os.getenv('LEADER_URL')}/namemappings/{full_path}")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Error getting name mapping")

@router.put("/namemappings/")
async def rename_name_mapping(
    old_path: str = Query(..., description="The current full path of the name mapping"),
    new_path: str = Query(..., description="The new full path of the name mapping")
):
    params = {'old_path': old_path, 'new_path': new_path}
    response = requests.put(f"{os.getenv('LEADER_URL')}/namemappings/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status, detail="Error renaming name mapping")

@router.get("/listfiles/")
async def list_files_in_folder(folder_path: str = Query(..., description="The path of the folder to list files from")):
    params = {'folder_path': folder_path}
    response = requests.get(f"{os.getenv('LEADER_URL')}/listfiles/", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status, detail="Error listing files")
