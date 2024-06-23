from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory to store chunks
CHUNK_DIR = "/tmp/chunks"

# Ensure the chunk directory exists
os.makedirs(CHUNK_DIR, exist_ok=True)

# Leader URL and Port
LEADER_URL = os.getenv("LEADER_URL", "http://localhost:8000")
PORT = int(os.getenv("PORT", 8100))

class Chunk(BaseModel):
    chunk_hash: str
    data: str

class Chunks(BaseModel):
    chunks: list
    file: bytes

@app.post("/store_chunks_pending/")
def store_chunks_pending(chunks: Chunks):
    for chunk_hash in chunks.chunks:
        chunk_path = os.path.join(CHUNK_DIR, f"pending_{chunk_hash}")
        with open(chunk_path, "wb") as f:
            f.write(chunks.file)
    return {"message": "Chunks stored in pending mode"}

@app.post("/finalize_chunks/")
def finalize_chunks(chunks: Chunks):
    for chunk_hash in chunks.chunks:
        pending_chunk_path = os.path.join(CHUNK_DIR, f"pending_{chunk_hash}")
        final_chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
        if os.path.exists(pending_chunk_path):
            os.rename(pending_chunk_path, final_chunk_path)
    return {"message": "Chunks finalized"}

@app.post("/delete_chunks/")
def delete_chunks(chunks: Chunks):
    for chunk_hash in chunks.chunks:
        chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
    return {"message": "Chunks deleted"}

@app.on_event("startup")
def register_with_leader():
    try:
        response = requests.post(f"{LEADER_URL}/register_chunk_server/", params={"url": f"http://localhost:{PORT}"})
        if response.status_code == 200:
            logger.info("Successfully registered with the leader.")
        else:
            logger.error("Failed to register with the leader.")
    except Exception as e:
        logger.error(f"Error registering with the leader: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting chunk server...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
