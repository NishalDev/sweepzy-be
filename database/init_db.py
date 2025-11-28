from sqlalchemy.orm import Session
from api.models import Base
from database.session import engine

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized!")
