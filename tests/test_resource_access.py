import base64

import pytest

from vela.apps import AppConfig, AppRegistry
from vela.resource_access import ResourceAccess
from vela.resources import ResourceStore


def test_explicit_revision_scoped_grants_and_revocation():
    registry = AppRegistry()
    registry.register(AppConfig(name="data", module="apps.data"))
    store = ResourceStore(max_chunk_bytes=4)
    access = ResourceAccess(store, registry)
    with pytest.raises(PermissionError):
        access.client("unknown")
    client = access.client("data")
    snap = store.publish(b"private")
    with pytest.raises(PermissionError):
        client.metadata(snap.resource_id, 1)
    access.grant("data", snap.resource_id, 1)
    assert "path" not in client.metadata(snap.resource_id, 1)
    assert base64.b64decode(client.read_chunk(snap.resource_id, 1, length=4)["data"]) == b"priv"
    with pytest.raises(ValueError):
        client.read_chunk(snap.resource_id, 1, length=5)
    store.publish(b"new", resource_id=snap.resource_id, expected_revision=1)
    with pytest.raises(PermissionError):
        client.metadata(snap.resource_id, 2)
    access.revoke("data", snap.resource_id, 1)
    with pytest.raises(PermissionError):
        client.metadata(snap.resource_id, 1)
    store.close()
