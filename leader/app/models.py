from sqlalchemy import Column, Integer, String, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NameMapping(Base):
    __tablename__ = 'name_mappings'
    id = Column(Integer, primary_key=True, index=True)
    full_path = Column(String, unique=True, index=True)
    chunk_hashes = Column(ARRAY(String))
