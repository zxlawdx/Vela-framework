"""New-project starter contracts, using the actual scaffold and bridge."""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from vela.cli.main import startproject

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return startproject("access-manager")


def test_project_name_structure_offline_assets_and_non_overwrite(project, capsys):
    assert project.name == "access-manager"
    expected = [
        "config/bridge.py",
        "config/wsgi.py",
        "manage.py",
        "apps/home/views/home.py",
        "apps/home/templates/home.html",
        "apps/home/static/starter.css",
        "apps/home/static/starter.js",
    ]
    for name in expected:
        assert (project / name).is_file()
    assert not (project / "apps/home/static/__init__.py").exists()
    assert not (project / "apps/login").exists()
    assert not (project / "apps/dashboard").exists()
    settings = (project / "config/settings.py").read_text(encoding="utf-8")
    assert 'APP_TITLE = "Access Manager"' in settings
    for path in project.rglob("*"):
        if path.suffix == ".py":
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
            assert "__VELA_PROJECT_TITLE__" not in source
    html = (project / "apps/home/templates/home.html").read_text(encoding="utf-8")
    assert "<html" not in html and "<body" not in html  # Vela shell owns the document.
    assert "static('home/starter.css')" in html
    assert "static('home/starter.js')" in html
    assert "v0.x.x" not in html
    for path in (project / "apps/home/static").glob("*"):
        assert "https://" not in path.read_text(encoding="utf-8")
    settings_path = project / "config/settings.py"
    settings_path.write_text("# user project", encoding="utf-8")
    assert startproject("access-manager") is None
    assert settings_path.read_text() == "# user project"


def load_bridge(project):
    spec = importlib.util.spec_from_file_location(
        "generated_starter_bridge", project / "config/bridge.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_counter_validates_bridge_arguments(project):
    bridge = load_bridge(project).StarterBridge()
    assert bridge.ping() == "pong"
    assert bridge.increment_counter(0) == 1
    assert bridge.increment_counter(999999) == 1000000
    for bad in [True, False, "1", None, {}, [], 1.5, -1, 1000000]:
        with pytest.raises(ValueError):
            bridge.increment_counter(bad)


def test_fixed_actions_do_not_accept_commands_or_paths(project, monkeypatch):
    module = load_bridge(project)
    bridge = module.StarterBridge()
    calls = []
    monkeypatch.setattr(module.webbrowser, "open", lambda url, **kw: calls.append(url) or True)
    assert bridge.starter_action("docs")["ok"]
    assert calls == [module.STARTER_LINKS["docs"]]
    for bad in ["/tmp", "../", "project;rm -rf /", {}, None]:
        assert not bridge.starter_action(bad)["ok"]
    assert len(calls) == 1
    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module.subprocess, "Popen", lambda args, **kw: calls.append((args, kw)))
    assert bridge.starter_action("project")["ok"]
    args, kw = calls[-1]
    assert args == ["xdg-open", str(project.resolve())]
    assert kw["shell"] is False


def test_generated_project_boots_routes_and_real_bridge(project):
    code = """
from pathlib import Path
from unittest.mock import patch
from config import wsgi
from vela.core.app import VelaApp
from vela.core.api_server import ApiServer

class Window:
    def __init__(self, **kwargs): self.bridge=kwargs['bridge']
    def run(self):
        assert self.bridge.ping() == 'pong'
        assert self.bridge.increment_counter(41) == 42
        page=self.bridge.navigate('/home')
        assert page['ok'] and page['layout']=='blank'
        assert 'Access Manager' in page['html']
        assert '{{' not in page['html'] and '__VELA_' not in page['html']
        assert '/__vela__/static/home/starter.css' in page['html']
        assert Path('staticfiles/home/starter.js').is_file()
        Path('rendered.html').write_text(page['html'],encoding='utf-8')
    def stop(self): pass

def factory(**kwargs):
    app=VelaApp(**kwargs,window_backend_class=Window)
    app._config['api']['port']=0
    app._config['api']['server']='bottle'
    return app
with patch.object(wsgi,'VelaApp',side_effect=factory):
    wsgi.run()
"""
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_starter_files_available_as_package_resources():
    template = files("vela").joinpath("templates/project")
    for path in [
        "config/bridge.py",
        "apps/home/templates/home.html",
        "apps/home/static/starter.js",
        "apps/home/static/starter.css",
    ]:
        assert template.joinpath(path).is_file()
