"""Utilitarios desktop opcionais: notificacao nativa e atualizacoes opt-in."""
from __future__ import annotations
import json
import os
import platform
import re
import shutil
import subprocess
from urllib.request import Request, urlopen


def notify(title, message):
    """Best-effort. Retorna False se nao ha backend suportado."""
    title, message = str(title), str(message)
    system = platform.system()
    if system == "Linux" and shutil.which("notify-send"):
        return subprocess.run(["notify-send", title, message], check=False).returncode == 0
    if system == "Darwin" and shutil.which("osascript"):
        def escape(value):
            return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        script = f'display notification "{escape(message)}" with title "{escape(title)}"'
        return subprocess.run(["osascript", "-e", script], check=False).returncode == 0
    if system == "Windows":
        try:
            from win10toast import ToastNotifier
        except ImportError:
            return False
        ToastNotifier().show_toast(title, message, duration=5, threaded=True)
        return True
    return False


def version_tuple(version):
    """Apenas semver estável; prereleases requerem escolha manual."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError("Esperada versao x.y.z sem sufixo")
    return tuple(map(int, match.groups()))


def check_for_updates(repo, current_version, *, timeout=5):
    """Consulta HTTPS GitHub Releases somente quando o desenvolvedor solicita.

    Nao instala nem executa releases automaticamente. O usuario decide.
    """
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or any(part in (".", "..") for part in repo.split("/"))):
        raise ValueError("Repositorio invalido; esperado: owner/repo")
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = Request(url, headers={"Accept": "application/vnd.github+json",
                                   "User-Agent": "Vela-Framework"})
    with urlopen(request, timeout=timeout) as response:
        release = json.load(response)
    latest = release["tag_name"]
    return {
        "current": current_version, "latest": latest,
        "available": version_tuple(latest) > version_tuple(current_version),
        "url": release["html_url"],
        "published_at": release.get("published_at"),
    }
