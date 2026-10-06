import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


def get_session():
    return SessionLocal()


def init_db():
    from app.infrastructure.models import Base

    Base.metadata.create_all(bind=engine)
