# SPDX-License-Identifier: MPL-2.0
"""Asset verification shared by ``vela assets verify`` and build checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from vela.static import AssetManifest, MANIFEST_NAME

_REMOTE_ASSET = re.compile(r"<(?:script|link)[^>]+https?://", re.IGNORECASE)


@dataclass(slots=True)
class AssetVerification:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)


def verify_assets(
    project_root: str | Path = ".", collected_root: str = "staticfiles"
) -> AssetVerification:
    root = Path(project_root).resolve()
    collected = (root / collected_root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    assets: list[str] = []

    shell = Path(__file__).resolve().parents[1] / "core" / "shell.html"
    if not shell.is_file():
        errors.append(f"shell Vela ausente: {shell}")
    else:
        shell_text = shell.read_text(encoding="utf-8")
        if _REMOTE_ASSET.search(shell_text):
            errors.append("shell de produção contém asset remoto/CDN")

    manifest_path = collected / MANIFEST_NAME
    if not collected.is_dir():
        errors.append(f"collected static ausente: {collected}")
        return AssetVerification(False, errors, warnings, assets)
    if not manifest_path.is_file():
        errors.append(f"manifest ausente: {manifest_path}")
        return AssetVerification(False, errors, warnings, assets)

    try:
        manifest = AssetManifest.load(collected)
    except (OSError, ValueError) as exc:
        errors.append(f"manifest inválido: {exc}")
        return AssetVerification(False, errors, warnings, assets)

    errors.extend(manifest.verify())
    assets.extend(sorted(manifest.files))

    apps_root = root / "apps"
    if apps_root.is_dir():
        for app in sorted(path for path in apps_root.iterdir() if path.is_dir()):
            source = app / "static"
            if not source.is_dir():
                continue
            for path in sorted(item for item in source.rglob("*") if item.is_file()):
                relative = f"{app.name}/{path.relative_to(source).as_posix()}"
                if relative not in manifest.files:
                    errors.append(f"asset source não coletado: {relative}")

    if not assets:
        warnings.append("manifest não contém assets de aplicação")
    return AssetVerification(not errors, errors, warnings, assets)


def print_asset_report(result: AssetVerification) -> int:
    for warning in result.warnings:
        print(f"[AVISO] {warning}")
    for error in result.errors:
        print(f"[ERRO ] {error}")
    if result.ok:
        print(f"[OK   ] assets verificados: {len(result.assets)}")
        return 0
    return 1
