"""Diagnostico multiplataforma do ambiente de desenvolvimento Vela.

A instalacao de pacotes exige confirmacao. NUNCA le senhas; usa pkexec
(polkit) para pedir privilegios por meio da interface do sistema operacional.
"""
from __future__ import annotations

import ctypes.util
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from vela.cli.build import backend_for


@dataclass
class Check:
    name: str
    status: str   # ok | warning | missing
    message: str
    hint: str = ""


def _module_exists(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def diagnose(root=None, backend="auto"):
    root = Path(root or Path.cwd()).resolve()
    gui = backend_for(backend)
    checks = []
    checks.append(Check(
        "Projeto Vela", "ok" if (root / "manage.py").is_file() else "missing",
        str(root), "Abra o terminal na pasta que contem manage.py"))
    checks.append(Check(
        "Python", "ok" if sys.version_info >= (3, 10) else "missing",
        platform.python_version(), "Vela requer Python >= 3.10"))
    for name, package, hint in (
        ("pywebview", "webview", "pip install pywebview==6.2.1"),
        ("Waitress", "waitress", "pip install 'waitress>=3,<4'"),
        ("PyInstaller", "PyInstaller", "pip install 'pyinstaller>=6.16,<7'"),
    ):
        ok = _module_exists(package)
        checks.append(Check(name, "ok" if ok else "missing",
                            "Disponivel" if ok else "Nao instalado", hint))
    if gui in ("qt6", "qt5"):
        qt = "PyQt6" if gui == "qt6" else "PyQt5"
        webengine = qt + ".QtWebEngineWidgets"
        for name in (qt, webengine, "qtpy"):
            ok = _module_exists(name)
            checks.append(Check(name, "ok" if ok else "missing",
                                "Disponivel" if ok else "Nao instalado",
                                ("pip install 'vela-framework[qt6]'"
                                 if gui == "qt6" else
                                 "pip install PyQt5 PyQtWebEngine qtpy")))
    if gui == "gtk" and platform.system() == "Linux":
        gi = _module_exists("gi")
        checks.append(Check("GTK/PyGObject", "ok" if gi else "missing",
                            "Disponivel" if gi else "Nao instalado",
                            "Instale python3-gi, gir1.2-gtk-3.0 e WebKit2GTK"))
    if platform.system() == "Linux":
        for library in ("GL", "EGL", "xcb-cursor", "xkbcommon-x11", "nss3"):
            ok = bool(ctypes.util.find_library(library))
            checks.append(Check(library, "ok" if ok else "warning",
                                "Biblioteca encontrada" if ok else "Biblioteca nao detectada",
                                "Verifique dependencias graficas do sistema"))
        if not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")):
            checks.append(Check("Ambiente grafico", "warning",
                                "DISPLAY e WAYLAND_DISPLAY ausentes",
                                "A GUI precisa de uma sessao grafica; CI pode usar Xvfb"))
    tk = _module_exists("tkinter")
    checks.append(Check("Assistente visual", "ok" if tk else "warning",
                        "Tkinter disponivel" if tk else "Tkinter nao instalado",
                        "No Ubuntu/Mint: sudo apt install python3-tk"))
    return checks


def missing_pip_packages(checks):
    names = {check.name for check in checks if check.status == "missing"}
    packages = []
    if "pywebview" in names:
        packages.append("pywebview==6.2.1")
    if "Waitress" in names:
        packages.append("waitress>=3,<4")
    if "PyInstaller" in names:
        packages.append("pyinstaller>=6.16,<7")
    if "PyQt6" in names or "PyQt6.QtWebEngineWidgets" in names:
        packages.extend(["PyQt6>=6.8,<7", "PyQt6-WebEngine>=6.8,<7"])
    if "qtpy" in names:
        packages.append("qtpy>=2.4,<3")
    if "PyQt5" in names or "PyQt5.QtWebEngineWidgets" in names:
        packages.extend(["PyQt5>=5.15,<6", "PyQtWebEngine>=5.15,<6"])
    # Mantem a ordem sem instalar duplicados.
    return list(dict.fromkeys(packages))


def apt_packages(checks):
    missing = {item.name for item in checks if item.status != "ok"}
    mapping = {
        "GL": "libgl1", "EGL": "libegl1", "xcb-cursor": "libxcb-cursor0",
        "xkbcommon-x11": "libxkbcommon-x11-0", "nss3": "libnss3",
        "Assistente visual": "python3-tk", "GTK/PyGObject": "python3-gi",
    }
    return [package for name, package in mapping.items() if name in missing]


def remedy(checks, confirm=input, notify=print):
    """Solicita aprovacao independente antes de cada conjunto de alteracoes."""
    pip_pkgs = missing_pip_packages(checks)
    if pip_pkgs:
        cmd = [sys.executable, "-m", "pip", "install", *pip_pkgs]
        notify("Pacotes Python ausentes: " + ", ".join(pip_pkgs))
        if confirm("Instalar no ambiente Python atual? [s/N] ").lower() in ("s", "sim", "y"):
            subprocess.run(cmd, check=True)
    if platform.system() == "Linux" and shutil.which("apt-get"):
        system = apt_packages(checks)
        if system:
            notify("Pacotes do sistema sugeridos: " + ", ".join(system))
            if confirm("Instalar usando o dialogo administrativo do sistema? [s/N] ").lower() in ("s", "sim", "y"):
                pkexec = shutil.which("pkexec")
                if not pkexec:
                    raise RuntimeError("pkexec nao encontrado; instale via gerenciador de pacotes")
                notify("O polkit solicitara sua autorizacao; o Vela nao acessa a senha.")
                subprocess.run([pkexec, "apt-get", "install", "-y", *system], check=True)


def print_report(checks):
    for item in checks:
        mark = {"ok": "OK", "warning": "AVISO", "missing": "FALTA"}[item.status]
        print(f"[{mark:5}] {item.name}: {item.message}")
        if item.status != "ok" and item.hint:
            print(f"        {item.hint}")
    return 0 if all(x.status == "ok" for x in checks) else 1
