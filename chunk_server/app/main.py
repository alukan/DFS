from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
import os
import requests
import aiofiles
from datetime import datetime, timedelta
import asyncio

app = FastAPI()

# Directory to store chunks
CHUNK_DIR = "/tmp/chunks"

# Ensure the chunk directory exists
os.makedirs(CHUNK_DIR, exist_ok=True)

# Leader URL and Port
LEADER_URL = os.getenv("LEADER_URL", "http://host.docker.internal:8000")
PORT = int(os.getenv("PORT", 8100))
HEALTH_CHECK_INTERVAL = 60  # Seconds
RECONNECT_INTERVAL = 10  # Seconds

class Chunk(BaseModel):
    chunk_hash: str
    data: str

class ChunkHashes(BaseModel):
    chunks: list[str]


@app.on_event("startup")
async def startup_event():
    await register_with_leader()
    asyncio.create_task(check_health())

async def check_health():
    global last_health_check
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        if datetime.now() - last_health_check > timedelta(seconds=HEALTH_CHECK_INTERVAL):
            print("Health check missed, attempting to reconnect to the leader.")
            await register_with_leader()

async def register_with_leader():
     while True:
        try:
            response = requests.post(f"{LEADER_URL}/register_chunk_server/", params={"url": f"http://host.docker.internal:{PORT}"})
            if response.status_code == 200:
                print("Successfully registered with the leader.")
                global last_health_check
                last_health_check = datetime.now()
                return
            else:
                print("Failed to register with the leader.")
        except Exception as e:
            print(f"Error registering with the leader: {e}")
        await asyncio.sleep(RECONNECT_INTERVAL)


@app.get("/health_check")
def health_check():
    global last_health_check
    last_health_check = datetime.now()
    return {"status": "ok"}


@app.post("/store_chunks_pending/")
async def store_chunks_pending(chunks: list[Chunk]):
    for chunk in chunks:
        chunk_path = os.path.join(CHUNK_DIR, f"pending_{chunk.chunk_hash}")
        os.makedirs(os.path.dirname(chunk_path), exist_ok=True)
        async with aiofiles.open(chunk_path, "w", encoding='utf-8') as f:
            await f.write(chunk.data)
    return {"message": f"Stored {len(chunks)} chunks in pending mode"}


@app.post("/finalize_chunks/")
def finalize_chunks(chunks: ChunkHashes):
    for chunk_hash in chunks.chunks:
        pending_chunk_path = os.path.join(CHUNK_DIR, f"pending_{chunk_hash}")
        final_chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
        if os.path.exists(pending_chunk_path):
            os.rename(pending_chunk_path, final_chunk_path)
    return {"message": "Chunks finalized"}

@app.post("/delete_chunks/")
def delete_chunks(chunks: ChunkHashes):
    for chunk_hash in chunks.chunks:
        chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
    return {"message": "Chunks deleted"}


@app.get("/get_chunk")
def get_chunk(chunk_hash: str = Query(..., description="The hash of the chunk to fetch")):
    chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
    if not os.path.exists(chunk_path):
        raise HTTPException(status_code=404, detail="Chunk not found")
    with open(chunk_path, "rb") as f:
        chunk_data = f.read()
    return chunk_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
