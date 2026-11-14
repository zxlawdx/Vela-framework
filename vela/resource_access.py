# SPDX-License-Identifier: MPL-2.0
"""Explicit, backend-owned capabilities for resource exchange.

Do not expose the broker or grant methods to JavaScript. Bind a client in a
trusted API handler; never accept an application name from a WebView request.
"""

from __future__ import annotations

import base64
from threading import RLock


class ResourceAccess:
    def __init__(self, store, registry):
        self.store = store
        self.registry = registry
        self._lock = RLock()
        self._grants = {}

    def client(self, app_name):
        if not any(app.name == app_name for app in self.registry):
            raise PermissionError("Application is not registered.")
        return ResourceClient(self, app_name)

    def grant(self, app_name, resource_id, revision):
        self.client(app_name)
        self.store.snapshot(resource_id, revision)
        with self._lock:
            self._grants.setdefault(app_name, set()).add((resource_id, revision))

    def revoke(self, app_name, resource_id, revision):
        with self._lock:
            self._grants.get(app_name, set()).discard((resource_id, revision))

    def check(self, app_name, resource_id, revision):
        with self._lock:
            if (resource_id, revision) not in self._grants.get(app_name, ()):
                raise PermissionError("Resource revision is not shared with this application.")


class ResourceClient:
    def __init__(self, broker, app_name):
        self._broker = broker
        self._app_name = app_name

    def metadata(self, resource_id, revision):
        self._broker.check(self._app_name, resource_id, revision)
        return self._broker.store.snapshot(resource_id, revision).to_dict()

    def read_chunk(self, resource_id, revision, *, offset=0, length=65536):
        self._broker.check(self._app_name, resource_id, revision)
        content = self._broker.store.read_chunk(resource_id, revision, offset=offset, length=length)
        return {
            "data": base64.b64encode(content).decode("ascii"),
            "offset": offset,
            "length": len(content),
            "encoding": "base64",
        }
