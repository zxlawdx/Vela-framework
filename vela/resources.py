# SPDX-License-Identifier: MPL-2.0
"""App-scoped immutable resource snapshots with optimistic publication.

Resources are stored as immutable, versioned files. Applications exchange
resource IDs and revisions, not entire payloads through the JS bridge.
"""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import BinaryIO
from uuid import uuid4

from vela.events import EventBus


class RevisionConflict(RuntimeError):
    """Publication attempted against a stale resource revision."""


class ResourceQuotaExceeded(ValueError):
    """Publication would exceed the configured total disk quota."""


class ResourceCorrupted(RuntimeError):
    """A catalogued snapshot is missing, redirected or has invalid content."""


class ResourceNotFound(KeyError):
    """Unknown resource or revision."""


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    resource_id: str
    revision: int
    size: int
    sha256: str
    media_type: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "resource_id": self.resource_id,
            "revision": self.revision,
            "size": self.size,
            "sha256": self.sha256,
            "media_type": self.media_type,
        }


class ResourceStore:
    """Local immutable snapshots; service lifetime is scoped to a VelaApp.

    The filesystem path is private to trusted Python consumers. Never send it
    to the WebView. The bridge should expose only bounded chunks and metadata.
    """

    def __init__(
        self,
        *,
        events: EventBus | None = None,
        directory: str | Path | None = None,
        max_resource_bytes: int = 2 * 1024**3,
        max_chunk_bytes: int = 1024**2,
        max_store_bytes: int | None = None,
        retention_versions: int | None = None,
        verify_on_startup: bool = True,
    ):
        if max_resource_bytes <= 0 or max_chunk_bytes <= 0:
            raise ValueError("Limits must be positive.")
        for value in (max_store_bytes, retention_versions):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError("Quota and retention must be positive integers.")
        self._quota = max_store_bytes
        self._retention = retention_versions
        self._events = events
        self._lock = RLock()
        self._temp = (
            tempfile.TemporaryDirectory(prefix="vela-resources-") if directory is None else None
        )
        requested = Path(self._temp.name if self._temp else directory).absolute()
        if requested.is_symlink():
            raise ValueError("Resource directory must not be a symbolic link.")
        self._root = requested.resolve()
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            if self._root.stat().st_uid != os.getuid():
                raise PermissionError("Resource directory belongs to a different user.")
            self._root.chmod(0o700)
        catalog = self._root / "resources.sqlite3"
        if catalog.is_symlink():
            raise PermissionError("Resource catalog must not be a symbolic link.")
        self._db = sqlite3.connect(self._root / "resources.sqlite3", check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS snapshots (resource_id TEXT, revision INTEGER, size INTEGER, sha256 TEXT, media_type TEXT, PRIMARY KEY(resource_id, revision))"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS resource_pins (owner TEXT, resource_id TEXT, revision INTEGER, PRIMARY KEY(owner, resource_id, revision))"
        )
        self._db.commit()
        self._max_size = max_resource_bytes
        self._chunk_limit = max_chunk_bytes
        self._closed = False
        try:
            self.recover(verify=verify_on_startup)
        except BaseException:
            self._db.close()
            if self._temp is not None:
                self._temp.cleanup()
            raise

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("ResourceStore is closed.")

    @staticmethod
    def _validate_id(resource_id: str) -> None:
        if not isinstance(resource_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", resource_id
        ):
            raise ValueError("Invalid resource ID.")

    def _path(self, resource_id: str, revision: int) -> Path:
        folder = self._root / resource_id
        if folder.is_symlink():
            raise PermissionError("Resource directory must not be a symbolic link.")
        path = folder / f"{revision}.blob"
        if path.is_symlink():
            raise PermissionError("Resource snapshot must not be a symbolic link.")
        return path

    def current(self, resource_id: str) -> ResourceSnapshot:
        with self._lock:
            self._check_open()
            self._validate_id(resource_id)
            row = self._db.execute(
                "SELECT * FROM snapshots WHERE resource_id=? ORDER BY revision DESC LIMIT 1",
                (resource_id,),
            ).fetchone()
            if row is None:
                raise ResourceNotFound(resource_id)
            return ResourceSnapshot(*row)

    def snapshot(self, resource_id: str, revision: int) -> ResourceSnapshot:
        with self._lock:
            self._check_open()
            self._validate_id(resource_id)
            if type(revision) is not int or revision < 1:
                raise ValueError("Invalid revision.")
            row = self._db.execute(
                "SELECT * FROM snapshots WHERE resource_id=? AND revision=?",
                (resource_id, revision),
            ).fetchone()
            if row is None:
                raise ResourceNotFound((resource_id, revision))
            return ResourceSnapshot(*row)

    @contextmanager
    def _publication(self):
        # Serialize writers across store instances/processes sharing a directory.
        self._check_open()
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise

    def publish(
        self,
        source: bytes | BinaryIO,
        *,
        resource_id: str | None = None,
        expected_revision: int | None = None,
        media_type: str = "application/octet-stream",
    ) -> ResourceSnapshot:
        """Create a resource or append an immutable revision.

        expected_revision must equal the current revision when updating.
        Input streams are consumed from their current offset.
        """
        if not isinstance(media_type, str) or not media_type or len(media_type) > 255:
            raise ValueError("Invalid media type.")
        if resource_id is None:
            if expected_revision is not None:
                raise ValueError("New resources cannot have an expected revision.")
            resource_id = uuid4().hex
        self._validate_id(resource_id)
        with self._lock, self._publication():
            self._check_open()
            if expected_revision is not None and (
                type(expected_revision) is not int or expected_revision < 1
            ):
                raise ValueError("Invalid expected revision.")
            row = self._db.execute(
                "SELECT MAX(revision) FROM snapshots WHERE resource_id=?", (resource_id,)
            ).fetchone()
            current_revision = row[0] or 0
            if expected_revision != (current_revision or None):
                raise RevisionConflict(f"Expected {expected_revision}, actual {current_revision}")
            committed_bytes = self._db.execute(
                "SELECT COALESCE(SUM(size),0) FROM snapshots"
            ).fetchone()[0]
            next_revision = current_revision + 1
            destination = self._path(resource_id, next_revision)
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temp_path = destination.with_suffix(".writing-" + uuid4().hex)
            digest = sha256()
            size = 0
            try:
                with temp_path.open("xb") as target:
                    if isinstance(source, bytes):
                        chunks = (source[i : i + 1024**2] for i in range(0, len(source), 1024**2))
                    elif hasattr(source, "read"):
                        chunks = iter(lambda: source.read(1024**2), b"")
                    else:
                        raise TypeError("Source must be bytes or a binary stream.")
                    for chunk in chunks:
                        if not isinstance(chunk, bytes):
                            raise TypeError("Input stream must return bytes.")
                        size += len(chunk)
                        if size > self._max_size:
                            raise ValueError("Resource exceeds max_resource_bytes.")
                        digest.update(chunk)
                        if self._quota is not None and committed_bytes + size > self._quota:
                            raise ResourceQuotaExceeded("Resource store quota exceeded.")
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                os.replace(temp_path, destination)
                self._sync_directory(destination.parent)
            finally:
                temp_path.unlink(missing_ok=True)
            result = ResourceSnapshot(
                resource_id, next_revision, size, digest.hexdigest(), media_type
            )
            self._db.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?)",
                (resource_id, next_revision, size, result.sha256, media_type),
            )
        if self._events is not None:
            self._events.emit("resource:published", result.to_dict())
        if self._retention is not None:
            self.prune(resource_id, keep_last=self._retention)
        return result

    def open_path(self, resource_id: str, revision: int) -> Path:
        """Trusted backend only: a read-only-by-contract snapshot path."""
        snap = self.snapshot(resource_id, revision)
        path = self._path(resource_id, revision)
        if not path.is_file() or path.stat().st_size != snap.size:
            raise ResourceCorrupted((resource_id, revision))
        return path

    def read_chunk(
        self, resource_id: str, revision: int, *, offset: int = 0, length: int = 65536
    ) -> bytes:
        snap = self.snapshot(resource_id, revision)
        if type(offset) is not int or offset < 0:
            raise ValueError("Invalid offset.")
        if type(length) is not int or not 0 < length <= self._chunk_limit:
            raise ValueError("Invalid length.")
        if offset >= snap.size:
            return b""
        with self.open_path(resource_id, revision).open("rb") as stream:
            stream.seek(offset)
            return stream.read(length)

    @contextmanager
    def edit(self, resource_id: str, revision: int):
        """Yield an isolated seekable draft. Publication is always explicit."""
        import shutil

        with tempfile.TemporaryFile(mode="w+b") as draft:
            with self.open_path(resource_id, revision).open("rb") as original:
                shutil.copyfileobj(original, draft, length=1024**2)
            draft.seek(0)
            yield draft

    def iter_chunks(self, resource_id: str, revision: int, *, length: int = 65536):
        """Stream bounded chunks without materializing a resource in memory."""
        offset = 0
        while True:
            chunk = self.read_chunk(resource_id, revision, offset=offset, length=length)
            if not chunk:
                return
            yield chunk
            offset += len(chunk)

    @staticmethod
    def _sync_directory(directory):
        # Directory fsync is supported on POSIX; Windows flushes files and uses
        # SQLite FULL synchronous commits, but has no equivalent portable API.
        if os.name != "nt":
            descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def verify(self, resource_id, revision):
        """Verify bytes against the immutable catalog; fail closed on corruption."""
        with self._lock:
            snapshot = self.snapshot(resource_id, revision)
            path = self.open_path(resource_id, revision)
            digest = sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024**2), b""):
                    digest.update(chunk)
            if digest.hexdigest() != snapshot.sha256:
                raise ResourceCorrupted((resource_id, revision))
            return snapshot

    def pin(self, owner, resource_id, revision):
        """Protect a revision retained by a durable workspace/reference owner."""
        self._validate_id(owner)
        with self._lock, self._publication():
            self.snapshot(resource_id, revision)
            self._db.execute(
                "INSERT OR IGNORE INTO resource_pins VALUES (?,?,?)", (owner, resource_id, revision)
            )

    def unpin(self, owner, resource_id, revision):
        self._validate_id(owner)
        with self._lock, self._publication():
            self._db.execute(
                "DELETE FROM resource_pins WHERE owner=? AND resource_id=? AND revision=?",
                (owner, resource_id, revision),
            )

    def replace_pins(self, owner, handles):
        """Atomically reconcile durable references owned by one consumer."""
        self._validate_id(owner)
        handles = list(handles)
        with self._lock, self._publication():
            for handle in handles:
                self.snapshot(handle["resource_id"], handle["revision"])
            self._db.execute("DELETE FROM resource_pins WHERE owner=?", (owner,))
            self._db.executemany(
                "INSERT OR IGNORE INTO resource_pins VALUES(?,?,?)",
                [(owner, handle["resource_id"], handle["revision"]) for handle in handles],
            )

    def prune(self, resource_id, *, keep_last=1):
        """Delete unpinned older versions; keep current and never renumber revisions."""
        self._validate_id(resource_id)
        if type(keep_last) is not int or keep_last < 1:
            raise ValueError("keep_last must be positive.")
        removed = []
        with self._lock, self._publication():
            threshold = self.current(resource_id).revision - keep_last
            rows = self._db.execute(
                "SELECT revision FROM snapshots s WHERE resource_id=? AND revision<=? AND NOT EXISTS (SELECT 1 FROM resource_pins p WHERE p.resource_id=s.resource_id AND p.revision=s.revision)",
                (resource_id, threshold),
            ).fetchall()
            for (revision,) in rows:
                self._db.execute(
                    "DELETE FROM snapshots WHERE resource_id=? AND revision=?",
                    (resource_id, revision),
                )
                removed.append(revision)
        # Metadata deletion commits first. Interrupted unlink is collected by
        # recover(); never expose a catalog row whose blob we already deleted.
        for revision in removed:
            self._path(resource_id, revision).unlink(missing_ok=True)
        if removed and self._events is not None:
            self._events.emit("resource:pruned", {"resource_id": resource_id, "revisions": removed})
        return removed

    def usage(self):
        with self._lock:
            self._check_open()
            count, size = self._db.execute(
                "SELECT COUNT(*),COALESCE(SUM(size),0) FROM snapshots"
            ).fetchone()
            return {"revisions": count, "bytes": size, "quota_bytes": self._quota}

    def recover(self, *, verify=True):
        """Serialize against publishers, verify committed data and remove orphans.

        Missing/corrupt committed blobs raise without modifying the catalog.
        No arbitrary recursive traversal and no following symbolic links.
        """
        removed = 0
        with self._lock, self._publication():
            if self._db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ResourceCorrupted("Invalid resource catalog.")
            for resource_id, revision in self._db.execute(
                "SELECT resource_id,revision FROM snapshots"
            ).fetchall():
                self._validate_id(resource_id)
                if verify:
                    self.verify(resource_id, revision)
                else:
                    self.open_path(resource_id, revision)
            for folder in self._root.iterdir():
                if folder.is_symlink():
                    raise PermissionError("Unexpected symbolic link in resource storage.")
                if not folder.is_dir():
                    continue
                self._validate_id(folder.name)
                for path in folder.iterdir():
                    if path.is_symlink():
                        raise PermissionError("Unexpected snapshot symbolic link.")
                    if not path.is_file():
                        continue
                    revision_text = path.stem
                    temporary = ".writing-" in path.name
                    orphan = (
                        path.suffix == ".blob"
                        and revision_text.isdigit()
                        and not self._db.execute(
                            "SELECT 1 FROM snapshots WHERE resource_id=? AND revision=?",
                            (folder.name, int(revision_text)),
                        ).fetchone()
                    )
                    if temporary or orphan:
                        path.unlink()
                        removed += 1
        return {"removed_orphans": removed}

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._db.close()
            if self._temp is not None:
                self._temp.cleanup()
