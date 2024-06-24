from chunk import Chunk
import requests
from sqlalchemy.orm import Session
from .files import get_chunk


async def send_interval_to_chunk_server(
    target: str, ini_chunk: int, end_chunk: int, db: Session
):
    chunks = (
        db.query(Chunk)
        .filter(
            Chunk.search_hash >= ini_chunk,
            Chunk.search_hash <= end_chunk,
        )
        .all()
    )
    batch_size = 10
    chunks_batchs = [
        chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)
    ]
    for batch in chunks_batchs:
        for chunk in batch:
            chunk.data = get_chunk((chunk.hash_id, chunk.search_hash))
        requests.post(
            f"http://{target}/upload",
            json={
                "files_data": [
                    {
                        "hash_id": chunk.hash_id,
                        "search_hash": chunk.search_hash,
                        "data": chunk.data,
                    }
                    for chunk in batch
                ]
            },
        )
    # Send the interval [ini_chunk, end_chunk] to the target chunk server
    requests.post(
        f"http://{target}/send_interval",
        json={
            "start_search_hash": ini_chunk,
            "end_search_hash": end_chunk,
        },
    )
