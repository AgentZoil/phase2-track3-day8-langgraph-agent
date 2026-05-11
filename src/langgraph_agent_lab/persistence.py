"""Checkpointer adapter."""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path
from typing import Any


def _normalize_sqlite_path(database_url: str | None) -> str:
    """Return a filesystem path for SQLite checkpoints.

    Accepts plain paths, ``sqlite:///...`` URLs, or ``:memory:``.
    """
    if not database_url:
        return "checkpoints.db"
    if database_url == ":memory:":
        return database_url
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    return database_url


def _build_sqlite_checkpointer(database_url: str | None) -> Any:  # noqa: ANN401
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "SQLite checkpointer requires: pip install langgraph-checkpoint-sqlite"
        ) from exc

    db_path = _normalize_sqlite_path(database_url)
    if db_path != ":memory:":
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return SqliteSaver(conn=conn)


def build_checkpointer(kind: str = "memory", database_url: str | None = None) -> Any | None:  # noqa: ANN401
    """Return a LangGraph checkpointer.

    Supports in-memory, SQLite, and optional Postgres checkpointers.
    """
    if kind == "none":
        return None
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    if kind == "sqlite":
        return _build_sqlite_checkpointer(database_url)
    if kind == "postgres":
        try:
            postgres_module = importlib.import_module("langgraph.checkpoint.postgres")
            postgres_saver_cls = postgres_module.PostgresSaver  # type: ignore[attr-defined]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Postgres checkpointer requires: pip install langgraph-checkpoint-postgres"
            ) from exc
        return postgres_saver_cls.from_conn_string(database_url or "")
    raise ValueError(f"Unknown checkpointer kind: {kind}")
