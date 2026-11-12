"""Couche d'accès aux données : engine SQLAlchemy, session, Base déclarative."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite exige check_same_thread=False en contexte multi-thread (FastAPI).
_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Le pooling n'a de sens que pour un vrai SGBD (PostgreSQL) ; SQLite reste simple.
_pool_kwargs = {} if _is_sqlite else {
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
    "pool_recycle": settings.db_pool_recycle,
    "pool_timeout": settings.db_pool_timeout,
}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,   # évite les connexions mortes en prod
    future=True,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session par requête et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
