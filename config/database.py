from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

# Optimized database configuration
DATABASE_URL = settings.DATABASE_URL

# Create engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    # Connection pooling settings
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    # Only echo SQL queries in debug mode
    echo=settings.DEBUG,
    # Connection timeout settings
    connect_args={
        "options": "-c timezone=utc"
    } if "postgresql" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── New Uploads config ──────────────────────────────────────────────────────────
# directory where uploaded files will live
# (adjust path if you want it elsewhere)
PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
