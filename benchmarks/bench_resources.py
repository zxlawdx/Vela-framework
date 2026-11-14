"""Run: PYTHONPATH=. python benchmarks/bench_resources.py. JSON diagnostic output."""

import json
import platform
import tempfile
import time
import tracemalloc

from vela.resources import ResourceStore


def measure(rows):
    # Build input outside measurement; benchmark publication rather than generator.
    with tempfile.TemporaryFile(mode="w+b") as source:
        for row in range(rows):
            source.write(f"{row},value-{row}\n".encode())
        source.seek(0)
        with tempfile.TemporaryDirectory() as directory:
            store = ResourceStore(directory=directory)
            tracemalloc.start()
            start = time.perf_counter()
            snapshot = store.publish(source, media_type="text/csv")
            publish_ms = (time.perf_counter() - start) * 1000
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            start = time.perf_counter()
            total = 0
            while chunk := store.read_chunk(snapshot.resource_id, 1, offset=total):
                total += len(chunk)
            stream_ms = (time.perf_counter() - start) * 1000
            assert total == snapshot.size
            store.close()
            return dict(
                rows=rows,
                bytes=total,
                publish_ms=publish_ms,
                stream_ms=stream_ms,
                python_peak_bytes=peak,
            )


if __name__ == "__main__":
    print(
        json.dumps(
            dict(
                platform=platform.platform(),
                python=platform.python_version(),
                results=[measure(n) for n in (1000, 10000, 100000, 1000000)],
            ),
            indent=2,
        )
    )
