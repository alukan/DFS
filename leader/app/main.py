from fastapi import FastAPI, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Tuple
import hashlib
import requests
import asyncio
import os

from . import crud, models, schemas
from .db import get_db

app = FastAPI()

# Initialize the list of chunk servers
chunk_servers = []
@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    # Fetch chunk servers from the database
    global chunk_servers
    chunk_servers = crud.get_chunk_servers(db)
    asyncio.create_task(health_check())

@app.post("/register_chunk_server/")
def register_chunk_server(url: str, db: Session = Depends(get_db)):
    # Check for duplicates
    for server in chunk_servers:
        if server.url == url:
            return {"message": "Chunk server already registered", "url": url, "position": server["position"]}

    position = str(int(hashlib.md5(url.encode('utf-8')).hexdigest(), 16))  # Convert to string
    chunk_server = models.ChunkServer(url=url, position=position, fail_count=0)
    chunk_servers.append(chunk_server)
    chunk_servers.sort(key=lambda x: x.position)
    crud.create_chunk_server(db, chunk_server)

    return {"message": "Chunk server registered successfully", "url": url, "position": position}

@app.get("/chunk_servers/")
def get_chunk_servers():
    return [{"url": server.url, "position": server.position, "fail_count": server.fail_count} for server in chunk_servers]

@app.post("/namemappings/", response_model=schemas.NameMapping)
def create_name_mapping(name_mapping: schemas.NameMappingCreate, db: Session = Depends(get_db)):
    try:
        db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken")

@app.get("/namemappings/{full_path:path}", response_model=schemas.NameMapping)
def get_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    db_name_mapping = crud.get_name_mapping(db=db, name=full_path)
    if db_name_mapping is None:
        raise HTTPException(status_code=404, detail="Name not found")
    return db_name_mapping

@app.put("/namemappings/")
def rename_name_mapping(
    old_path: str = Query(..., description="The current full path of the name mapping"),
    new_path: str = Query(..., description="The new full path of the name mapping"),
    db: Session = Depends(get_db)
):
    try:
        db_name_mapping = crud.rename_name_mapping(db=db, old_name=old_path, new_name=new_path)
        if db_name_mapping is None:
            raise HTTPException(status_code=404, detail="Name not found")
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="New name already taken")

@app.delete("/namemappings/{full_path:path}")
def delete_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    success = crud.delete_name_mapping(db=db, name=full_path)
    if not success:
        raise HTTPException(status_code=404, detail="Name not found")
    return {"message": "Name deleted successfully"}

@app.get("/listfiles/", response_model=List[schemas.NameMapping])
def list_files_in_folder(
    folder_path: str = Query(..., description="The path of the folder to list files from"),
    db: Session = Depends(get_db)
):
    files = crud.list_files_in_folder(db=db, folder_path=folder_path)
    if not files:
        raise HTTPException(status_code=404, detail="No files found in the specified folder")
    return files

async def health_check():
    while True:
        for server in chunk_servers:
            try:
                response = requests.get(f"{server.url}/health_check")
                if response.status_code == 200:
                    server.fail_count = 0
                else:
                    server.fail_count += 1
            except requests.exceptions.RequestException:
                server.fail_count += 1

            
                db = next(get_db())
                crud.update_chunk_server_fail_count(db, server.url, server.fail_count)

                if server.fail_count >= 5:
                    chunk_servers.remove(server)
                    crud.delete_chunk_server(db, server.url)
                    print(f"Removed chunk server: {server.url} due to failed health checks.")
        
        await asyncio.sleep(10)


