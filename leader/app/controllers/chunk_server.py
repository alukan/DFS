from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import hashlib
from app import crud, models
from app.db import get_db
import requests
import asyncio

router = APIRouter()

@router.post("/register_chunk_server/")
def register_chunk_server(url: str, db: Session = Depends(get_db)):
    for server in chunk_servers:
        if server.url == url:
            return {"message": "Chunk server already registered", "url": url, "position": server["position"]}

    position = str(int(hashlib.md5(url.encode('utf-8')).hexdigest(), 16))
    chunk_server = models.ChunkServer(url=url, position=position, fail_count=0)
    chunk_servers.append(chunk_server)
    chunk_servers.sort(key=lambda x: x.position)
    crud.create_chunk_server(db, chunk_server)

    return {"message": "Chunk server registered successfully", "url": url, "position": position}

@router.get("/chunk_servers/")
def get_chunk_servers():
    return [{"url": server.url, "position": server.position, "fail_count": server.fail_count} for server in chunk_servers]

async def health_check():
    while True:
        for server in chunk_servers:
            try:
                response = requests.get(f"{server.url}/health_check")
                if response.status_code == 200:
                    server.fail_count = 0
                else:
                    server.fail_count += 1
            except requests.exceptions.RequestException:
                server.fail_count += 1

            db = next(get_db())
            crud.update_chunk_server_fail_count(db, server.url, server.fail_count)

            if server.fail_count >= 5:
                chunk_servers.remove(server)
                crud.delete_chunk_server(db, server.url)
                print(f"Removed chunk server: {server.url} due to failed health checks.")
        
        await asyncio.sleep(10)

chunk_servers = []
@router.on_event("startup")
async def startup_event():
    db = next(get_db())
    global chunk_servers
    chunk_servers = crud.get_chunk_servers(db)
    asyncio.create_task(health_check())
