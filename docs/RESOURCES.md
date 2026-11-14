# Versioned resources (native Vela service)

`VelaApp.resources` is an app-scoped `ResourceStore`. It stores immutable
binary snapshots in a temporary directory, uses optimistic revision checks,
and emits `resource:published` metadata through the existing EventBus.
It does **not** require pandas, Arrow, a database or a new runtime.

```python
snap = app.resources.publish(b"col\nvalue\n", media_type="text/csv")
previous = app.resources.snapshot(snap.resource_id, 1)
new = app.resources.publish(
    b"col\nother\n", resource_id=snap.resource_id,
    expected_revision=previous.revision, media_type="text/csv"
)
```

Python apps exchange `resource_id` and `revision` as stable handles.
Trusted services can open `app.resources.open_path(id, revision)` to load a
snapshot directly from disk. The WebView must **never** receive the path;
it should receive only `snapshot.to_dict()` and bounded, encoded chunks
from `read_chunk`. Avoid transferring entire datasets as JSON.

Important: this is a minimal foundational API, **not** a complete DataFrame
registry, transaction database, durable workspace, or secure streaming server.
Consumers own data conversion (CSV/Parquet/Arrow), authorization and application
specific edits. No implicit mutation: updates require an explicit expected
revision. Revisions are retained until `close()`; persistence between app
launches is not yet supported. The default store is cleaned during VelaApp
shutdown. Custom directories are not automatically deleted.

Performance: metadata current-revision lookup O(1) average, historical lookup
O(1), chunk read O(k) with k bounded by max_chunk_bytes, and publication O(n)
for n payload bytes (streaming in 1 MiB blocks). Disk use grows with retained
versions; plan retention policies before long-running production use.
