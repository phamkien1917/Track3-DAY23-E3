"""Checkpointer adapter."""

from __future__ import annotations

import sqlite3
from typing import Any


def build_checkpointer(kind: str = "memory", database_url: str | None = None) -> Any | None:
    """Return a LangGraph checkpointer.

    Supports in-memory, SQLite, and Postgres checkpointers.
    """
    if kind == "none":
        return None

    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    if kind == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        # Resolve target path: use database_url if given, else a local default file.
        db_path = database_url or "checkpoints.sqlite"
        if db_path.startswith("sqlite:///"):
            db_path = db_path[len("sqlite:///"):]

        # check_same_thread=False is required because LangGraph may access the
        # connection from a different thread than the one that created it
        # (e.g. when running inside an async event loop / executor).
        conn = sqlite3.connect(db_path, check_same_thread=False)

        # WAL mode allows concurrent readers while a write is in progress,
        # which is important if multiple graph runs share the same DB file.
        conn.execute("PRAGMA journal_mode=WAL")

        saver = SqliteSaver(conn)
        saver.setup()  # creates the checkpoint tables if they don't exist yet
        return saver

    if kind == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver

        if not database_url:
            raise ValueError(
                "database_url is required for the postgres checkpointer "
                "(e.g. postgresql://user:pass@host:5432/dbname)"
            )

        # from_conn_string returns a context-manager-friendly saver; here we
        # want a plain object to return, so we open the connection directly.
        conn_ctx = PostgresSaver.from_conn_string(database_url)
        saver = conn_ctx.__enter__()
        saver.setup()
        return saver

    raise ValueError(f"Unknown checkpointer kind: {kind}")