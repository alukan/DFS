from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./chunk_metadata.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ChunkMetadata(Base):
    __tablename__ = "chunk_metadata"

    search_hash = Column(String, primary_key=True, index=True)
    hash_id = Column(String, primary_key=True, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)
