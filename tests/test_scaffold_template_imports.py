from pathlib import Path

from vela.cli.commands import CommandRunner
from vela.cli.main import startproject

EXPECTED_IMPORT = "from vela.template_engine import render_template"
LEGACY_IMPORT = "from vela.shortcuts import render_template"


def test_startproject_uses_public_template_engine_import(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    project = startproject("sample-project")
    source = (project / "apps/home/views/home.py").read_text(encoding="utf-8")

    assert EXPECTED_IMPORT in source
    assert LEGACY_IMPORT not in source


def test_startapp_uses_public_template_engine_import(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CommandRunner().cmd_startapp(["forge"])
    assert result == 0

    source = Path("apps/forge/views/forge.py").read_text(encoding="utf-8")

    assert EXPECTED_IMPORT in source
    assert LEGACY_IMPORT not in source
