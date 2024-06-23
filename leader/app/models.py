from sqlalchemy import Column, Integer, String, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class NameMapping(Base):
    __tablename__ = 'name_mappings'
    id = Column(Integer, primary_key=True, index=True)
    full_path = Column(String, unique=True, index=True)
    chunk_hashes = Column(JSONB)
