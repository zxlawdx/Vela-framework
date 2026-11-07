# SPDX-License-Identifier: MPL-2.0
"""Exercise single-file distribution without requiring a GUI or admin rights."""

import shutil
import subprocess
import sys

import pytest

from vela.cli.standalone_installer import (
    build_linux_installer,
    build_windows_installer,
    windows_script,
)


def test_windows_installer_includes_entire_bundle_and_project_icon(tmp_path, monkeypatch):
    meta = {
        "name": "Minha Aplicação",
        "slug": "Minha-App",
        "version": "1.2.0",
        "platform": "windows",
        "executable": "Minha-App.exe",
    }
    icon = tmp_path / "Logo do app.ico"
    compiler = tmp_path / "ISCC.exe"
    bundle = tmp_path / "bundle com espaços"

    def compile_script(command, *, check):
        assert command[0] == str(compiler) and check
        from pathlib import Path

        script = Path(command[1])
        text = script.read_text(encoding="utf-8-sig")
        assert "AppId=Vela.Minha-App" in text
        assert f'SetupIconFile="{icon}"' in text
        assert f'Source: "{bundle}\\*"' in text
        assert "recursesubdirs createallsubdirs" in text
        assert "PrivilegesRequired=lowest" in text
        assert 'AppName="Minha Aplicação"' in text
        stem = next(
            line.split("=", 1)[1]
            for line in text.splitlines()
            if line.startswith("OutputBaseFilename=")
        )
        (script.parent / (stem + ".exe")).write_bytes(b"compiled")

    monkeypatch.setattr(subprocess, "run", compile_script)
    installer = build_windows_installer(bundle, meta, tmp_path, icon, compiler)
    assert installer.name.endswith("-Setup.exe")
    assert installer.read_bytes() == b"compiled"
    with pytest.raises(ValueError, match="controle"):
        windows_script(bundle, {**meta, "name": "Nome\n[Run]"}, tmp_path, "setup")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux self-extractor")
def test_linux_setup_is_standalone_and_preserves_bundle_tree(tmp_path):
    bundle = tmp_path / "bundle"
    destination = tmp_path / "installed"
    bundle.mkdir()
    for name in (
        "apps/demo/templates/index.html",
        "staticfiles/demo/main.css",
        "staticfiles/demo/main.js",
    ):
        file = bundle / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(name)
    (bundle / "staticfiles/demo/link.js").symlink_to("main.js")
    executable = bundle / "Demo"
    executable.write_text(
        '#!/bin/sh\nset -eu\n[ "$1" = --vela-install ]\n'
        'cp -a "$(dirname "$0")" "$VELA_TEST_DESTINATION"\n'
    )
    executable.chmod(0o755)
    meta = {"slug": "Demo", "version": "1.0", "platform": "linux", "executable": "Demo"}
    installer = build_linux_installer(bundle, meta, tmp_path)
    shutil.rmtree(bundle)
    import os

    result = subprocess.run(
        [str(installer)],
        cwd=tmp_path,
        env={**os.environ, "VELA_TEST_DESTINATION": str(destination)},
        check=True,
        capture_output=True,
        text=True,
    )
    assert "[3/3]" in result.stdout
    assert (destination / "apps/demo/templates/index.html").is_file()
    assert (destination / "staticfiles/demo/main.css").is_file()
    assert (destination / "staticfiles/demo/link.js").is_symlink()
    assert (destination / "staticfiles/demo/link.js").read_text() == "staticfiles/demo/main.js"


def test_installer_build_plan_keeps_project_asset_pipeline_and_uses_qt_on_windows(
    tmp_path, monkeypatch
):
    from vela.cli import build

    (tmp_path / "manage.py").touch()
    (tmp_path / "config").mkdir()
    (tmp_path / "config/settings.py").write_text(
        "ASSETS = {'node': {'scripts': ['bundle']}, 'tailwind': False}\n"
    )
    monkeypatch.setattr(build, "platform_id", lambda: "windows")
    plan = build.build_app(
        tmp_path, build.BuildOptions(installer=True, dry_run=True, resolve_dependencies=True)
    )
    assert plan["gui"] == "qt6"
    assert plan["asset_config"]["node"]["scripts"] == ["bundle"]
    assert not (tmp_path / "dist").exists()
