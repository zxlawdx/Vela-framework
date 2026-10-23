# SPDX-License-Identifier: MPL-2.0
"""Cross-platform project/environment diagnostics for Vela."""

from __future__ import annotations

import ctypes.util
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from vela.cli.build import (
    LEGACY_PKG_RESOURCES_MODULES,
    LEGACY_PKG_RESOURCES_PIP,
    backend_for,
    gui_venv_messages,
    inherited_pkg_resources_warning,
    linux_venv_info,
)
from vela.cli.tools import resolve_node_tool


@dataclass
class Check:
    name: str
    status: str
    message: str
    hint: str = ""


def _module_exists(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _active_venv() -> Path | None:
    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        return Path(sys.prefix).resolve()
    virtual_env = os.environ.get("VIRTUAL_ENV")
    return Path(virtual_env).resolve() if virtual_env else None


def _environment_checks(root: Path) -> list[Check]:
    import vela

    checks = [
        Check("PROJECT_ROOT", "ok" if (root / "manage.py").is_file() else "missing", str(root), "Abra o terminal na pasta que contém manage.py"),
        Check("PYTHON_EXECUTABLE", "ok", str(Path(sys.executable).resolve())),
        Check("VELA_INSTALL_PATH", "ok", str(Path(vela.__file__).resolve())),
        Check("Vela version", "ok", vela.__version__),
    ]
    venv = _active_venv()
    if venv is None:
        checks.append(Check("VENV_ROOT", "warning", "nenhum virtualenv ativo", "Use um venv por projeto."))
    else:
        belongs = root == venv or root in venv.parents or venv in root.parents
        checks.append(
            Check(
                "VENV_ROOT",
                "ok" if belongs else "warning",
                str(venv),
                "WARNING: active Python environment does not belong to current project."
                if not belongs
                else "",
            )
        )
    for tool in ("node", "npm", "npx"):
        executable = resolve_node_tool(tool, project_root=root)
        checks.append(Check(tool, "ok" if executable else "warning", executable or "não encontrado", "Instale Node.js apenas se o projeto precisar pipeline JS/Tailwind."))
    essentials = {
        "vela.core.app": _module_exists("vela.core.app"),
        "vela.core.api_server": _module_exists("vela.core.api_server"),
        "vela.cli.commands": _module_exists("vela.cli.commands"),
        "vela.cli.build": _module_exists("vela.cli.build"),
        "shell.html": (Path(vela.__file__).resolve().parent / "core" / "shell.html").is_file(),
        "project templates": (Path(vela.__file__).resolve().parent / "templates" / "project").is_dir(),
    }
    for name, ok in essentials.items():
        checks.append(Check("Framework: " + name, "ok" if ok else "missing", "Disponível" if ok else "AUSENTE", "Reinstale o vela-framework; a instalação está incompleta."))
    static_root = root / "staticfiles"
    checks.append(Check("STATIC_ROOT", "ok" if static_root.is_dir() else "warning", str(static_root), "Rode collectstatic antes do build."))
    checks.append(Check("Build workspace", "warning" if (root / ".vela-build").exists() else "ok", str(root / ".vela-build"), "Diretório temporário existe; builds podem limpá-lo."))
    return checks


def diagnose(root=None, backend="auto"):
    root = Path(root or Path.cwd()).resolve()
    gui = backend_for(backend)
    checks = _environment_checks(root)
    checks.append(Check("Python", "ok" if sys.version_info >= (3, 10) else "missing", platform.python_version(), "Vela requer Python >= 3.10"))
    for name, package, hint in (
        ("pywebview", "webview", "pip install pywebview==6.2.1"),
        ("Waitress", "waitress", "pip install 'waitress>=3,<4'"),
        ("PyInstaller", "PyInstaller", "pip install 'pyinstaller>=6.16,<7'"),
    ):
        ok = _module_exists(package)
        checks.append(Check(name, "ok" if ok else "missing", "Disponível" if ok else "Não instalado", hint))
    if platform.system() == "Linux":
        info = linux_venv_info()
        messages = gui_venv_messages(gui)
        checks.append(Check("Ambiente virtual Linux", "warning" if messages else "ok", info["python"], " ".join(messages)))
        inherited = inherited_pkg_resources_warning()
        if inherited:
            checks.append(Check("Setuptools herdado", "warning", inherited, "Use um venv isolado com extras de build."))
    if _module_exists("pkg_resources"):
        for module in LEGACY_PKG_RESOURCES_MODULES:
            ok = _module_exists(module)
            checks.append(Check("Build: " + module, "ok" if ok else "missing", "Disponível" if ok else "Ausente", "python -m pip install 'vela-framework[build]'"))
    if gui in ("qt6", "qt5"):
        qt = "PyQt6" if gui == "qt6" else "PyQt5"
        for name in (qt, qt + ".QtWebEngineWidgets", "qtpy"):
            ok = _module_exists(name)
            checks.append(Check(name, "ok" if ok else "missing", "Disponível" if ok else "Não instalado"))
    if platform.system() == "Linux":
        for library in ("GL", "EGL", "xcb-cursor", "xkbcommon-x11", "nss3"):
            ok = bool(ctypes.util.find_library(library))
            checks.append(Check(library, "ok" if ok else "warning", "Biblioteca encontrada" if ok else "Biblioteca não detectada"))
    return checks


def missing_pip_packages(checks):
    names = {check.name for check in checks if check.status == "missing"}
    packages = []
    if "pywebview" in names: packages.append("pywebview==6.2.1")
    if "Waitress" in names: packages.append("waitress>=3,<4")
    if "PyInstaller" in names: packages.append("pyinstaller>=6.16,<7")
    if any("Build: " + module in names for module in LEGACY_PKG_RESOURCES_MODULES): packages.extend(LEGACY_PKG_RESOURCES_PIP)
    if "PyQt6" in names or "PyQt6.QtWebEngineWidgets" in names: packages.extend(["PyQt6>=6.8,<7", "PyQt6-WebEngine>=6.8,<7"])
    if "qtpy" in names: packages.append("qtpy>=2.4,<3")
    return list(dict.fromkeys(packages))


def apt_packages(checks):
    missing = {item.name for item in checks if item.status != "ok"}
    mapping = {"GL": "libgl1", "EGL": "libegl1", "xcb-cursor": "libxcb-cursor0", "xkbcommon-x11": "libxkbcommon-x11-0", "nss3": "libnss3"}
    return [package for name, package in mapping.items() if name in missing]


def remedy(checks, confirm=input, notify=print):
    pip_pkgs = missing_pip_packages(checks)
    if pip_pkgs and confirm("Instalar pacotes Python ausentes? [s/N] ").lower() in ("s", "sim", "y"):
        subprocess.run([sys.executable, "-m", "pip", "install", *pip_pkgs], check=True)
    if platform.system() == "Linux" and shutil.which("apt-get"):
        system = apt_packages(checks)
        if system and confirm("Instalar dependências do sistema via polkit? [s/N] ").lower() in ("s", "sim", "y"):
            pkexec = shutil.which("pkexec")
            if not pkexec: raise RuntimeError("pkexec não encontrado")
            subprocess.run([pkexec, "apt-get", "install", "-y", *system], check=True)


def print_report(checks):
    for item in checks:
        mark = {"ok": "OK", "warning": "AVISO", "missing": "FALTA"}[item.status]
        print(f"[{mark:5}] {item.name}: {item.message}")
        if item.status != "ok" and item.hint: print(f"        {item.hint}")
    return 0 if all(x.status == "ok" for x in checks) else 1
