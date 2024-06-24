from pydantic import BaseModel
from typing import List


class ChunkData(BaseModel):
    hash_id: str
    search_hash: int
    content: bytes


class UploadRequest(BaseModel):
    file_id: str
    data: List[ChunkData]


class ChunkServerRegistration(BaseModel):
    id: str
    cleanense_need: int = 0
    alive_missed: int = 0
