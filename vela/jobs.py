# SPDX-License-Identifier: MPL-2.0
"""Pools de IO/CPU com backpressure e shutdown idempotente."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import BoundedSemaphore, RLock

from vela.exceptions import JobQueueFullError


class JobManager:
    def __init__(
        self,
        io_workers: int = 4,
        cpu_workers: int = 0,
        max_pending_jobs: int | None = 128,
        block_when_full: bool = False,
    ):
        if io_workers <= 0 or cpu_workers < 0:
            raise ValueError("Quantidade de workers inválida.")
        if max_pending_jobs is not None and max_pending_jobs <= 0:
            raise ValueError("max_pending_jobs deve ser positivo ou None.")
        self.io_pool = ThreadPoolExecutor(
            max_workers=io_workers, thread_name_prefix="vela-io"
        )
        self.cpu_pool = (
            ProcessPoolExecutor(max_workers=cpu_workers) if cpu_workers else None
        )
        self._lock = RLock()
        self._closed = False
        self._block_when_full = bool(block_when_full)
        self._slots = BoundedSemaphore(max_pending_jobs) if max_pending_jobs else None

    def submit(self, callback, *args, mode="io", on_done=None, **kwargs):
        with self._lock:
            if self._closed:
                raise RuntimeError("JobManager já foi encerrado.")
            pool = (
                self.io_pool
                if mode == "io"
                else self.cpu_pool
                if mode == "cpu"
                else None
            )
            if pool is None:
                raise ValueError("Modo inválido ou CPU pool não habilitado.")
            if self._slots is not None and not self._slots.acquire(
                blocking=self._block_when_full
            ):
                raise JobQueueFullError(
                    "Fila de jobs do Vela atingiu o limite configurado."
                )
            try:
                future = pool.submit(callback, *args, **kwargs)
            except Exception:
                if self._slots is not None:
                    self._slots.release()
                raise
            if self._slots is not None:
                future.add_done_callback(lambda _: self._slots.release())
            if on_done:
                future.add_done_callback(on_done)
            return future

    def shutdown(self, wait=True):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self.io_pool.shutdown(wait=wait, cancel_futures=True)
        if self.cpu_pool:
            self.cpu_pool.shutdown(wait=wait, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.shutdown()
