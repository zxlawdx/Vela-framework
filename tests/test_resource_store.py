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
