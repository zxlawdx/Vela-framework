# SPDX-License-Identifier: MPL-2.0
"""Cross-platform static collection and optional asset preparation."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from vela.cli.asset_pipeline import (
    AssetPipelineError,
    _confirm_install,
    run_project_asset_pipeline,
)
from vela.cli.tools import resolve_node_tool
from vela.log.logger import VelaLogger
from vela.static import AssetManifest

logger = VelaLogger("collectstatic")

_TAILWIND_CDN_RE = re.compile(
    r"cdn\.tailwindcss\.com|unpkg\.com/tailwindcss|jsdelivr.*tailwind", re.IGNORECASE
)
_TAILWIND_CLASS_RE = re.compile(
    r"class=[\"'][^\"']*(?:bg-|text-|flex|grid|p-\d|m-\d|w-|h-|rounded|border|shadow|items-|justify-|gap-|space-|font-|hover:|focus:|sm:|md:|lg:|xl:|dark:)"
)
_TEMPLATE_EXTS = {".html", ".htm", ".jinja", ".j2"}
_DEFAULT_TAILWIND_CONFIG = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./apps/**/templates/**/*.html", "./apps/**/static/**/*.js", "./templates/**/*.html"],
  theme: { extend: {} },
  plugins: [],
}
"""
_TAILWIND_INPUT_CSS = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"


def _file_hash(path: str) -> str:
    # Compatibility helper retained for callers; manifests use SHA-256 now.
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_template_files(project_root: str) -> list[str]:
    found: list[str] = []
    skip = {
        "node_modules",
        "venv",
        ".venv",
        "staticfiles",
        ".vela-build",
        "__pycache__",
        ".git",
        "dist",
        "build",
    }
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [directory for directory in dirs if directory not in skip]
        for filename in files:
            if Path(filename).suffix in _TEMPLATE_EXTS:
                found.append(os.path.join(root, filename))
    return found


def _detect_tailwind(project_root: str) -> dict:
    config_path = Path(project_root) / "tailwind.config.js"
    if config_path.exists():
        return {"found": True, "reason": "config_file", "config_exists": True}
    for path in _find_template_files(project_root):
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _TAILWIND_CDN_RE.search(content):
            return {"found": True, "reason": "cdn_tag", "config_exists": False}
        if _TAILWIND_CLASS_RE.search(content):
            return {"found": True, "reason": "class_usage", "config_exists": False}
    return {"found": False, "reason": None, "config_exists": False}


def _ensure_node_available(project_root: str = ".") -> bool:
    return bool(
        resolve_node_tool("node", project_root=project_root)
        and resolve_node_tool("npm", project_root=project_root)
    )


def _ensure_tailwind_cli(
    project_root: str,
    verbose: bool,
    *,
    assume_yes: bool = False,
    allow_install: bool = True,
) -> bool:
    if resolve_node_tool("tailwindcss", project_root=project_root):
        return True
    npm = resolve_node_tool("npm", project_root=project_root)
    if not npm:
        return False
    command = [npm, "install", "--save-dev", "tailwindcss@3.4.17"]
    _confirm_install(command, assume_yes=assume_yes, allow_install=allow_install)
    if verbose:
        print("    -> Instalando Tailwind CLI local via npm...")
    try:
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error(f"npm install tailwindcss falhou: {exc}")
        return False
    if result.returncode != 0:
        logger.error(f"npm install tailwindcss falhou: {result.stderr}")
        return False
    return bool(resolve_node_tool("tailwindcss", project_root=project_root))


def _create_tailwind_config(project_root: str) -> None:
    path = Path(project_root) / "tailwind.config.js"
    if not path.exists():
        path.write_text(_DEFAULT_TAILWIND_CONFIG, encoding="utf-8")


def _compile_tailwind(
    project_root: str,
    input_css: str,
    output_css: str,
    minify: bool,
    verbose: bool,
) -> bool:
    executable = resolve_node_tool("tailwindcss", project_root=project_root)
    if not executable:
        return False
    command = [executable, "-i", input_css, "-o", output_css]
    if minify:
        command.append("--minify")
    try:
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error(f"Tailwind CLI exec error: {exc}")
        return False
    if result.returncode != 0:
        logger.error(f"Tailwind CLI error: {result.stderr}")
        return False
    if verbose:
        print(f"    * vela.bundle.css gerado ({Path(output_css).stat().st_size / 1024:.1f} KB)")
    return True


def run_tailwind_pipeline(
    project_root: str,
    output_dir: str,
    minify: bool = False,
    verbose: bool = True,
    *,
    assume_yes: bool = False,
    allow_install: bool = True,
) -> bool:
    detection = _detect_tailwind(project_root)
    if not detection["found"]:
        return False
    if not _ensure_node_available(project_root):
        raise AssetPipelineError(
            "Node.js/npm não encontrado(s), mas Tailwind foi detectado. Instale Node.js "
            "(recomendado: versão LTS, com npm) e execute novamente "
            "`python manage.py collectstatic`."
        )
    _create_tailwind_config(project_root)
    if not _ensure_tailwind_cli(
        project_root,
        verbose,
        assume_yes=assume_yes,
        allow_install=allow_install,
    ):
        raise AssetPipelineError("Tailwind CLI não pôde ser preparado.")
    css_dir = Path(output_dir) / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    input_css = css_dir / "tailwind.input.css"
    input_css.write_text(_TAILWIND_INPUT_CSS, encoding="utf-8")
    return _compile_tailwind(
        project_root,
        str(input_css),
        str(css_dir / "vela.bundle.css"),
        minify,
        verbose,
    )


def _collect_app_statics(abs_apps_dir: str, abs_output: str, verbose: bool) -> dict:
    stats = {"copied": 0, "skipped": 0, "errors": 0}
    apps = Path(abs_apps_dir)
    output = Path(abs_output)
    if not apps.is_dir():
        # An empty project is valid; it simply has no application assets yet.
        return stats
    for app in sorted(path for path in apps.iterdir() if path.is_dir()):
        static = app / "static"
        if not static.is_dir():
            continue
        destination = output / app.name
        for source in sorted(path for path in static.rglob("*") if path.is_file()):
            if source.name == "tailwind.input.css":
                continue
            target = destination / source.relative_to(static)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and _file_hash(str(source)) == _file_hash(str(target)):
                    stats["skipped"] += 1
                    continue
                shutil.copy2(source, target)
                stats["copied"] += 1
                if verbose:
                    print(f"    * copiado: {target.relative_to(output).as_posix()}")
            except OSError as exc:
                stats["errors"] += 1
                logger.error(f"Erro ao copiar {source}: {exc}")
    return stats


def _generate_manifest(output_dir: str, verbose: bool) -> dict:
    manifest = AssetManifest.generate(output_dir)
    manifest.write()
    if verbose:
        print(f"\n  * manifest.json gerado ({len(manifest.files)} arquivo(s), SHA-256).")
    return {"version": manifest.version, "algorithm": manifest.algorithm, "files": manifest.files}


def collect_static(
    apps_dir: str = "apps",
    output_dir: str = "staticfiles",
    verbose: bool = True,
    skip_tailwind: bool = False,
    minify: bool = False,
    *,
    asset_config: dict | None = None,
    assume_yes: bool = False,
    allow_install: bool = True,
) -> dict:
    """Prepare project assets and collect them into the runtime static directory.

    ``output_dir`` is collected runtime data, not the build workspace (``.vela-build``)
    and not the final distribution directory (``dist``).

    When ``config.settings.ASSETS`` is supplied by the CLI, project-specific npm
    scripts and Python hooks run before files are copied. Missing project-local
    npm dependencies require explicit confirmation, unless ``assume_yes`` is set.
    """
    project_root = Path.cwd()
    output = (project_root / output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    pipeline_report = run_project_asset_pipeline(
        project_root,
        asset_config,
        assume_yes=assume_yes,
        allow_install=allow_install,
        verbose=verbose,
    )

    config_tailwind = True
    if asset_config is not None:
        config_tailwind = bool(asset_config.get("tailwind", True))
    tailwind_ok = False
    if not skip_tailwind and config_tailwind:
        tailwind_ok = run_tailwind_pipeline(
            str(project_root),
            str(output),
            minify=minify,
            verbose=verbose,
            assume_yes=assume_yes,
            allow_install=allow_install,
        )

    stats = _collect_app_statics(str(project_root / apps_dir), str(output), verbose)
    manifest = _generate_manifest(str(output), verbose)
    return {
        **stats,
        "tailwind_bundle": tailwind_ok,
        "asset_pipeline": pipeline_report,
        "manifest": manifest,
    }
