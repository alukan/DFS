from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Directory to store chunks
CHUNK_DIR = "/tmp/chunks"

# Ensure the chunk directory exists
os.makedirs(CHUNK_DIR, exist_ok=True)

# Leader URL and Port
LEADER_URL = os.getenv("LEADER_URL", "http://host.docker.internal:8000")
PORT = int(os.getenv("PORT", 8100))

class Chunk(BaseModel):
    chunk_hash: str
    data: str

class Chunks(BaseModel):
    chunks: list[str]

@app.post("/store_chunks_pending/")
def store_chunks_pending(file: UploadFile = File(...), chunk_hash: str = Form(...)):
    chunk_path = os.path.join(CHUNK_DIR, f"pending_{chunk_hash}")
    with open(chunk_path, "wb") as f:
        f.write(file.file.read())
    return {"message": "Chunk stored in pending mode"}

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

@app.get("/health_check")
def health_check():
    return {"status": "ok"}

@app.get("/get_chunk")
def get_chunk(chunk_hash: str = Query(..., description="The hash of the chunk to fetch")):
    chunk_path = os.path.join(CHUNK_DIR, chunk_hash)
    if not os.path.exists(chunk_path):
        raise HTTPException(status_code=404, detail="Chunk not found")
    with open(chunk_path, "rb") as f:
        chunk_data = f.read()
    return chunk_data

@app.on_event("startup")
def register_with_leader():
    try:
        response = requests.post(f"{LEADER_URL}/register_chunk_server/", params={"url": f"http://host.docker.internal:{PORT}"})
        if response.status_code == 200:
            print("Successfully registered with the leader.")
        else:
            print("Failed to register with the leader.")
    except Exception as e:
        print(f"Error registering with the leader: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
