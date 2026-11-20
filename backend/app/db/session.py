from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # Created lazily so importing the app never opens a database connection.
    # hide_parameters: SQL logs and error messages never include bound values (feature JSON etc.).
    engine = create_engine(
        get_settings().sqlalchemy_url, pool_pre_ping=True, pool_recycle=3600, hide_parameters=True
    )
    if engine.dialect.name == "sqlite":  # e.g. a synthetic demo database; MySQL enforces FKs itself
        event.listen(engine, "connect", lambda dbapi_conn, _record: dbapi_conn.execute("PRAGMA foreign_keys=ON"))
    return engine


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
