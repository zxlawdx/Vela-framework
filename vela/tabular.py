# SPDX-License-Identifier: MPL-2.0
"""Optional tabular adapters. Heavy libraries are imported only on use."""

from __future__ import annotations

import tempfile

from vela.resources import ResourceStore


class TabularResources:
    def __init__(self, store: ResourceStore):
        self.store = store

    def publish_pandas(self, frame, **publication):
        """Serialize to a disk-backed Parquet draft, then publish explicitly."""
        with tempfile.TemporaryFile(mode="w+b") as stream:
            frame.to_parquet(stream, index=False)
            stream.seek(0)
            return self.store.publish(
                stream, media_type="application/vnd.apache.parquet", **publication
            )

    def to_pandas(self, resource_id, revision, *, columns=None):
        import pandas as pd

        return pd.read_parquet(self.store.open_path(resource_id, revision), columns=columns)

    def publish_arrow(self, table, **publication):
        import pyarrow.parquet as pq

        with tempfile.TemporaryFile(mode="w+b") as stream:
            pq.write_table(table, stream)
            stream.seek(0)
            return self.store.publish(
                stream, media_type="application/vnd.apache.parquet", **publication
            )

    def batches(self, resource_id, revision, *, batch_size=65536, columns=None):
        """Lazy Parquet record batches; memory is bounded by decoded batch size."""
        if type(batch_size) is not int or not 1 <= batch_size <= 1_000_000:
            raise ValueError("Invalid batch size.")
        import pyarrow.parquet as pq

        with pq.ParquetFile(self.store.open_path(resource_id, revision)) as parquet:
            yield from parquet.iter_batches(batch_size=batch_size, columns=columns)

    def page(self, resource_id, revision, *, offset=0, limit=100, columns=None):
        """Read an Arrow page, skipping complete Parquet row groups by metadata."""
        if (
            type(offset) is not int
            or offset < 0
            or type(limit) is not int
            or not 1 <= limit <= 1000
        ):
            raise ValueError("Invalid page bounds.")
        import pyarrow as pa
        import pyarrow.parquet as pq

        with pq.ParquetFile(self.store.open_path(resource_id, revision)) as parquet:
            schema = parquet.schema_arrow
            if columns is not None:
                schema = pa.schema([schema.field(name) for name in columns])
            groups = []
            skipped = 0
            for index in range(parquet.num_row_groups):
                count = parquet.metadata.row_group(index).num_rows
                if skipped + count > offset:
                    groups = list(range(index, parquet.num_row_groups))
                    break
                skipped += count
            batches = []
            remaining = limit
            local_offset = offset - skipped
            if groups:
                for batch in parquet.iter_batches(
                    batch_size=1000, row_groups=groups, columns=columns
                ):
                    if local_offset >= batch.num_rows:
                        local_offset -= batch.num_rows
                        continue
                    selected = batch.slice(
                        local_offset, min(remaining, batch.num_rows - local_offset)
                    )
                    batches.append(selected)
                    remaining -= selected.num_rows
                    local_offset = 0
                    if remaining == 0:
                        break
            return pa.Table.from_batches(batches, schema=schema)
