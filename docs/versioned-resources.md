# Native versioned resources

`VelaApp.resources` owns disk-backed immutable snapshots. Set
`RESOURCE_DIRECTORY` in settings to retain snapshots across launches; otherwise
shutdown deletes the temporary store. A host embedding several workspaces can pass
`VelaApp(resource_directory=path)` without modifying process-global settings. SQLite indexes metadata and serializes
writers (including other processes using the same directory). Publication streams
in 1 MiB blocks, fsyncs the blob, renames it, then commits its metadata. A crash
before metadata commit can leave an unreferenced blob; it is never exposed by the
catalog. This is local storage, not a distributed/object store or a backup system.
Use a directory writable only by the application user; do not place it on a
network filesystem or mutate its contents externally. Filesystem/power-loss
recovery and quota/retention policies remain follow-up work.

```python
snap = app.resources.publish(binary_stream, media_type="text/csv")
with app.resources.edit(snap.resource_id, snap.revision) as draft:
    # Modify only this private disk-backed draft, then explicitly publish:
    draft.seek(0)
    updated = app.resources.publish(draft, resource_id=snap.resource_id,
                                    expected_revision=snap.revision)
```

`edit()` never auto-publishes, even on successful exit. Truncate a shortened draft
before publishing. Conflicting writers receive `RevisionConflict`; retry requires
an explicit merge/rebase decision. Failed input streams leave no visible revision.
`open_path()` is trusted-backend-only and read-only **by contract**, not an OS
sandbox. Never give its path to the WebView or untrusted Python code.

## Sharing and transport

Register applications normally with `AppConfig`. Trusted backend composition code
can grant access to an exact immutable revision:

```python
app.resource_access.grant("data", snap.resource_id, snap.revision)
client = app.resource_access.client("data")
metadata = client.metadata(snap.resource_id, snap.revision)
chunk = client.read_chunk(snap.resource_id, snap.revision, length=65536)
```

Clients return metadata and bounded base64 chunks, never filesystem paths. New
revisions require a new explicit grant. Revocation blocks subsequent calls. Grants
are in-memory session capabilities and intentionally do not survive restart. Bind
a client to a trusted API handler; do not accept a caller-provided application
name. Keep existing session-token/origin checks on transport endpoints. The broker
is not exposed automatically on the bridge and is not a Python code sandbox.

Long operations should use the existing `JobManager.submit` API; do not add a
second executor. `resource:published` uses the existing EventBus and carries only
metadata, after commit. VelaApp closes the store through its existing lifecycle.

## Optional tabular adapters

Install `vela-framework[tabular]` to use `app.tabular.publish_pandas(frame)`,
`to_pandas(id, revision, columns=...)`, `publish_arrow(table)` and lazy
`batches(id, revision, batch_size=65536, columns=...)`. Imports are deferred;
base Vela does not require pandas or Arrow. `page(id, revision, offset=0, limit=100,
columns=...)` returns a bounded Arrow table (limit <= 1000), skipping complete
Parquet row groups through metadata. Reading an offset within a row group still
decodes preceding batches; this is not a constant-time arbitrary-row index. Exchange handles between apps.
Parquet batches permit bounded processing and column projection. `to_pandas`
materializes the selected frame and allocates memory proportional to its decoded
size; it is not a zero-copy promise. Publishing a modified frame requires an
explicit resource ID and expected revision. Private conversion files are cleaned
on success and failure.

## Complexity and measured limits

For n payload bytes and v revisions: publication O(n + log v) time, O(1 MiB)
Python buffering; metadata lookup O(log v) time with SQLite indexes, bounded SQLite
page cache; chunk read O(k + log v) time and O(k) memory. Metadata stays on disk,
not in an unbounded Python registry. Blob caching uses the OS page cache rather
than a duplicate framework payload cache. Storage grows O(total retained bytes).
Draft editing copies O(n) bytes on disk; no copy-on-write guarantee is made.

Run `PYTHONPATH=. python benchmarks/bench_resources.py`. The checked-in Linux
JSON files compare PR head b1fcc68 with this implementation for 1k/10k/100k/1M CSV
records. These are single-run diagnostics (warm filesystem, tracemalloc Python
allocations only), not a statistical speedup claim or a GUI/startup benchmark.
At 1M records (~19.8 MB), publication measured 54.35 ms before and 60.80 ms after;
Python peak stayed ~2.10 MB. Durable indexing has a cost. No Open Doc performance
improvement is established by these measurements.

Tests cover reopening, concurrent writers, conflicts, isolated drafts, failed
streams, revision grants, revocation and optional tabular roundtrips. CI runs the
suite on Linux and Windows; a locally passing Linux run is not evidence that the
Windows CI or packaged GUI builds have passed.
