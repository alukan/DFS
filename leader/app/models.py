from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base

class NameMapping(Base):
    __tablename__ = "NameMappings"
    
    name = Column(String, primary_key=True, index=True)
    chunks = Column(JSONB)
