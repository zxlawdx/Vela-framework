"""Native resource store regression tests."""
from io import BytesIO

import pytest

from vela.events import EventBus
from vela.resources import ResourceNotFound, ResourceStore, RevisionConflict


def test_publish_snapshot_is_immutable_and_conflicts(tmp_path):
    store = ResourceStore(directory=tmp_path)
    first = store.publish(b"a,b\n1,2", media_type="text/csv")
    second = store.publish(BytesIO(b"a,b\n3,4"), resource_id=first.resource_id,
                           expected_revision=1, media_type="text/csv")
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
