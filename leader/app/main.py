from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from .db import get_db, Base, engine, init_db
from .models import FileMetadata, ChunkServer
from .schemas import UploadRequest, ChunkServerRegistration
from .background import check_health, handle_new_server

app = FastAPI()


@app.post("/upload")
async def upload_chunks(request: UploadRequest, db: Session = Depends(get_db)):
    metadata = FileMetadata(
        file_id=request.file_id,
        data=[
            {"hash_id": chunk.hash_id, "search_hash": chunk.search_hash}
            for chunk in request.data
        ],
    )
    db.add(metadata)
    db.commit()
    # Distribute chunks to chunk servers (implement the distribution logic here)
    return {"message": "Chunks uploaded successfully"}


@app.post("/register-chunk-server")
async def register_chunk_server(
    server: ChunkServerRegistration, db: Session = Depends(get_db)
):
    chunk_server = ChunkServer(
        id=server.id,
        cleanness_need=server.cleanness_need,
        alive_missed=server.alive_missed,
        host=server.host,
    )
    db.add(chunk_server)
    db.commit()
    # Handle the addition of a new server
    handle_new_server(chunk_server, db)
    return {"message": "Chunk server registered successfully"}


@app.on_event("startup")
async def startup_event():
    init_db()
