import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

# Read database configuration
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Validate configuration
required_values = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing_values = [
    key for key, value in required_values.items() if not value
]

if missing_values:
    raise ValueError(
        f"Missing database environment variables: {', '.join(missing_values)}"
    )

# Create database URL
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Create database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# Base class for all database models
class Base(DeclarativeBase):
    pass


# FastAPI database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()