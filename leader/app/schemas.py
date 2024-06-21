from pydantic import BaseModel
from typing import Dict

class NameMappingBase(BaseModel):
    name: str

class NameMappingCreate(NameMappingBase):
    chunks: Dict[str, str]

class NameMapping(NameMappingBase):
    chunks: Dict[str, str]

    class Config:
        orm_mode = True
