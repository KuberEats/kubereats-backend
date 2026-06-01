import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/kubereats")

# Securely log the database host to verify connection
from urllib.parse import urlparse
try:
    parsed_url = urlparse(DATABASE_URL)
    print(f"Connecting to database at host: {parsed_url.hostname}")
except Exception:
    print("Connecting to database...")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=50,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
