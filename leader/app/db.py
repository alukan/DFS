import time
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .models import Base

SQLALCHEMY_DATABASE_URL = "postgresql://user:password@db:5432/mydatabase"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

max_retries = 60
retry_interval = 1

for i in range(max_retries):
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database connected and tables created.")
        break
    except OperationalError as e:
        print(f"Database connection failed: {e}")
        if i < max_retries - 1:
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
        else:
            print("Max retries reached. Exiting.")
            raise
