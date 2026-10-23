# SPDX-License-Identifier: MPL-2.0
"""Persistência SQLite com migrations imutáveis, concorrentes e transacionais."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import sqlite3
from pathlib import Path


def app_data_dir(app_id):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", app_id):
        raise ValueError("Identificador de aplicativo inválido.")
    system = platform.system()
    if system == "Windows":
        home = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif system == "Darwin":
        home = Path.home() / "Library/Application Support"
    else:
        home = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
    return home / "vela" / app_id


def _iter_sql_statements(source: str):
    """Divide script em statements usando o parser de completude do SQLite."""
    buffer: list[str] = []
    for char in source:
        buffer.append(char)
        if char == ";":
            candidate = "".join(buffer)
            if sqlite3.complete_statement(candidate):
                if candidate.strip():
                    yield candidate
                buffer.clear()
    remaining = "".join(buffer).strip()
    if remaining:
        candidate = remaining + ";"
        if not sqlite3.complete_statement(candidate):
            raise sqlite3.OperationalError("Migration SQL incompleta.")
        yield candidate


class SQLiteStore:
    def __init__(self, app_id, database=None, *, wal=True):
        self.path = (
            Path(database).expanduser() if database else app_data_dir(app_id) / "app.sqlite3"
        )
        self.wal = bool(wal)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        if self.wal:
            try:
                mode = db.execute("PRAGMA journal_mode = WAL").fetchone()[0]
                if str(mode).lower() == "wal":
                    db.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.DatabaseError:
                pass
        return db

    def migrate(self, directory):
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(str(directory))
        paths = sorted(directory.glob("*.sql"))
        applied = []
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS vela_migrations ("
                "name TEXT PRIMARY KEY, sha256 TEXT NOT NULL)"
            )
            conn.commit()
            for path in paths:
                name = path.name
                if not re.fullmatch(r"[A-Za-z0-9_.-]+\.sql", name):
                    raise ValueError("Migration com nome inválido.")
                source = path.read_bytes()
                digest = hashlib.sha256(source).hexdigest()
                sql = source.decode("utf-8")
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    row = conn.execute(
                        "SELECT sha256 FROM vela_migrations WHERE name = ?", (name,)
                    ).fetchone()
                    if row is not None:
                        if row[0] != digest:
                            raise RuntimeError("Migration já aplicada foi alterada: " + name)
                        conn.commit()
                        continue
                    for statement in _iter_sql_statements(sql):
                        conn.execute(statement)
                    conn.execute(
                        "INSERT INTO vela_migrations(name, sha256) VALUES(?, ?)",
                        (name, digest),
                    )
                    conn.commit()
                except Exception:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                applied.append(name)
        return applied
