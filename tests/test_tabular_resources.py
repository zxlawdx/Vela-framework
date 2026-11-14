import pytest

from vela.resources import ResourceStore, RevisionConflict
from vela.tabular import TabularResources


def test_pandas_roundtrip_isolated_explicit_publication():
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    store = ResourceStore()
    tables = TabularResources(store)
    first = tables.publish_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    frame = tables.to_pandas(first.resource_id, 1)
    frame.loc[0, "a"] = 99
    assert tables.to_pandas(first.resource_id, 1).a.tolist() == [1, 2, 3]
    second = tables.publish_pandas(frame, resource_id=first.resource_id, expected_revision=1)
    assert second.revision == 2
    assert [batch.num_rows for batch in tables.batches(first.resource_id, 2, batch_size=2)] == [
        2,
        1,
    ]
    with pytest.raises(RevisionConflict):
        tables.publish_pandas(frame, resource_id=first.resource_id, expected_revision=1)
    store.close()


def test_arrow_roundtrip():
    pa = pytest.importorskip("pyarrow")
    store = ResourceStore()
    tables = TabularResources(store)
    snap = tables.publish_arrow(pa.table({"x": [1, 2], "y": [3, 4]}))
    batches = list(tables.batches(snap.resource_id, 1, columns=["y"]))
    assert batches[0].to_pydict() == {"y": [3, 4]}
    store.close()
