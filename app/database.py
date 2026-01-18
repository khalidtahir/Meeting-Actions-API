"""
Database connection and session management.
SQLAlchemy setup with dependency injection for FastAPI.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config import get_settings

settings = get_settings()

# Create engine - check_same_thread=False needed for SQLite with FastAPI
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory - creates new sessions for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency that provides a database session to route handlers.
    Automatically closes session after request completes.
    
    Usage in routes:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables in the database.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)