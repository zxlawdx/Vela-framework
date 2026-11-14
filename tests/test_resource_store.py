"""Native resource store regression tests."""

from io import BytesIO

import pytest

from vela.events import EventBus
from vela.resources import ResourceNotFound, ResourceStore, RevisionConflict


def test_publish_snapshot_is_immutable_and_conflicts(tmp_path):
    store = ResourceStore(directory=tmp_path)
    first = store.publish(b"a,b\n1,2", media_type="text/csv")
    second = store.publish(
        BytesIO(b"a,b\n3,4"),
        resource_id=first.resource_id,
        expected_revision=1,
        media_type="text/csv",
    )
    assert first.revision == 1 and second.revision == 2
    assert first.sha256 != second.sha256
    assert store.read_chunk(first.resource_id, 1) == b"a,b\n1,2"
    assert store.read_chunk(first.resource_id, 2) == b"a,b\n3,4"
    assert store.current(first.resource_id) == second
    with pytest.raises(RevisionConflict):
        store.publish(b"stale", resource_id=first.resource_id, expected_revision=1)


def test_limits_and_invalid_inputs(tmp_path):
    store = ResourceStore(directory=tmp_path, max_resource_bytes=4, max_chunk_bytes=2)
    with pytest.raises(ValueError):
        store.publish(b"12345")
    snap = store.publish(b"1234")
    assert store.read_chunk(snap.resource_id, 1, offset=2, length=2) == b"34"
    with pytest.raises(ValueError):
        store.read_chunk(snap.resource_id, 1, length=3)
    with pytest.raises(ResourceNotFound):
        store.snapshot(snap.resource_id, 2)
    with pytest.raises(ValueError):
        store.publish(b"x", resource_id="../escape", expected_revision=1)


def test_events_and_shutdown():
    events = EventBus()
    seen = []
    events.on("resource:published", seen.append)
    store = ResourceStore(events=events)
    snap = store.publish(b"test")
    assert seen == [snap.to_dict()]
    path = store.open_path(snap.resource_id, 1)
    assert path.exists()
    store.close()
    assert not path.exists()
    store.close()
    with pytest.raises(RuntimeError):
        store.current(snap.resource_id)


def test_reopen_and_isolated_edit(tmp_path):
    store = ResourceStore(directory=tmp_path)
    first = store.publish(b"original")
    with store.edit(first.resource_id, 1) as draft:
        draft.seek(0)
        draft.write(b"modified")
        assert store.read_chunk(first.resource_id, 1) == b"original"
        draft.seek(0)
        second = store.publish(draft, resource_id=first.resource_id, expected_revision=1)
    store.close()
    reopened = ResourceStore(directory=tmp_path)
    assert reopened.current(first.resource_id) == second
    assert b"".join(reopened.iter_chunks(first.resource_id, 1, length=2)) == b"original"
    reopened.close()


def test_two_store_writers_are_serialized(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    first = ResourceStore(directory=tmp_path)
    second = ResourceStore(directory=tmp_path)
    snap = first.publish(b"initial")

    def update(store):
        try:
            return store.publish(b"update", resource_id=snap.resource_id, expected_revision=1)
        except RevisionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, (first, second)))
    assert sum(result is not None for result in results) == 1
    assert first.current(snap.resource_id).revision == 2
    first.close()
    second.close()


def test_failed_stream_does_not_publish_and_store_remains_usable(tmp_path):
    class Broken:
        def read(self, size):
            raise OSError("failed input")

    store = ResourceStore(directory=tmp_path)
    snap = store.publish(b"initial")
    with pytest.raises(OSError):
        store.publish(Broken(), resource_id=snap.resource_id, expected_revision=1)
    assert store.current(snap.resource_id) == snap
    assert not list(tmp_path.rglob("*.writing-*"))
    assert store.publish(b"retry", resource_id=snap.resource_id, expected_revision=1).revision == 2
    store.close()


def test_boolean_revision_is_rejected(tmp_path):
    store = ResourceStore(directory=tmp_path)
    snap = store.publish(b"initial")
    with pytest.raises(ValueError):
        store.publish(b"bad", resource_id=snap.resource_id, expected_revision=True)
    store.close()


def test_vela_instances_keep_workspace_storage_separate(tmp_path):
    from vela.core.app import VelaApp

    first = VelaApp(settings_module="tests.no_settings", resource_directory=tmp_path / "one")
    second = VelaApp(settings_module="tests.no_settings", resource_directory=tmp_path / "two")
    snapshot = first.resources.publish(b"one")
    with pytest.raises(ResourceNotFound):
        second.resources.current(snapshot.resource_id)
    first.close()
    second.close()
    reopened = VelaApp(settings_module="tests.no_settings", resource_directory=tmp_path / "one")
    assert reopened.resources.current(snapshot.resource_id) == snapshot
    reopened.close()


def test_retention_preserves_pins_and_never_reuses_revisions(tmp_path):
    store = ResourceStore(directory=tmp_path, retention_versions=2)
    first = store.publish(b"1")
    store.pin("workspace", first.resource_id, 1)
    for revision in range(1, 5):
        store.publish(
            str(revision + 1).encode(), resource_id=first.resource_id, expected_revision=revision
        )
    assert store.snapshot(first.resource_id, 1) == first
    with pytest.raises(ResourceNotFound):
        store.snapshot(first.resource_id, 2)
    store.unpin("workspace", first.resource_id, 1)
    assert store.prune(first.resource_id, keep_last=2) == [1]
    assert store.publish(b"6", resource_id=first.resource_id, expected_revision=5).revision == 6
    store.close()


def test_quota_failure_is_atomic_and_pruning_releases_capacity(tmp_path):
    from vela.resources import ResourceQuotaExceeded

    store = ResourceStore(directory=tmp_path, max_store_bytes=6)
    first = store.publish(b"123")
    with pytest.raises(ResourceQuotaExceeded):
        store.publish(b"1234", resource_id=first.resource_id, expected_revision=1)
    assert store.current(first.resource_id) == first
    assert store.usage()["bytes"] == 3
    store.publish(b"456", resource_id=first.resource_id, expected_revision=1)
    store.prune(first.resource_id)
    assert store.usage()["bytes"] == 3
    store.publish(b"789", resource_id=first.resource_id, expected_revision=2)
    store.close()


def test_integrity_fails_closed_without_removing_committed_data(tmp_path):
    from vela.resources import ResourceCorrupted

    store = ResourceStore(directory=tmp_path)
    snap = store.publish(b"valid")
    path = store.open_path(snap.resource_id, 1)
    path.write_bytes(b"wrong")
    with pytest.raises(ResourceCorrupted):
        store.verify(snap.resource_id, 1)
    store.close()
    with pytest.raises(ResourceCorrupted):
        ResourceStore(directory=tmp_path)
    assert path.read_bytes() == b"wrong"


def test_interrupted_writer_is_recovered_after_process_exit(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    code = """
import os,sys
from vela.resources import ResourceStore
class Interrupted:
    count = 0
    def read(self, size):
        self.count += 1
        if self.count > 1: os._exit(17)
        return b'x' * size
store = ResourceStore(directory=sys.argv[1])
store.publish(Interrupted())
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert result.returncode == 17
    assert list(tmp_path.rglob("*.writing-*"))
    store = ResourceStore(directory=tmp_path)
    assert store.usage()["revisions"] == 0
    assert not list(tmp_path.rglob("*.writing-*"))
    store.close()


def test_job_manager_publication_event_and_lifecycle_shutdown(tmp_path):
    from vela.core.app import VelaApp
    from vela.jobs import JobManager

    app = VelaApp(settings_module="tests.no_settings", resource_directory=tmp_path)
    seen = []
    app.events.on("resource:published", seen.append)
    with JobManager(io_workers=1) as jobs:
        snap = jobs.submit(app.resources.publish, b"async").result(timeout=5)
    assert seen == [snap.to_dict()]
    app.close()
    with pytest.raises(RuntimeError):
        app.resources.current(snap.resource_id)


def test_crash_between_blob_rename_and_catalog_commit_collects_orphan(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    script = """
import os,sys
from vela.resources import ResourceStore
store = ResourceStore(directory=sys.argv[1])
class InterruptedCatalog:
    def __getattr__(self,name): return getattr(original,name)
    def execute(self,query,*args):
        if query.startswith("INSERT INTO snapshots"): os._exit(18)
        return original.execute(query,*args)
original = store._db
store._db = InterruptedCatalog()
store.publish(b"renamed-but-not-committed")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert result.returncode == 18
    assert list(tmp_path.rglob("*.blob"))
    store = ResourceStore(directory=tmp_path)
    assert store.usage()["revisions"] == 0
    assert not list(tmp_path.rglob("*.blob"))
    store.close()
