from typing import List
from pydantic import BaseModel


class FileId(BaseModel):
    search_hash: str
    hash_id: str


class SaveFileRequest(BaseModel):
    file_id: FileId
    file_data: bytes


class GetChunksRequest(BaseModel):
    files_ids: List[FileId]


class GetChunkResponse(BaseModel):
    file_id: FileId
    file_data: str


class GetChunksResponse(BaseModel):
    chunks_data: List[GetChunkResponse]


class RemoveFilesRequest(BaseModel):
    start_search_hash: str
    end_search_hash: str
