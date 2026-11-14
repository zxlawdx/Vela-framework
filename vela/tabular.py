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
