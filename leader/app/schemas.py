from typing import List, Tuple
from pydantic import BaseModel

class NameMappingBase(BaseModel):
    full_path: str

class NameMappingCreate(NameMappingBase):
    chunk_hashes: List[Tuple[str, str]]
    size: int

class NameMapping(NameMappingBase):
    id: int
    chunk_hashes: List[Tuple[str, int]]
    size: int

    class Config:
        orm_mode = True
