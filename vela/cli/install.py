# SPDX-License-Identifier: MPL-2.0
"""Instalacao desktop e atalhos. Nao solicita nem armazena senhas."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def safe_slug(slug):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", slug):
        raise ValueError("Identificador de aplicativo invalido")
    return slug


def read_manifest(bundle):
    path = Path(bundle) / ".vela-app.json"
    if not path.is_file():
        raise FileNotFoundError(f"Manifesto do build ausente: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    safe_slug(data["slug"])
    if Path(data.get("executable", "")).name != data.get("executable"):
        raise ValueError("Caminho do executavel invalido")
    return data


def linux_paths(slug, scope="user"):
    slug = safe_slug(slug)
    if scope == "system":
        return (Path("/opt/vela") / slug,
                Path("/usr/share/applications") / (slug + ".desktop"),
                Path("/usr/share/mime/packages") / (slug + ".xml"))
    if scope != "user":
        raise ValueError("Escopo valido: user ou system")
    home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return (home / "vela-apps" / slug, home / "applications" / (slug + ".desktop"),
            home / "mime/packages" / (slug + ".xml"))


def desktop_entry(meta, install_root):
    """Gera arquivo freedesktop sem comandos de shell arbitrarios."""
    def text(value):
        return str(value).replace("\r", " ").replace("\n", " ").replace("%", "%%")
    def quote_path(path):
        escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
        return '"' + escaped + '"'

    icon = install_root / meta["icon"] if meta.get("icon") else None
    lines = [
        "[Desktop Entry]", "Type=Application",
        "Name=" + text(meta["name"]),
        "Comment=" + text(meta.get("description", "")),
        "Exec=" + quote_path(install_root / meta["executable"]) + " %F",
        "Path=" + str(install_root),
        "Terminal=false",
        "Categories=Development;Graphics;",
        "StartupWMClass=" + meta["slug"],
        "Icon=" + str(icon) if icon else "Icon=applications-graphics",
    ]
    exts = meta.get("file_extensions", [])
    if exts:
        lines.append("MimeType=application/x-vela-" + meta["slug"].lower() + ";")
    return "\n".join(lines) + "\n"


def _write_mime(meta, destination):
    patterns = meta.get("file_extensions", [])
    if not patterns:
        return
    from xml.sax.saxutils import escape
    destination.parent.mkdir(parents=True, exist_ok=True)
    glob_elements = []
    for extension in patterns:
        if not re.fullmatch(r"\.[A-Za-z0-9.]{1,40}", extension):
            raise ValueError("Extensao de arquivo invalida: " + extension)
        glob_elements.append('<glob pattern="*' + escape(extension) + '"/>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
           '<mime-type type="application/x-vela-' + meta["slug"].lower() + '">\n'
           '<comment>' + escape(meta["name"]) + '</comment>\n' +
           "\n".join(glob_elements) + '\n</mime-type></mime-info>\n')
    destination.write_text(xml, encoding="utf-8")


def _elevate_linux(bundle):
    pkexec = shutil.which("pkexec")
    if not pkexec:
        raise RuntimeError("pkexec nao encontrado. Instale polkit para instalacao global.")
    # Polkit exibe o dialogo de elevacao nativo; nenhuma senha passa pelo Vela.
    if getattr(sys, "frozen", False):
        # O executavel PyInstaller nao interpreta "python -m".
        # Reexecuta o proprio binario, que entende --vela-install.
        cmd = [pkexec, sys.executable, "--vela-install", "--scope=system"]
    else:
        cmd = [pkexec, sys.executable, "-m", "vela.cli.install",
               "--bundle", str(Path(bundle).resolve()), "--scope", "system"]
    subprocess.run(cmd, check=True)


def install_bundle(bundle, scope="user", notify=print):
    bundle = Path(bundle).resolve()
    meta = read_manifest(bundle)
    executable = bundle / meta["executable"]
    if not executable.is_file():
        raise FileNotFoundError(f"Executavel nao encontrado: {executable}")
    system = platform.system()
    if system == "Linux":
        if scope == "system" and os.geteuid() != 0:
            notify("O polkit solicitara autorizacao administrativa.")
            return _elevate_linux(bundle)
        target, desktop, mime = linux_paths(meta["slug"], scope=scope)
        if target != bundle:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # instalacao anterior e substituida somente neste diretorio conhecido.
                shutil.rmtree(target)
            shutil.copytree(bundle, target)
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(desktop_entry(meta, target), encoding="utf-8")
        desktop.chmod(0o644)
        if meta.get("file_extensions"):
            _write_mime(meta, mime)
            tool = shutil.which("update-mime-database")
            if tool:
                subprocess.run([tool, str(mime.parent.parent)], check=False)
        notify(f"Aplicativo instalado: {target}")
        notify(f"Atalho de menu: {desktop} (voce pode fixar o aplicativo na barra)")
        return target

    if system == "Windows":
        if scope == "system":
            raise NotImplementedError(
                "Instalacao global Windows depende de instalador MSI/Inno Setup")
        localapp = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        target = localapp / "Programs" / "Vela" / meta["slug"]
        if bundle != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(bundle, target)
        start_menu = Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming")))
        start_menu = start_menu / "Microsoft/Windows/Start Menu/Programs"
        start_menu.mkdir(parents=True, exist_ok=True)
        # O nome exibido pode ser livre; o arquivo de atalho usa slug validado.
        shortcut = start_menu / (meta["slug"] + ".lnk")
        def ps_string(value):
            return "'" + str(value).replace("'", "''") + "'"
        script = (
            "$shell=New-Object -ComObject WScript.Shell; "
            f"$s=$shell.CreateShortcut({ps_string(shortcut)}); "
            f"$s.TargetPath={ps_string(target / meta['executable'])}; "
            f"$s.WorkingDirectory={ps_string(target)}; "
        )
        if meta.get("icon"):
            script += f"$s.IconLocation={ps_string(target / meta['icon'])}; "
        script += "$s.Save()"
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
        notify(f"Instalado em {target}; atalho: {shortcut}")
        return target
    if system == "Darwin":
        raise NotImplementedError("Instalador macOS .app em desenvolvimento")
    raise RuntimeError("Sistema nao suportado: " + system)


def uninstall_app(slug, scope="user"):
    slug = safe_slug(slug)
    if platform.system() != "Linux":
        raise NotImplementedError("uninstallapp implementado no Linux inicialmente")
    target, desktop, mime = linux_paths(slug, scope=scope)
    if scope == "system" and os.geteuid() != 0:
        raise PermissionError("Remova instalacoes do sistema com autorizacao administrativa")
    if target.exists():
        shutil.rmtree(target)
    desktop.unlink(missing_ok=True)
    mime.unlink(missing_ok=True)
    update = shutil.which("update-mime-database")
    if update and mime.parent.exists():
        subprocess.run([update, str(mime.parent.parent)], check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--scope", choices=["user", "system"], default="user")
    args = parser.parse_args()
    install_bundle(args.bundle, args.scope)


if __name__ == "__main__":
    main()
