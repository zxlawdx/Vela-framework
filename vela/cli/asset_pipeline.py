# SPDX-License-Identifier: MPL-2.0
"""Declarative project asset preparation for ``collectstatic``.

Projects may opt into Node/npm preparation and Python asset hooks through the
``ASSETS`` setting.  Vela never installs system packages: when Node.js/npm is
missing the command fails with an actionable message.  Project-local npm
packages may be installed only after explicit user approval (or ``--yes``).
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from vela.cli.tools import resolve_node_tool


class AssetPipelineError(RuntimeError):
    """Raised when declared asset prerequisites cannot be satisfied safely."""


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssetPipelineError(
            f"Falha ao executar {' '.join(command)!r}: {exc}"
        ) from exc


def _node_tools(project_root: Path) -> tuple[str, str]:
    node = resolve_node_tool("node", project_root=str(project_root))
    npm = resolve_node_tool("npm", project_root=str(project_root))
    if node and npm:
        return node, npm
    missing = "Node.js e npm" if not node and not npm else ("Node.js" if not node else "npm")
    raise AssetPipelineError(
        f"{missing} não encontrado(s). O pipeline de assets deste projeto depende deles. "
        "Instale Node.js (recomendado: versão LTS, com npm) e execute novamente "
        "`python manage.py collectstatic`. Vela não instala pacotes de sistema automaticamente."
    )


def _node_dependencies_ready(project_root: Path, npm: str) -> bool:
    if not (project_root / "node_modules").is_dir():
        return False
    result = _run(
        [npm, "ls", "--depth=0", "--json"],
        cwd=project_root,
        timeout=30,
        capture_output=True,
    )
    return result.returncode == 0


def _confirm_install(
    command: list[str],
    *,
    assume_yes: bool,
    allow_install: bool,
) -> None:
    rendered = " ".join(command)
    if not allow_install:
        raise AssetPipelineError(
            f"Dependências de assets ausentes ou inconsistentes. Execute `{rendered}` e rode "
            "`python manage.py collectstatic` novamente."
        )
    if assume_yes:
        return
    if not sys.stdin or not sys.stdin.isatty():
        raise AssetPipelineError(
            "Dependências de assets ausentes ou inconsistentes em ambiente não interativo. "
            f"Execute `{rendered}` antes, ou use `python manage.py collectstatic --yes` para "
            "autorizar a instalação local automaticamente."
        )
    answer = input(
        f"Dependências JavaScript ausentes ou inconsistentes. Executar `{rendered}` agora? [S/n] "
    )
    if answer.strip().lower() not in {"", "s", "sim", "y", "yes"}:
        raise AssetPipelineError(
            f"Instalação recusada. Execute `{rendered}` quando quiser preparar os assets."
        )


def _install_node_dependencies(
    project_root: Path,
    npm: str,
    install_mode: str,
    *,
    assume_yes: bool,
    allow_install: bool,
    verbose: bool,
) -> str:
    if install_mode not in {"ci", "install"}:
        raise AssetPipelineError(
            "ASSETS['node']['install'] deve ser 'ci' ou 'install'."
        )
    if install_mode == "ci" and not (project_root / "package-lock.json").is_file():
        raise AssetPipelineError(
            "ASSETS solicita `npm ci`, mas package-lock.json não existe. "
            "Gere o lockfile ou use install='install'."
        )
    command = [npm, install_mode]
    _confirm_install(command, assume_yes=assume_yes, allow_install=allow_install)
    if verbose:
        print(f"\n  -> Instalando dependências locais: {' '.join(command)}")
    result = _run(command, cwd=project_root, timeout=300)
    if result.returncode != 0:
        raise AssetPipelineError(
            f"`{' '.join(command)}` terminou com código {result.returncode}."
        )
    return install_mode


def _run_npm_script(project_root: Path, npm: str, script: str, *, verbose: bool) -> None:
    if not isinstance(script, str) or not script.strip():
        raise AssetPipelineError("Scripts npm em ASSETS devem ser strings não vazias.")
    if verbose:
        print(f"\n  -> npm run {script}")
    result = _run([npm, "run", script], cwd=project_root, timeout=300)
    if result.returncode != 0:
        raise AssetPipelineError(
            f"`npm run {script}` terminou com código {result.returncode}."
        )


def _run_python_hook(project_root: Path, target: str, *, verbose: bool) -> None:
    if not isinstance(target, str) or ":" not in target:
        raise AssetPipelineError(
            "Hooks Python em ASSETS devem usar o formato 'modulo:callable'."
        )
    module_name, callable_name = target.rsplit(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or module_name
        raise AssetPipelineError(
            f"Não foi possível carregar o hook {target!r}; módulo/dependência Python ausente: "
            f"{missing!r}. Instale as dependências Python do projeto e execute collectstatic novamente."
        ) from exc
    callback = getattr(module, callable_name, None)
    if not callable(callback):
        raise AssetPipelineError(f"Hook de assets inválido: {target!r} não é callable.")
    if verbose:
        print(f"\n  -> hook Python {target}")
    callback()


def run_project_asset_pipeline(
    project_root: str | Path,
    config: dict[str, Any] | None,
    *,
    assume_yes: bool = False,
    allow_install: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    """Prepare project-specific assets declared in ``config.settings.ASSETS``.

    Supported configuration::

        ASSETS = {
            "node": {
                "install": "ci",            # or "install"
                "scripts": ["build:vendor"],
            },
            "hooks": ["tools.build_css:main"],
            "tailwind": False,              # consumed by collectstatic
        }

    Node/npm themselves are never installed by Vela.  Missing local npm
    dependencies are installed only after an interactive confirmation, or when
    ``assume_yes`` is explicitly enabled by the CLI ``--yes`` flag.
    """
    root = Path(project_root).resolve()
    config = dict(config or {})
    if not config:
        return {
            "configured": False,
            "node_dependencies": None,
            "npm_scripts": [],
            "python_hooks": [],
        }

    node_config = config.get("node") or {}
    if not isinstance(node_config, dict):
        raise AssetPipelineError("ASSETS['node'] deve ser um dicionário.")
    scripts = node_config.get("scripts") or []
    hooks = config.get("hooks") or []
    if not isinstance(scripts, (list, tuple)):
        raise AssetPipelineError("ASSETS['node']['scripts'] deve ser uma lista.")
    if not isinstance(hooks, (list, tuple)):
        raise AssetPipelineError("ASSETS['hooks'] deve ser uma lista.")

    report: dict[str, Any] = {
        "configured": True,
        "node_dependencies": None,
        "npm_scripts": [],
        "python_hooks": [],
    }

    if node_config or scripts:
        if not (root / "package.json").is_file():
            raise AssetPipelineError(
                "ASSETS declara pipeline Node, mas package.json não existe na raiz do projeto."
            )
        _node, npm = _node_tools(root)
        install_mode = str(node_config.get("install", "ci"))
        if not _node_dependencies_ready(root, npm):
            report["node_dependencies"] = _install_node_dependencies(
                root,
                npm,
                install_mode,
                assume_yes=assume_yes,
                allow_install=allow_install,
                verbose=verbose,
            )
        else:
            report["node_dependencies"] = "ready"
            if verbose:
                print("  * dependências Node: OK")
        for script in scripts:
            _run_npm_script(root, npm, script, verbose=verbose)
            report["npm_scripts"].append(script)

    for hook in hooks:
        _run_python_hook(root, hook, verbose=verbose)
        report["python_hooks"].append(hook)

    return report
