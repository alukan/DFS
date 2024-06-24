from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    file_id = Column(String, primary_key=True, index=True)
    data = Column(JSON, nullable=False)


class ChunkServer(Base):
    __tablename__ = "chunk_servers"
    id = Column(String, primary_key=True, index=True)
    cleanness_need = Column(Integer, default=0)
    alive_missed = Column(Integer, default=0)
    host = Column(String, nullable=False)
    alive = Column(Boolean, default=True)
