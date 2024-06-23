from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas

def create_name_mapping(db: Session, name_mapping: schemas.NameMappingCreate):
    db_name_mapping = models.NameMapping(
        full_path=name_mapping.full_path,
        chunk_hashes=name_mapping.chunk_hashes
    )
    db.add(db_name_mapping)
    db.commit()
    db.refresh(db_name_mapping)
    return db_name_mapping

def get_name_mapping(db: Session, name: str):
    return db.query(models.NameMapping).filter(models.NameMapping.full_path == name).first()

def delete_name_mapping(db: Session, name: str):
    db_name_mapping = db.query(models.NameMapping).filter(models.NameMapping.full_path == name).first()
    if db_name_mapping:
        db.delete(db_name_mapping)
        db.commit()
        return True
    return False

def rename_name_mapping(db: Session, old_name: str, new_name: str):
    db_name_mapping = db.query(models.NameMapping).filter(models.NameMapping.full_path == old_name).first()
    if db_name_mapping:
        db_name_mapping.full_path = new_name
        db.commit()
        db.refresh(db_name_mapping)
        return db_name_mapping
    return None

def list_files_in_folder(db: Session, folder_path: str):
    if not folder_path.endswith('/'):
        folder_path += '/'
    files = db.query(models.NameMapping).filter(models.NameMapping.full_path.like(f'{folder_path}%')).all()
    return files
