from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
from app import crud, schemas
from app.db import get_db
from datetime import datetime, timedelta
import asyncio


router = APIRouter()


temporary_name_mappings = {}

@router.post("/temp_namemappings/")
def create_temp_name_mapping(name_mapping: schemas.NameMappingCreate):
    temporary_name_mappings[name_mapping.full_path] = {
        "name_mapping": name_mapping,
        "timestamp": datetime.now()
    }
    return name_mapping

@router.post("/finalize_namemappings/")
def finalize_name_mapping(full_path: str = Query(..., description="The full path of the name mapping"),
                          db: Session = Depends(get_db)):
    if full_path not in temporary_name_mappings:
        raise HTTPException(status_code=404, detail="Temporary name mapping not found")

    name_mapping_data = temporary_name_mappings.pop(full_path)
    name_mapping = name_mapping_data["name_mapping"]
    try:
        db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken")
    

@router.post("/namemappings/", response_model=schemas.NameMapping)
def create_name_mapping(name_mapping: schemas.NameMappingCreate, db: Session = Depends(get_db)):
    try:
        db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken")

@router.get("/namemappings/{full_path:path}", response_model=schemas.NameMapping)
def get_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    db_name_mapping = crud.get_name_mapping(db=db, name=full_path)
    if db_name_mapping is None:
        raise HTTPException(status_code=404, detail="Name not found")
    return db_name_mapping

@router.put("/namemappings/")
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

@router.delete("/namemappings/{full_path:path}")
def delete_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    success = crud.delete_name_mapping(db=db, name=full_path)
    if not success:
        raise HTTPException(status_code=404, detail="Name not found")
    return {"message": "Name deleted successfully"}

@router.get("/listfiles/", response_model=List[str])
def list_files_in_folder(
    folder_path: str = Query(..., description="The path of the folder to list files from"),
    db: Session = Depends(get_db)
):
    files = crud.list_files_in_folder(db=db, folder_path=folder_path)
    if not files:
        raise HTTPException(status_code=404, detail="No files found in the specified folder")
    return [file.full_path for file in files]


async def clean_old_temp_mappings():
    while True:
        await asyncio.sleep(600) #10 mins
        now = datetime.now()
        keys_to_delete = []
        for key, value in temporary_name_mappings.items():
            if now - value["timestamp"] > timedelta(minutes=10):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del temporary_name_mappings[key]

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(clean_old_temp_mappings())