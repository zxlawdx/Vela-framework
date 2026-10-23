# SPDX-License-Identifier: MPL-2.0
import importlib
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vela.database import SQLiteStore
from vela.events import EventBus
from vela.exceptions import JobQueueFullError
from vela.jobs import JobManager
from vela.runtime.hotreload import HotReloadManager
from vela.runtime.lifecycle import LifecycleManager


class EventBusHardeningTests(unittest.TestCase):
    def test_listener_failure_does_not_stop_other_listeners(self):
        bus = EventBus()
        received = []

        def broken(payload):
            raise RuntimeError("boom")

        bus.on("x", broken)
        bus.on("x", received.append)
        bus.emit("x", "ok")
        self.assertEqual(received, ["ok"])

    def test_duplicate_listener_is_not_added_twice(self):
        bus = EventBus()
        received = []
        bus.on("x", received.append)
        bus.on("x", received.append)
        bus.emit("x", 1)
        self.assertEqual(received, [1])
        self.assertTrue(bus.off("x", received.append))
        self.assertFalse(bus.off("x", received.append))

    def test_invalid_payload_has_contextual_error(self):
        bus = EventBus()
        with self.assertRaises(TypeError):
            bus.emit("x", {"invalid": object()})

    def test_unicode_payload_without_window_is_supported(self):
        bus = EventBus()
        received = []
        bus.on("unicode", received.append)
        detail = bus.emit("unicode", {"text": "ação 🚀"})
        self.assertEqual(received, [{"text": "ação 🚀"}])
        self.assertEqual(detail["name"], "unicode")


class JobManagerHardeningTests(unittest.TestCase):
    def test_backpressure_rejects_when_queue_is_full(self):
        gate = threading.Event()
        jobs = JobManager(io_workers=1, max_pending_jobs=1)
        first = jobs.submit(lambda: gate.wait(2))
        try:
            with self.assertRaises(JobQueueFullError):
                jobs.submit(lambda: None)
        finally:
            gate.set()
            first.result(timeout=3)
            jobs.shutdown()

    def test_shutdown_is_idempotent_and_rejects_submit(self):
        jobs = JobManager(io_workers=1)
        jobs.shutdown()
        jobs.shutdown()
        with self.assertRaises(RuntimeError):
            jobs.submit(lambda: None)


class DatabaseHardeningTests(unittest.TestCase):
    def test_invalid_migration_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            migrations = root / "migrations"
            migrations.mkdir()
            (migrations / "001 bad.sql").write_text("SELECT 1;", encoding="utf-8")
            store = SQLiteStore("test", root / "app.db")
            with self.assertRaises(ValueError):
                store.migrate(migrations)

    def test_concurrent_migration_is_applied_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            migrations = root / "migrations"
            migrations.mkdir()
            (migrations / "001_setup.sql").write_text(
                "CREATE TABLE concurrent_data(id INTEGER PRIMARY KEY);",
                encoding="utf-8",
            )
            database = root / "app.db"
            barrier = threading.Barrier(2)
            results = []
            errors = []

            def run():
                try:
                    barrier.wait(timeout=2)
                    results.append(
                        SQLiteStore("test", database).migrate(migrations)
                    )
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertEqual(errors, [])
            self.assertEqual(sorted(len(result) for result in results), [0, 1])

    def test_broken_migration_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            migrations = root / "migrations"
            migrations.mkdir()
            (migrations / "001_bad.sql").write_text(
                "CREATE TABLE transient(id INTEGER); THIS IS INVALID SQL",
                encoding="utf-8",
            )
            store = SQLiteStore("test", root / "app.db")
            with self.assertRaises(Exception):
                store.migrate(migrations)
            with store.connect() as db:
                names = {
                    row[0]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertNotIn("transient", names)


class HotReloadTests(unittest.TestCase):
    def test_only_changed_tracked_module_is_reloaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hot_a.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "hot_b.py").write_text("VALUE = 1\n", encoding="utf-8")
            sys.path.insert(0, directory)
            try:
                a = importlib.import_module("hot_a")
                b = importlib.import_module("hot_b")
                manager = HotReloadManager(enabled=True)
                manager.track_module(a)
                manager.track_module(b)
                reloaded = []
                manager.add_reload_callback(
                    lambda name, module: reloaded.append(name)
                )
                (root / "hot_a.py").write_text("VALUE = 2\n", encoding="utf-8")
                now = time.time_ns() + 2_000_000_000
                os.utime(root / "hot_a.py", ns=(now, now))
                result = manager.refresh()
                self.assertEqual(result, ("hot_a",))
                self.assertEqual(reloaded, ["hot_a"])
                self.assertEqual(sys.modules["hot_a"].VALUE, 2)
                self.assertEqual(sys.modules["hot_b"].VALUE, 1)
            finally:
                sys.path.remove(directory)
                sys.modules.pop("hot_a", None)
                sys.modules.pop("hot_b", None)

    def test_production_disables_reload(self):
        with patch.dict(os.environ, {"VELA_PRODUCTION": "1"}):
            manager = HotReloadManager(enabled=True)
        self.assertFalse(manager.enabled)
        self.assertEqual(manager.refresh(), ())


class LifecycleTests(unittest.TestCase):
    def test_shutdown_is_reverse_order_and_idempotent(self):
        lifecycle = LifecycleManager()
        calls = []
        lifecycle.on_shutdown(lambda: calls.append("first"))
        lifecycle.on_shutdown(lambda: calls.append("second"))
        lifecycle.shutdown()
        lifecycle.shutdown()
        self.assertEqual(calls, ["second", "first"])


if __name__ == "__main__":
    unittest.main()
