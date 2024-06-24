from typing import List
from pydantic import BaseModel


class FileId(BaseModel):
    search_hash: int
    hash_id: str


class SaveFileRequest(BaseModel):
    file_id: FileId
    file_data: bytes


class SaveFilesRequest(BaseModel):
    files_data: List[SaveFileRequest]


class GetChunksRequest(BaseModel):
    files_ids: List[FileId]


class GetChunkResponse(BaseModel):
    file_id: FileId
    file_data: str


class GetChunksResponse(BaseModel):
    chunks_data: List[GetChunkResponse]


class RemoveFilesRequest(BaseModel):
    start_search_hash: int
    end_search_hash: int


class SendIntervalRequest(BaseModel):
    target: str
    ini_chunk: int
    end_chunk: int
