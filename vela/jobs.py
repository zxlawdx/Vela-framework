# SPDX-License-Identifier: MPL-2.0
"""Pool de tarefas IO/CPU para evitar trabalho pesado no thread de interface."""
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from threading import RLock


class JobManager:
    def __init__(self, io_workers=4, cpu_workers=0):
        self.io_pool = ThreadPoolExecutor(max_workers=io_workers,
                                          thread_name_prefix="vela-io")
        self.cpu_pool = (ProcessPoolExecutor(max_workers=cpu_workers)
                         if cpu_workers else None)
        self._lock = RLock()
        self._closed = False

    def submit(self, callback, *args, mode="io", on_done=None, **kwargs):
        """Callbacks de termino rodam em worker; GUI deve agendar no UI thread."""
        with self._lock:
            if self._closed:
                raise RuntimeError("JobManager ja foi encerrado")
            pool = self.io_pool if mode == "io" else self.cpu_pool if mode == "cpu" else None
            if pool is None:
                raise ValueError("Modo invalido ou CPU pool nao habilitado")
            future = pool.submit(callback, *args, **kwargs)
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
