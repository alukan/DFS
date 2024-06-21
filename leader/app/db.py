import time
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

SQLALCHEMY_DATABASE_URL = "postgresql://user:password@db:5432/mydatabase"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Retry mechanism for database connection
max_retries = 60
retry_interval = 1

for i in range(max_retries):
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Add the index on the chunks column
        with engine.connect() as connection:
            connection.execute(
                text('CREATE INDEX IF NOT EXISTS chunks_idx ON "NameMappings" USING GIN (chunks jsonb_path_ops)')
            )
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
