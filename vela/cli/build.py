"""Compilacao nativa Vela via PyInstaller. Build nao usa sudo."""
from __future__ import annotations
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildOptions:
    gui: str = "auto"
    icon: str = ""
    installer: bool = False
    output: str = "dist"
    dry_run: bool = False
    tailwind: bool = False
    plugins: bool = False


def platform_id():
    return {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(
        platform.system(), platform.system().lower())


def backend_for(gui="auto", system=None):
    system = system or platform_id()
    if gui not in ("auto", "qt6", "qt5", "gtk", "native"):
        raise ValueError("Backend desconhecido: " + gui)
    if gui == "gtk" and system != "linux":
        raise ValueError("GTK so esta disponivel no Linux")
    if gui in ("native", "auto") and system == "linux":
        return "qt6"
    return {"auto": "native"}.get(gui, gui)


def read_settings(root):
    from importlib.util import module_from_spec, spec_from_file_location
    path = Path(root) / "config" / "settings.py"
    spec = spec_from_file_location("_vela_project_settings", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(settings):
    title = str(getattr(settings, "APP_TITLE", "Vela App")).strip() or "Vela App"
    slug = re.sub(r"[^A-Za-z0-9_.-]", "-", title.replace(" ", "-")).strip("-._") or "VelaApp"
    return {"name": title, "slug": slug,
            "version": str(getattr(settings, "APP_VERSION", "0.1.0")),
            "author": str(getattr(settings, "APP_AUTHOR", "")),
            "description": str(getattr(settings, "APP_DESCRIPTION", "")),
            "file_extensions": list(getattr(settings, "APP_FILE_EXTENSIONS", []))}


def launcher_source(gui):
    return (
        '"""Entry point gerado pelo Vela. Nao editar manualmente."""\n'
        'import os, sys\n'
        'import multiprocessing; multiprocessing.freeze_support()\n'
        'os.environ.setdefault("VELA_PRODUCTION", "1")\n'
        'from pathlib import Path\n'
        f'GUI = {gui!r}\n'
        'if GUI == "gtk" and "--vela-install" not in sys.argv:\n'
        '    os.environ["PYWEBVIEW_GUI"] = "gtk"\n'
        '    os.environ["VELA_GUI"] = "gtk"\n'
        '    try:\n'
        '        import webview.platforms.gtk\n'
        '    except (ImportError, ValueError) as exc:\n'
        '        raise RuntimeError("GTK exige extensoes Python gi/Gtk/WebKit2 no binario. Recompile com Python que importa gi ou use --gui qt6.") from exc\n'
        'if GUI in ("qt6", "qt5") and "--vela-install" not in sys.argv:\n'
        '    os.environ["PYWEBVIEW_GUI"] = "qt"\n'
        '    os.environ["VELA_GUI"] = "qt"\n'
        '    os.environ["QT_API"] = "pyqt6" if GUI == "qt6" else "pyqt5"\n'
        '    if sys.platform.startswith("linux") and os.getenv("VELA_HARDWARE_ACCELERATION") != "1":\n'
        '        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")\n'
        '        os.environ.setdefault("QT_QUICK_BACKEND", "software")\n'
        '        os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")\n'
        '        flags = os.getenv("QTWEBENGINE_CHROMIUM_FLAGS", "")\n'
        '        if "--disable-gpu" not in flags:\n'
        '            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (flags + " --disable-gpu").strip()\n'
        '    if GUI == "qt6":\n'
        '        from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa\n'
        '    else:\n'
        '        from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa\n'
        '    try:\n'
        '        import qtpy\n'
        '        from qtpy import QtCore, QtWebChannel, QtWebEngineWidgets\n'
        '        import webview.platforms.qt\n'
        '        assert (qtpy.PYQT6 if GUI == "qt6" else qtpy.PYQT5), "QtPy selecionou o backend errado"\n'
        '    except (ImportError, AssertionError) as exc:\n'
        '        raise RuntimeError("Dependencias qtpy/PyQt WebEngine nao foram empacotadas. Recompile com o Vela atualizado.") from exc\n'
        'ROOT = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent\n'
        'os.chdir(ROOT)\n'
        'sys.path.insert(0, str(ROOT))\n'
        'if __name__ == "__main__":\n'
        '    if "--vela-install" in sys.argv:\n'
        '        from vela.cli.install import install_bundle\n'
        '        scope = "system" if "--scope=system" in sys.argv else "user"\n'
        '        install_bundle(ROOT, scope=scope)\n'
        '    elif "--self-test" in sys.argv:\n'
        '        from config.wsgi import run\n'
        '        assert (ROOT / "apps").is_dir() and (ROOT / "staticfiles").is_dir()\n'
        '        print("Vela build OK")\n'
        '    else:\n'
        '        from config.wsgi import run\n'
        '        run()\n'
    )


def build_plan(root, options):
    root = Path(root).resolve()
    if not (root / "manage.py").is_file() or not (root / "config/settings.py").is_file():
        raise FileNotFoundError("Execute buildapp na raiz de um projeto Vela")
    settings = read_settings(root)
    meta = identity(settings)
    system = platform_id()
    gui = backend_for(options.gui, system)
    icon = options.icon or getattr(settings, "APP_ICON", "")
    icon_path = (root / icon).resolve() if icon else None
    if icon_path and not icon_path.is_file():
        raise FileNotFoundError("Icone inexistente: " + str(icon_path))
    if icon_path and system == "windows" and icon_path.suffix.lower() != ".ico":
        raise ValueError("Use um arquivo .ico para o executavel Windows")
    if icon_path and system == "macos" and icon_path.suffix.lower() != ".icns":
        raise ValueError("Use um arquivo .icns para o executavel macOS")
    output = Path(options.output)
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    entry = root / ".vela-build" / "__vela_launcher__.py"
    folders = ["apps", "config", "staticfiles"]
    if (root / "assets").is_dir():
        folders.append("assets")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onedir", "--windowed", "--name", meta["slug"],
           "--distpath", str(output), "--workpath",
           str(root / ".vela-build" / "work"), "--specpath",
           str(root / ".vela-build"), "--collect-all", "vela",
           "--collect-submodules", "apps", "--collect-submodules", "config",
           "--hidden-import", "config.wsgi"]
    # Arquivos do projeto sao copiados PARA A RAIZ do bundle apos PyInstaller.
    # Coloca-los via --add-data moveria arquivos apenas para _internal/ no
    # PyInstaller 6, quebrando import dinamico de templates no Vela.
    if gui in ("qt5", "qt6"):
        cmd += ["--collect-all", "qtpy",
                "--hidden-import", "qtpy",
                "--hidden-import", "webview.platforms.qt",
                "--hidden-import", "qtpy.QtWebEngineWidgets",
                "--hidden-import", "qtpy.QtWebEngineCore",
                "--hidden-import", "qtpy.QtWebChannel"]
    elif gui == "gtk":
        cmd += ["--collect-all", "gi", "--hidden-import", "webview.platforms.gtk",
                "--hidden-import", "gi.repository.Gtk",
                "--hidden-import", "gi.repository.WebKit2"]
    if icon_path:
        cmd += ["--icon", str(icon_path)]
    cmd.append(str(entry))
    return {"root": root, "meta": meta, "gui": gui, "system": system,
            "icon": icon_path, "output": output, "entry": entry,
            "bundle": output / meta["slug"], "command": cmd,
            "folders": folders}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_app(root=None, options=None, notify=print):
    options = options or BuildOptions()
    plan = build_plan(root or Path.cwd(), options)
    if options.dry_run:
        notify("Plataforma: " + plan["system"] + ", backend: " + plan["gui"])
        notify("Comando: " + subprocess.list2cmdline(plan["command"]))
        return plan
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller ausente: pip install 'vela-framework[build]'")
    if plan["gui"] == "qt6" and importlib.util.find_spec("PyQt6") is None:
        raise RuntimeError("PyQt6 ausente: pip install 'vela-framework[qt6]'")
    if plan["gui"] == "qt5" and importlib.util.find_spec("PyQt5") is None:
        raise RuntimeError("PyQt5 ausente: instale PyQt5, PyQtWebEngine e qtpy")

    # Validacao na MESMA instalacao Python/PyInstaller do desenvolvedor.
    gui = plan["gui"]
    if gui in ("qt5", "qt6"):
        if importlib.util.find_spec("qtpy") is None:
            raise RuntimeError("QtPy ausente no ambiente do build. Instale o extra vela-framework[qt6].")
        expected = "pyqt6" if gui == "qt6" else "pyqt5"
        selected = os.environ.get("QT_API", "").lower()
        if selected and selected != expected:
            raise RuntimeError(f"QT_API={selected} conflita com a opcao --gui {gui}.")
        os.environ["QT_API"] = expected
        os.environ["PYWEBVIEW_GUI"] = "qt"
        try:
            importlib.import_module(
                "PyQt6.QtWebEngineWidgets" if gui == "qt6" else "PyQt5.QtWebEngineWidgets")
            importlib.import_module("qtpy.QtWebEngineWidgets")
            importlib.import_module("webview.platforms.qt")
        except (ImportError, ValueError) as exc:
            raise RuntimeError(f"Backend {gui} indisponivel neste ambiente: {exc}") from exc
    elif gui == "gtk":
        try:
            importlib.import_module("webview.platforms.gtk")
        except (ImportError, ValueError) as exc:
            raise RuntimeError(
                "O Python do build nao consegue importar gi/Gtk/WebKit2, mesmo "
                "que GTK esteja instalado no sistema. Use --gui qt6 ou "
                "Python compativel com python3-gi."
            ) from exc

    from vela.cli.collectstatic import collect_static
    notify("Coletando estaticos...")
    if options.tailwind:
        from vela.core.api_server import CORE_DIR
        (plan["root"] / ".vela-build").mkdir(parents=True, exist_ok=True)
        shutil.copy2(CORE_DIR / "shell.html",
                     plan["root"] / ".vela-build/framework-shell.html")
    report = collect_static(apps_dir=str(plan["root"] / "apps"),
                            output_dir=str(plan["root"] / "staticfiles"),
                            verbose=False, skip_tailwind=not options.tailwind)
    if report["errors"]:
        raise RuntimeError("Falha ao copiar arquivos estaticos")
    if options.tailwind and not report["tailwind_bundle"]:
        raise RuntimeError("Tailwind offline nao foi compilado. Verifique Node.js, npm e Tailwind CLI.")
    plan["entry"].parent.mkdir(parents=True, exist_ok=True)
    plan["entry"].write_text(launcher_source(plan["gui"]), encoding="utf-8")
    if options.plugins:
        from vela.plugins import apply_build_hooks
        apply_build_hooks(plan)
    notify("Iniciando PyInstaller...")
    build_env = dict(os.environ)
    if gui in ("qt5", "qt6"):
        build_env["QT_API"] = "pyqt6" if gui == "qt6" else "pyqt5"
        build_env["PYWEBVIEW_GUI"] = "qt"
    elif gui == "gtk":
        build_env["PYWEBVIEW_GUI"] = "gtk"
    subprocess.run(plan["command"], cwd=plan["root"], env=build_env, check=True)
    bundle = plan["bundle"]
    if not bundle.is_dir():
        raise RuntimeError("Binario nao encontrado apos o build")
    # O Vela resolve templates e estaticos a partir do cwd; distribua-os
    # junto ao executavel (nao exclusivamente em _internal).
    for folder in plan["folders"]:
        destination = bundle / folder
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(plan["root"] / folder, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Reexecuta o binario congelado: --self-test agora carrega o backend
    # grafico real e falha quando qtpy/gi nao foram empacotados.
    binary = bundle / (plan["meta"]["slug"] +
                       (".exe" if plan["system"] == "windows" else ""))
    notify("Validando o runtime grafico DENTRO do executavel...")
    try:
        check = subprocess.run([str(binary), "--self-test"], cwd=bundle,
                               capture_output=True, text=True, timeout=50, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        details = getattr(exc, "stderr", "") or getattr(exc, "stdout", "")
        raise RuntimeError(
            "O executavel nao passou no teste interno de GUI; o ZIP nao "
            "sera gerado. " + str(details)[-3500:]
        ) from exc
    notify(check.stdout.strip() or "Runtime grafico empacotado corretamente.")

    meta = dict(plan["meta"], platform=plan["system"], backend=plan["gui"],
                executable=plan["meta"]["slug"] +
                (".exe" if plan["system"] == "windows" else ""))
    if plan["icon"]:
        (bundle / ".vela").mkdir(exist_ok=True)
        shutil.copy2(plan["icon"], bundle / ".vela" / plan["icon"].name)
        meta["icon"] = ".vela/" + plan["icon"].name
    (bundle / ".vela-app.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if options.installer:
        if plan["system"] == "linux":
            script = bundle / "Instalar.sh"
            script.write_text('#!/bin/sh\nDIR="$(cd "$(dirname "$0")" && pwd)"\n'
                              'exec "$DIR/' + meta["executable"] + '" --vela-install\n')
            script.chmod(0o755)
        elif plan["system"] == "windows":
            (bundle / "Instalar.cmd").write_text(
                '@echo off\r\n"%~dp0' + meta["executable"] + '" --vela-install\r\n')
    archive = plan["output"] / (
        meta["slug"] + "-" + meta["platform"] + "-" + platform.machine() +
        "-" + meta["version"] + ".zip")
    notify("Empacotando ZIP...")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for item in bundle.rglob("*"):
            if item.is_file():
                z.write(item, arcname=str(Path(bundle.name) / item.relative_to(bundle)))
    (archive.parent / (archive.name + ".sha256")).write_text(
        sha256(archive) + "  " + archive.name + "\n", encoding="utf-8")
    plan["archive"] = archive
    notify("Build concluido: " + str(archive))
    return plan
