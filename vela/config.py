# SPDX-License-Identifier: MPL-2.0
"""Configuração tipada com compatibilidade para settings.py legado."""

from __future__ import annotations

import importlib
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from vela.exceptions import ConfigurationError


def is_missing_target(exc: ModuleNotFoundError, target: str) -> bool:
    """True somente quando o próprio target (ou um pacote pai) não existe."""
    missing = exc.name or ""
    return target == missing or target.startswith(missing + ".")


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    sidebar: bool = True
    topbar: bool = True
    theme: str | None = None


@dataclass(frozen=True, slots=True)
class WindowConfig:
    width: int = 1280
    height: int = 800

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ConfigurationError("WINDOW_WIDTH/WINDOW_HEIGHT devem ser positivos.")


@dataclass(frozen=True, slots=True)
class ApiConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    prefix: str = "/api"
    auto_port: bool = True
    server: str = "waitress"
    workers: int = 4
    docs_enabled: bool = True
    docs_title: str | None = None
    docs_version: str | None = None
    allow_remote: bool = False
    cors_origins: tuple[str, ...] = ()
    max_body_size: int = 1_048_576

    def __post_init__(self):
        if not self.host:
            raise ConfigurationError("API.host não pode ser vazio.")
        if not 0 <= int(self.port) <= 65535:
            raise ConfigurationError("API.port deve estar entre 0 e 65535.")
        if not isinstance(self.prefix, str) or not self.prefix.startswith("/"):
            raise ConfigurationError("API.prefix deve iniciar por '/'.")
        if self.prefix != "/" and self.prefix.endswith("/"):
            raise ConfigurationError("API.prefix não deve terminar com '/'.")
        if int(self.workers) <= 0:
            raise ConfigurationError("API.workers deve ser maior que zero.")
        if self.server not in {"waitress", "bottle"}:
            raise ConfigurationError("API.server deve ser 'waitress' ou 'bottle'.")
        if int(self.max_body_size) <= 0:
            raise ConfigurationError("API.max_body_size deve ser maior que zero.")


@dataclass(frozen=True, slots=True)
class StaticConfig:
    collected_root: str = "staticfiles"
    runtime_prefix: str = "/__vela__/static"


@dataclass(frozen=True, slots=True)
class VelaConfig:
    title: str = "Vela App"
    icon: str = ""
    entry_route: str = "/"
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    debug: bool = True
    api: ApiConfig = field(default_factory=ApiConfig)
    shell_mode: str = "http"
    static_root: str = "staticfiles"

    def __post_init__(self):
        if self.shell_mode not in {"http", "file"}:
            raise ConfigurationError("SHELL_MODE deve ser 'http' ou 'file'.")
        if not self.entry_route.startswith("/"):
            raise ConfigurationError("ENTRY_ROUTE deve iniciar por '/'.")
        if not self.static_root:
            raise ConfigurationError("STATIC_ROOT não pode ser vazio.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["api"]["cors_origins"] = list(self.api.cors_origins)
        return data


class ConfigLoader:
    def __init__(self, settings_module: str = "config.settings"):
        self.settings_module = settings_module
        self._loaded = False
        self._module = None

    def load_module(self):
        if self._loaded:
            return self._module
        try:
            self._module = importlib.import_module(self.settings_module)
        except ModuleNotFoundError as exc:
            if not is_missing_target(exc, self.settings_module):
                raise
            self._module = None
        self._loaded = True
        return self._module

    def load(
        self,
        *,
        title: str | None = None,
        layout: Mapping[str, Any] | None = None,
        enable_api: bool = True,
    ) -> VelaConfig:
        settings = self.load_module()
        layout_data: dict[str, Any] = {"sidebar": True, "topbar": True, "theme": None}
        api_data: dict[str, Any] = {
            "enabled": enable_api,
            "host": "127.0.0.1",
            "port": 8000,
            "prefix": "/api",
            "auto_port": True,
            "server": "waitress",
            "workers": 4,
            "docs_enabled": True,
            "allow_remote": False,
            "cors_origins": (),
            "max_body_size": 1_048_576,
        }
        values: dict[str, Any] = {
            "title": "Vela App",
            "icon": "",
            "entry_route": "/",
            "width": 1280,
            "height": 800,
            "debug": True,
            "shell_mode": "http",
            "static_root": "staticfiles",
        }
        if settings is not None:
            mapping = {
                "APP_TITLE": "title",
                "APP_ICON": "icon",
                "ENTRY_ROUTE": "entry_route",
                "WINDOW_WIDTH": "width",
                "WINDOW_HEIGHT": "height",
                "DEBUG": "debug",
                "SHELL_MODE": "shell_mode",
                "STATIC_ROOT": "static_root",
            }
            for setting_name, key in mapping.items():
                if hasattr(settings, setting_name):
                    values[key] = getattr(settings, setting_name)
            if hasattr(settings, "LAYOUT"):
                layout_data.update(dict(settings.LAYOUT))
            if hasattr(settings, "API"):
                api_data.update(dict(settings.API))
        if title is not None:
            values["title"] = title
        if layout is not None:
            layout_data.update(dict(layout))
        if os.environ.get("VELA_PRODUCTION") == "1":
            values["debug"] = False
        api_data["cors_origins"] = tuple(api_data.get("cors_origins") or ())
        return VelaConfig(
            title=str(values["title"]),
            icon=str(values["icon"]),
            entry_route=str(values["entry_route"]),
            layout=LayoutConfig(**layout_data),
            window=WindowConfig(width=int(values["width"]), height=int(values["height"])),
            debug=bool(values["debug"]),
            api=ApiConfig(**api_data),
            shell_mode=str(values["shell_mode"]),
            static_root=str(values["static_root"]),
        )
