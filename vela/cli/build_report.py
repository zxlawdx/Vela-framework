# SPDX-License-Identifier: MPL-2.0
"""Machine-readable build evidence for Vela distributions."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path


def build_report(plan: dict, project_root: str | Path = ".") -> dict[str, object]:
    import vela

    root = Path(project_root).resolve()
    meta = dict(plan.get("meta") or {})
    warnings = list(plan.get("warnings") or [])
    executable = plan.get("executable") or meta.get("executable")
    apps = []
    apps_root = root / "apps"
    if apps_root.is_dir():
        apps = sorted(path.name for path in apps_root.iterdir() if path.is_dir() and (path / "__init__.py").exists())
    assets = []
    manifest = root / "staticfiles" / "manifest.json"
    if manifest.is_file():
        try:
            assets = sorted(json.loads(manifest.read_text(encoding="utf-8")).get("files", {}))
        except (ValueError, OSError):
            warnings.append("staticfiles/manifest.json inválido")
    hidden_imports = sorted(set(plan.get("hidden_imports") or []))
    return {
        "python": sys.version.split()[0],
        "vela": vela.__version__,
        "platform": platform.platform(),
        "backend": plan.get("gui") or plan.get("backend") or "unknown",
        "apps": apps,
        "hidden_imports": hidden_imports,
        "assets": assets,
        "entrypoint": str(plan.get("entry") or "config/wsgi.py"),
        "executable": str(executable or ""),
        "warnings": warnings,
    }


def write_build_report(plan: dict, project_root: str | Path = ".") -> Path:
    root = Path(project_root).resolve()
    output = Path(plan.get("output") or root / "dist")
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    target = output / "build-report.json"
    target.write_text(json.dumps(build_report(plan, root), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
