"""Configuração do SQLAlchemy 2.0: engine, sessão, Base e dependency get_db()."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite exige check_same_thread=False para uso com FastAPI (múltiplas threads).
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos (definidos nas próximas fases)."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: abre uma sessão por request e fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
