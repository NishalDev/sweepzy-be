from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from  config.settings import settings  # adjust import based on your structure

# Use the value loaded from .env
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()