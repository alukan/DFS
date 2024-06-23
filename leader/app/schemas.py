from pydantic import BaseModel
from typing import List, Tuple

class NameMappingBase(BaseModel):
    full_path: str

class NameMappingCreate(NameMappingBase):
    chunk_hashes: List[Tuple[str, str]]

class NameMapping(NameMappingBase):
    id: int
    chunk_hashes: List[Tuple[str, str]] 

    class Config:
        orm_mode = True
