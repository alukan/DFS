import os
from typing import Tuple
from sqlalchemy.orm import Session

from .database import ChunkMetadata

BASE_DIR = "chunk_storage"
os.makedirs(BASE_DIR, exist_ok=True)


def save_chunk(file_id: Tuple[str, str], file_data: bytes, db: Session) -> None:
    search_hash, hash_id = file_id
    file_path = os.path.join(BASE_DIR, f"{search_hash}_{hash_id}.bin")
    with open(file_path, "wb") as file:
        file.write(file_data)

    chunk_metadata = ChunkMetadata(search_hash=search_hash, hash_id=hash_id)
    db.add(chunk_metadata)
    db.commit()


def get_chunk(file_id: Tuple[str, str]) -> bytes:
    search_hash, hash_id = file_id
    file_path = os.path.join(BASE_DIR, f"{search_hash}_{hash_id}.bin")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Chunk with ID {file_id} not found.")
    with open(file_path, "rb") as file:
        return file.read()


def remove_chunks_not_in_interval(
    start_search_hash: str, end_search_hash: str, db: Session
) -> int:
    print(start_search_hash, end_search_hash)
    chunks_to_remove = (
        db.query(ChunkMetadata)
        .filter(ChunkMetadata.search_hash < start_search_hash)
        .all()
    )
    chunks_to_remove += (
        db.query(ChunkMetadata)
        .filter(ChunkMetadata.search_hash > end_search_hash)
        .all()
    )
    print(chunks_to_remove)
    removed_files = 0
    for chunk in chunks_to_remove:
        file_path = os.path.join(BASE_DIR, f"{chunk.search_hash}_{chunk.hash_id}.bin")
        if os.path.exists(file_path):
            os.remove(file_path)
            removed_files += 1
        db.delete(chunk)
    db.commit()
    return removed_files
