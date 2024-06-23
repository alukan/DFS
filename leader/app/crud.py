from sqlalchemy.orm import Session
from . import models, schemas

def get_chunk_servers(db: Session):
    return db.query(models.ChunkServer).all()

def create_chunk_server(db: Session, chunk_server: models.ChunkServer):
    db.add(chunk_server)
    db.commit()
    db.refresh(chunk_server)
    return chunk_server

def update_chunk_server_fail_count(db: Session, url: str, fail_count: int):
    chunk_server = db.query(models.ChunkServer).filter(models.ChunkServer.url == url).first()
    if chunk_server:
        chunk_server.fail_count = fail_count
        db.commit()
    return chunk_server

def delete_chunk_server(db: Session, url: str):
    chunk_server = db.query(models.ChunkServer).filter(models.ChunkServer.url == url).first()
    if chunk_server:
        db.delete(chunk_server)
        db.commit()
    return chunk_server

def get_name_mapping(db: Session, name: str):
    return db.query(models.NameMapping).filter(models.NameMapping.full_path == name).first()

def create_name_mapping(db: Session, name_mapping: schemas.NameMappingCreate):
    db_name_mapping = models.NameMapping(
        full_path=name_mapping.full_path, 
        chunk_hashes=name_mapping.chunk_hashes
    )
    db.add(db_name_mapping)
    db.commit()
    db.refresh(db_name_mapping)
    return db_name_mapping

def rename_name_mapping(db: Session, old_name: str, new_name: str):
    db_name_mapping = db.query(models.NameMapping).filter(models.NameMapping.full_path == old_name).first()
    if db_name_mapping:
        db_name_mapping.full_path = new_name
        db.commit()
        db.refresh(db_name_mapping)
    return db_name_mapping

def delete_name_mapping(db: Session, name: str):
    db_name_mapping = db.query(models.NameMapping).filter(models.NameMapping.full_path == name).first()
    if db_name_mapping:
        db.delete(db_name_mapping)
        db.commit()
        return True
    return False

def list_files_in_folder(db: Session, folder_path: str):
    return db.query(models.NameMapping).filter(models.NameMapping.full_path.like(f"{folder_path}%")).all()
