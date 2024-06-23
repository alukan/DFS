from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app import crud
from app.db import get_db

router = APIRouter()

@router.get("/file/{full_path:path}/size", response_model=int)
def get_file_size(
    full_path: str = Path(..., description="The full path of the name mapping"),
    db: Session = Depends(get_db)
):
    db_name_mapping = crud.get_name_mapping(db=db, name=full_path)
    if db_name_mapping is None:
        raise HTTPException(status_code=404, detail="Name not found")
    return db_name_mapping.size
