from fastapi import FastAPI, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from . import crud, models, schemas
from .db import get_db
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/namemappings/", response_model=schemas.NameMapping)
def create_name_mapping(name_mapping: schemas.NameMappingCreate, db: Session = Depends(get_db)):
    try:
        db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken")

@app.delete("/namemappings/{full_path:path}")
def delete_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    success = crud.delete_name_mapping(db=db, name=full_path)
    if not success:
        raise HTTPException(status_code=404, detail="Name not found")
    return {"message": "Name deleted successfully"}

@app.get("/namemappings/{full_path:path}", response_model=schemas.NameMapping)
def get_name_mapping(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    db_name_mapping = crud.get_name_mapping(db=db, name=full_path)
    if db_name_mapping is None:
        raise HTTPException(status_code=404, detail="Name not found")
    return db_name_mapping

@app.put("/namemappings/", response_model=schemas.NameMapping)
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

@app.get("/listfiles/", response_model=List[schemas.NameMapping])
def list_files_in_folder(
    folder_path: str = Query(..., description="The path of the folder to list files from"),
    db: Session = Depends(get_db)
):
    files = crud.list_files_in_folder(db=db, folder_path=folder_path)
    if not files:
        raise HTTPException(status_code=404, detail="No files found in the specified folder")
    return files
