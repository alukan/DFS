from fastapi import FastAPI, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
import hashlib
from . import crud, models, schemas
from .db import get_db

app = FastAPI()

# Initialize the list of chunk servers
chunk_servers = []

@app.post("/register_chunk_server/")
def register_chunk_server(url: str, db: Session = Depends(get_db)):
    position = int(hashlib.md5(url.encode('utf-8')).hexdigest(), 16)
    chunk_servers.append({"url": url, "position": position})
    chunk_servers.sort(key=lambda x: x['position'])
    return {"message": "Chunk server registered successfully", "url": url, "position": position}

@app.get("/chunk_servers/")
def get_chunk_servers():
    return chunk_servers

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
