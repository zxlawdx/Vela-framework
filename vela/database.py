"""Persistencia local SQLite com migrations SQL idempotentes por projeto."""
from __future__ import annotations

import hashlib
import os
import platform
import re
import sqlite3
from pathlib import Path


def app_data_dir(app_id):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", app_id):
        raise ValueError("Identificador de aplicativo invalido")
    system = platform.system()
    if system == "Windows":
        home = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif system == "Darwin":
        home = Path.home() / "Library/Application Support"
    else:
        home = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
    return home / "vela" / app_id


class SQLiteStore:
    def __init__(self, app_id, database=None):
        self.path = (Path(database).expanduser() if database
                     else app_data_dir(app_id) / "app.sqlite3")

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def migrate(self, directory):
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(str(directory))
        applied = []
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS vela_migrations ("
                "name TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
            existing = dict(conn.execute("SELECT name, sha256 FROM vela_migrations"))
            for path in sorted(directory.glob("*.sql")):
                name = path.name
                if not re.fullmatch(r"[A-Za-z0-9_.-]+\.sql", name):
                    raise ValueError("Migration com nome invalido")
                source = path.read_bytes()
                digest = hashlib.sha256(source).hexdigest()
                if name in existing:
                    if existing[name] != digest:
                        raise RuntimeError("Migration ja aplicada foi alterada: " + name)
                    continue
                # Arquivos SQL sao codigo confiavel da propria aplicacao.
                # A tabela de historico e atualizada no mesmo commit.
                sql = source.decode("utf-8").rstrip(";\n ")
                script = ("BEGIN IMMEDIATE;\n" + sql + ";\n"
                          "INSERT INTO vela_migrations(name, sha256) VALUES("
                          "'" + name + "', '" + digest + "');\nCOMMIT;")
                try:
                    conn.executescript(script)
                except Exception:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                applied.append(name)
        return applied
