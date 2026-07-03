"""Configuração do SQLAlchemy 2.0: engine, sessão, Base e dependency get_db()."""

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite exige check_same_thread=False para uso com FastAPI (múltiplas threads).
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite vem com foreign_keys OFF por padrão: sem isso, ondelete CASCADE /
    # SET NULL dos modelos NÃO rodam (os relationships usam passive_deletes=True
    # e delegam ao banco). Liga por conexão, igualando o comportamento ao Postgres.
    @event.listens_for(engine, "connect")
    def _sqlite_fk_on(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Convenção de nomes de constraints — garante nomes previsíveis e idênticos
# em SQLite (dev) e PostgreSQL (prod), o que o Alembic (inclusive batch mode) exige.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: abre uma sessão por request e fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
