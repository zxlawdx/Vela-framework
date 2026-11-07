# SPDX-License-Identifier: MPL-2.0
"""Turn a tested PyInstaller bundle into a single distribution file."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from vela.cli.install import safe_slug


def installer_name(meta):
    version = meta["version"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+!-]{0,79}", version):
        raise ValueError("APP_VERSION inválida para o nome do instalador.")
    return f'{safe_slug(meta["slug"])}-{meta["platform"]}-{platform.machine()}-{version}-Setup'


def find_iscc():
    configured = os.environ.get("VELA_ISCC")
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError("VELA_ISCC deve apontar para ISCC.exe.")
    executable = shutil.which("ISCC.exe")
    if executable:
        return Path(executable)
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        if base := os.environ.get(variable):
            for folder in ("Inno Setup 6", "Programs/Inno Setup 6"):
                path = Path(base) / folder / "ISCC.exe"
                if path.is_file():
                    return path
    raise FileNotFoundError(
        "Instale Inno Setup 6 na máquina de build ou aponte VELA_ISCC para ISCC.exe."
    )


def _inno_text(value):
    value = str(value)
    if any(ord(char) < 32 for char in value):
        raise ValueError("Metadados do instalador não podem conter caracteres de controle.")
    return value.replace("{", "{{").replace('"', '""')


def windows_script(bundle, meta, output, name, icon=None):
    slug = safe_slug(meta["slug"])
    exe = _inno_text(meta["executable"])
    title = _inno_text(meta["name"])
    lines = [
        "[Setup]",
        f"AppId=Vela.{slug}",
        f'AppName="{title}"',
        f'AppVersion="{_inno_text(meta["version"])}"',
        f"DefaultDirName={{localappdata}}\\Programs\\Vela\\{slug}",
        "PrivilegesRequired=lowest",
        "DisableProgramGroupPage=yes",
        "WizardStyle=modern",
        "Compression=lzma2",
        "SolidCompression=yes",
        "CloseApplications=yes",
        "RestartApplications=no",
        f"UninstallDisplayIcon={{app}}\\{exe}",
        f'OutputDir="{_inno_text(output)}"',
        f"OutputBaseFilename={name}",
    ]
    if meta.get("author"):
        lines.append(f'AppPublisher="{_inno_text(meta["author"])}"')
    if icon:
        lines.append(f'SetupIconFile="{_inno_text(icon)}"')
    lines.extend(
        [
            "",
            "[Files]",
            f'Source: "{_inno_text(bundle)}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs',
            "",
            "[Icons]",
            f'Name: "{{autoprograms}}\\{slug}"; Filename: "{{app}}\\{exe}"; WorkingDir: "{{app}}"',
            "",
            "[Run]",
            f'Filename: "{{app}}\\{exe}"; WorkingDir: "{{app}}"; Description: "Abrir {title}"; Flags: nowait postinstall skipifsilent',
        ]
    )
    return "\n".join(lines) + "\n"


def build_windows_installer(bundle, meta, output, icon, compiler):
    name = installer_name(meta)
    with TemporaryDirectory(prefix="vela-inno-", dir=output) as directory:
        stage = Path(directory)
        script = stage / "setup.iss"
        script.write_text(windows_script(bundle, meta, stage, name, icon), encoding="utf-8-sig")
        subprocess.run([str(compiler), str(script)], check=True)
        compiled = stage / (name + ".exe")
        if not compiled.is_file():
            raise RuntimeError("O Inno Setup não produziu o instalador esperado.")
        target = output / compiled.name
        compiled.replace(target)
    return target


def build_linux_installer(bundle, meta, output):
    target = output / (installer_name(meta) + ".run")
    executable = safe_slug(meta["executable"])
    header = r"""#!/bin/sh
set -eu
stage=$(mktemp -d "${TMPDIR:-/tmp}/vela-setup.XXXXXXXX")
trap 'rm -rf -- "$stage"' EXIT
trap 'exit 1' HUP INT TERM
printf '%s\n' '[1/3] Extraindo o aplicativo...'
tail -n +PAYLOAD_LINE -- "$0" | tar -xzf - -C "$stage"
printf '%s\n' '[2/3] Instalando aplicativo e atalhos...'
"$stage/bundle/EXECUTABLE" --vela-install
printf '%s\n' '[3/3] Instalação concluída.'
exit 0
"""
    header = header.replace("PAYLOAD_LINE", str(len(header.splitlines()) + 1))
    header = header.replace("EXECUTABLE", executable)
    with TemporaryDirectory(prefix="vela-run-", dir=output) as directory:
        stage = Path(directory) / target.name
        with stage.open("wb") as stream:
            stream.write(header.encode("utf-8"))
            with tarfile.open(fileobj=stream, mode="w|gz") as archive:
                archive.add(bundle, arcname="bundle")
        stage.chmod(0o755)
        stage.replace(target)
    return target
