from fastapi import FastAPI, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import crud, models, schemas
from .db import get_db

app = FastAPI()

@app.post("/namemappings/", response_model=schemas.NameMapping)
def create_name_mapping(name_mapping: schemas.NameMappingCreate, db: Session = Depends(get_db)):
    try:
        db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
        return db_name_mapping
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken")
    
    name_mapping.name = name_mapping
    db_name_mapping = crud.create_name_mapping(db=db, name_mapping=name_mapping)
    return db_name_mapping

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