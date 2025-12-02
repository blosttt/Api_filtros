# database.py - VERSIÓN COMPATIBLE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base  # ← MANTENER así para SQLAlchemy 1.4
from config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # ← NO CAMBIAR, así está bien para 1.4

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()