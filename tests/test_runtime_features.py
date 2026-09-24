"""Integração entre eventos, jobs, SQLite, plugins e templates."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vela.database import SQLiteStore
from vela.desktop import check_for_updates, version_tuple
from vela.events import EventBus
from vela.jobs import JobManager
from vela.plugins import register_build_hook, apply_build_hooks, _build_hooks
from vela.template_engine.engine import render_template, _read_template_cached


class RuntimeFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_sqlite_migrations_are_idempotent_and_checked(self):
        folder = self.root / "migrations"
        folder.mkdir()
        sql = folder / "001_setup.sql"
        sql.write_text("CREATE TABLE messages(id INTEGER PRIMARY KEY, content TEXT);")
        database = SQLiteStore("test-vela", self.root / "app.db")
        self.assertEqual(database.migrate(folder), ["001_setup.sql"])
        self.assertEqual(database.migrate(folder), [])
        with database.connect() as db:
            tables = {x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("messages", tables)
        sql.write_text("CREATE TABLE messages(id INTEGER PRIMARY KEY);")
        with self.assertRaises(RuntimeError):
            database.migrate(folder)

    def test_event_bus_serializes_python_payload_for_javascript(self):
        received = []
        window = type("Window", (), {"evaluate_js": lambda self, js: received.append(js)})()
        bus = EventBus()
        local = []
        bus.on("progress", local.append)
        bus.attach_window(window)
        data = {"text": 'hello"); console.log("injection'}
        bus.emit("progress", data)
        self.assertEqual(local, [data])
        self.assertIn("new CustomEvent('vela:event'", received[0])
        self.assertIn("console.log", received[0])
        self.assertIn(r"\"injection", received[0])
        bus.off("progress", local.append)

    def test_io_tasks_return_result(self):
        with JobManager(io_workers=2) as jobs:
            result = jobs.submit(str.upper, "ola").result(timeout=3)
            self.assertEqual(result, "OLA")

    def test_build_plugins_are_opt_in_and_ordered(self):
        _build_hooks.clear()
        @register_build_hook
        def add_argument(plan):
            plan["command"].append("--test-custom")
        with patch("vela.plugins.entry_points", return_value=[]):
            plan = {"command": ["python"]}
            apply_build_hooks(plan)
            self.assertEqual(plan["command"][-1], "--test-custom")
        _build_hooks.clear()

    def test_updater_checks_only_when_explicitly_called(self):
        response = json.dumps({"tag_name": "v0.3.0",
                               "html_url": "https://github.com/example/app/releases/tag/v0.3.0",
                               "published_at": "2026-09-24T12:00:00Z"}).encode()
        with patch("vela.desktop.urlopen", return_value=io.BytesIO(response)) as urlopen:
            result = check_for_updates("example/app", "0.2.0")
            self.assertTrue(result["available"])
            urlopen.assert_called_once()
        self.assertEqual(version_tuple("v0.10.1"), (0, 10, 1))
        with self.assertRaises(ValueError):
            check_for_updates("../invalid", "0.2.0")

    def test_template_cache_invalidates_on_file_change(self):
        template = self.root / "page.html"
        template.write_text("<p>{{ label }}</p>", encoding="utf-8")
        _read_template_cached.cache_clear()
        current = Path.cwd()
        os.chdir(self.root)
        try:
            first = render_template("page.html", {"label": "Primeiro"})
            hits = _read_template_cached.cache_info().hits
            second = render_template("page.html", {"label": "Segundo"})
            self.assertIn("Primeiro", first)
            self.assertIn("Segundo", second)
            self.assertEqual(_read_template_cached.cache_info().hits, hits + 1)
            template.write_text("<div>{{ label }}</div>", encoding="utf-8")
            self.assertIn("<div>", render_template("page.html", {"label": "Novo"}))
        finally:
            os.chdir(current)


if __name__ == "__main__":
    unittest.main()
