# SPDX-License-Identifier: MPL-2.0
"""App-scoped immutable resource snapshots with optimistic publication.

Resources are stored as immutable, versioned files. Applications exchange
resource IDs and revisions, not entire payloads through the JS bridge.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import BinaryIO
from uuid import uuid4
import os
import shutil
import tempfile

from vela.events import EventBus


class RevisionConflict(RuntimeError):
    """Publication attempted against a stale resource revision."""


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

    def __init__(self, *, events: EventBus | None = None, directory: str | Path | None = None,
                 max_resource_bytes: int = 2 * 1024**3, max_chunk_bytes: int = 1024**2):
        if max_resource_bytes <= 0 or max_chunk_bytes <= 0:
            raise ValueError("Limits must be positive.")
        self._events = events
        self._lock = RLock()
        self._temp = tempfile.TemporaryDirectory(prefix="vela-resources-") if directory is None else None
        self._root = Path(self._temp.name if self._temp else directory).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._items: dict[str, list[ResourceSnapshot]] = {}
        self._max_size = max_resource_bytes
        self._chunk_limit = max_chunk_bytes
        self._closed = False

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("ResourceStore is closed.")

    @staticmethod
    def _validate_id(resource_id: str) -> None:
        if not isinstance(resource_id, str) or not resource_id or len(resource_id) > 128:
            raise ValueError("Invalid resource ID.")

    def _path(self, resource_id: str, revision: int) -> Path:
        return self._root / resource_id / f"{revision}.blob"

    def current(self, resource_id: str) -> ResourceSnapshot:
        with self._lock:
            self._check_open()
            self._validate_id(resource_id)
            versions = self._items.get(resource_id)
            if not versions:
                raise ResourceNotFound(resource_id)
            return versions[-1]

    def snapshot(self, resource_id: str, revision: int) -> ResourceSnapshot:
        with self._lock:
            self._check_open()
            self._validate_id(resource_id)
            if type(revision) is not int or revision < 1:
                raise ValueError("Invalid revision.")
            versions = self._items.get(resource_id)
            if not versions or revision > len(versions):
                raise ResourceNotFound((resource_id, revision))
            return versions[revision - 1]

    def publish(self, source: bytes | BinaryIO, *, resource_id: str | None = None,
                expected_revision: int | None = None,
                media_type: str = "application/octet-stream") -> ResourceSnapshot:
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
        with self._lock:
            self._check_open()
            existing = self._items.get(resource_id)
            current_revision = existing[-1].revision if existing else 0
            if expected_revision != (current_revision or None):
                raise RevisionConflict(f"Expected {expected_revision}, actual {current_revision}")
            next_revision = current_revision + 1
            destination = self._path(resource_id, next_revision)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp_path = destination.with_suffix(".writing-" + uuid4().hex)
            digest = sha256()
            size = 0
            try:
                with temp_path.open("xb") as target:
                    if isinstance(source, bytes):
                        chunks = (source[i:i + 1024**2] for i in range(0, len(source), 1024**2))
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
                        target.write(chunk)
                os.replace(temp_path, destination)
            finally:
                temp_path.unlink(missing_ok=True)
            result = ResourceSnapshot(resource_id, next_revision, size, digest.hexdigest(), media_type)
            self._items.setdefault(resource_id, []).append(result)
        if self._events is not None:
            self._events.emit("resource:published", result.to_dict())
        return result

    def open_path(self, resource_id: str, revision: int) -> Path:
        """Trusted backend only: a read-only-by-contract snapshot path."""
        self.snapshot(resource_id, revision)
        return self._path(resource_id, revision)

    def read_chunk(self, resource_id: str, revision: int, *, offset: int = 0,
                   length: int = 65536) -> bytes:
        snap = self.snapshot(resource_id, revision)
        if type(offset) is not int or offset < 0:
            raise ValueError("Invalid offset.")
        if type(length) is not int or not 0 < length <= self._chunk_limit:
            raise ValueError("Invalid length.")
        if offset >= snap.size:
            return b""
        with self._path(resource_id, revision).open("rb") as stream:
            stream.seek(offset)
            return stream.read(length)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._items.clear()
            if self._temp is not None:
                self._temp.cleanup()
