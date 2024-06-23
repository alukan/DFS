import base64
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
import os
from .files import save_chunk, get_chunk, remove_chunks_not_in_interval
from .schemas import (
    GetChunkResponse,
    GetChunksRequest,
    GetChunksResponse,
    SaveFileRequest,
    FileId,
    RemoveFilesRequest,
)
from .database import SessionLocal, init_db
import requests
import logging

app = FastAPI()


def bytes_to_base64(data: bytes) -> str:
    return jsonable_encoder(
        data, custom_encoder={bytes: lambda v: base64.b64encode(v).decode("utf-8")}
    )


SERVER_ID = os.getenv("SERVER_ID", "1")
LEADER_URL = os.getenv("LEADER_URL", "http://localhost:8000")
logger = logging.getLogger(__name__)


def register_to_leader():
    response = requests.post(
        f"{LEADER_URL}/register_chunk_server",
        json={"server_id": SERVER_ID},
        timeout=2,
    )
    logger.info(response.json())


@app.on_event("startup")
def on_startup():
    init_db()
    register_to_leader()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/save_chunk")
async def save_chunk_endpoint(request: SaveFileRequest, db: Session = Depends(get_db)):
    file_id = (request.file_id.search_hash, request.file_id.hash_id)
    try:
        save_chunk(file_id, request.file_data, db)
        return {"message": "Chunk saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_chunk", response_model=GetChunkResponse)
async def get_chunk_endpoint(file_id: FileId):
    file_id_tuple = (file_id.search_hash, file_id.hash_id)
    print(file_id_tuple)
    try:
        chunk_data = get_chunk(file_id_tuple)
        print(chunk_data)
        return {"file_id": file_id, "file_data": bytes_to_base64(chunk_data)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chunk not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_chunks")
async def get_chunks_endpoint(request: GetChunksRequest) -> GetChunksResponse:
    chunks_data = []
    for file_id in request.files_ids:
        file_id_tuple = (file_id.search_hash, file_id.hash_id)
        try:
            chunk_data = get_chunk(file_id_tuple)
            chunks_data.append(
                {"file_id": file_id, "file_data": bytes_to_base64(chunk_data)}
            )
        except FileNotFoundError:
            chunks_data.append({"file_id": file_id, "file_data": None})
            pass
    return {"chunks_data": chunks_data}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/remove_chunks")
async def remove_chunks_endpoint(
    request: RemoveFilesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        background_tasks.add_task(
            remove_chunks_not_in_interval,
            request.start_search_hash,
            request.end_search_hash,
            db,
        )
        return {"message": "Chunk removal task started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
