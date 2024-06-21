from sqlalchemy.orm import Session
from . import models, schemas

def create_name_mapping(db: Session, name_mapping: schemas.NameMappingCreate):
    db_name_mapping = models.NameMapping(name=name_mapping.name, chunks=name_mapping.chunks)
    db.add(db_name_mapping)
    db.commit()
    db.refresh(db_name_mapping)
    return db_name_mapping


def delete_name_mapping(db: Session, name: str):
    db_name_mapping = db.query(models.NameMapping).filter(models.NameMapping.name == name).first()
    if db_name_mapping:
        db.delete(db_name_mapping)
        db.commit()
        return True
    return False

def get_name_mapping(db: Session, name: str):
    return db.query(models.NameMapping).filter(models.NameMapping.name == name).first()
