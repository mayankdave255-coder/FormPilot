"""Shared SQL database used by authentication and application session storage."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import Column, Float, Index, Integer, MetaData, String, Table, Text, create_engine, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

metadata = MetaData()
users = Table(
    "users", metadata,
    Column("id", String(32), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("name", String(80), nullable=False),
    Column("password_hash", String(256), nullable=False),
    Column("created_at", Float, nullable=False),
)
login_attempts = Table(
    "login_attempts", metadata,
    Column("email", String(254), primary_key=True),
    Column("attempts", Integer, nullable=False),
    Column("first_attempt", Float, nullable=False),
    Column("blocked_until", Float, nullable=False, default=0),
)
application_sessions = Table(
    "application_sessions", metadata,
    Column("id", String(64), primary_key=True),
    Column("owner_id", String(32), nullable=False),
    Column("payload", Text, nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)
Index("ix_application_sessions_owner_updated", application_sessions.c.owner_id, application_sessions.c.updated_at)
document_library = Table(
    "document_library", metadata,
    Column("id", String(64), primary_key=True),
    Column("owner_id", String(32), nullable=False),
    Column("payload", Text, nullable=False),
    Column("created_at", String(64), nullable=False),
)
Index("ix_document_library_owner", document_library.c.owner_id)

_engine: Engine | None = None


def init_database(data_dir: Path) -> None:
    """Connect to DATABASE_URL, or use the local SQLite file in development."""
    global _engine
    data_dir.mkdir(parents=True, exist_ok=True)
    url = os.getenv("DATABASE_URL", "").strip()
    app_env = os.getenv("APP_ENV", "development").lower()
    if not url:
        if app_env == "production":
            raise RuntimeError("Set DATABASE_URL to a persistent PostgreSQL database before starting in production.")
        url = f"sqlite:///{(data_dir / 'auth.sqlite3').as_posix()}"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if app_env == "production" and not url.startswith("postgresql+"):
        raise RuntimeError("Production deployments must use PostgreSQL through DATABASE_URL.")

    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 15}
    _engine = create_engine(url, **options)
    metadata.create_all(_engine)
    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database has not been initialized.")
    return _engine


@contextmanager
def transaction() -> Iterator[Connection]:
    with engine().begin() as connection:
        yield connection


def backend_name() -> str:
    return engine().dialect.name


def ping() -> bool:
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def save_application_session(session: dict[str, Any]) -> None:
    payload = json.dumps(session, ensure_ascii=False)
    values = {
        "id": session["id"],
        "owner_id": session["owner_id"],
        "payload": payload,
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
    }
    db_engine = engine()
    if db_engine.dialect.name == "postgresql":
        statement = postgres_insert(application_sessions).values(**values)
    elif db_engine.dialect.name == "sqlite":
        statement = sqlite_insert(application_sessions).values(**values)
    else:
        with transaction() as connection:
            current = connection.execute(select(application_sessions.c.id).where(application_sessions.c.id == session["id"])).first()
            if current:
                connection.execute(application_sessions.update().where(application_sessions.c.id == session["id"]).values(**values))
            else:
                connection.execute(application_sessions.insert().values(**values))
        return
    statement = statement.on_conflict_do_update(
        index_elements=[application_sessions.c.id],
        set_={key: statement.excluded[key] for key in ("owner_id", "payload", "created_at", "updated_at")},
    )
    with transaction() as connection:
        connection.execute(statement)


def get_application_session(session_id: str) -> dict[str, Any] | None:
    with engine().connect() as connection:
        payload = connection.execute(
            select(application_sessions.c.payload).where(application_sessions.c.id == session_id)
        ).scalar_one_or_none()
    return json.loads(payload) if payload else None


def list_application_sessions() -> list[dict[str, Any]]:
    with engine().connect() as connection:
        payloads = connection.execute(select(application_sessions.c.payload)).scalars().all()
    results = []
    for payload in payloads:
        try:
            results.append(json.loads(payload))
        except (TypeError, json.JSONDecodeError):
            continue
    return results


def delete_application_session(session_id: str) -> None:
    with transaction() as connection:
        connection.execute(application_sessions.delete().where(application_sessions.c.id == session_id))


def save_library_document(document: dict[str, Any]) -> None:
    values = {"id": document["document_id"], "owner_id": document["owner_id"],
              "payload": json.dumps(document, ensure_ascii=False), "created_at": document["created_at"]}
    db_engine = engine()
    statement = (postgres_insert(document_library) if db_engine.dialect.name == "postgresql"
                 else sqlite_insert(document_library)).values(**values)
    statement = statement.on_conflict_do_update(index_elements=[document_library.c.id],
        set_={key: statement.excluded[key] for key in ("owner_id", "payload", "created_at")})
    with transaction() as connection:
        connection.execute(statement)


def list_library_documents(owner_id: str) -> list[dict[str, Any]]:
    with engine().connect() as connection:
        payloads = connection.execute(select(document_library.c.payload).where(document_library.c.owner_id == owner_id)).scalars().all()
    results = []
    for payload in payloads:
        try:
            results.append(json.loads(payload))
        except (TypeError, json.JSONDecodeError):
            continue
    return results


def get_library_document(document_id: str, owner_id: str) -> dict[str, Any] | None:
    with engine().connect() as connection:
        payload = connection.execute(select(document_library.c.payload).where(
            document_library.c.id == document_id, document_library.c.owner_id == owner_id)).scalar_one_or_none()
    return json.loads(payload) if payload else None


def delete_library_document(document_id: str, owner_id: str) -> None:
    with transaction() as connection:
        connection.execute(document_library.delete().where(
            document_library.c.id == document_id, document_library.c.owner_id == owner_id))
