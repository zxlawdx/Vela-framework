# SPDX-License-Identifier: MPL-2.0
"""Explicit application manifests used by runtime, hot reload and builders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    """Description of one Vela application.

    Legacy ``register_app('apps.foo')`` calls are converted to this model.  A
    manifest makes API modules, static roots and build-time imports explicit so
    consumers do not need side-effect imports merely to register decorators.
    """

    name: str
    module: str
    views_module: str | None = None
    urls_module: str | None = None
    api_module: str | None = None
    static_dirs: tuple[str, ...] = ()
    template_dirs: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    hidden_imports: tuple[str, ...] = ()
    reloadable_modules: tuple[str, ...] = ()
    persistent_modules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or not self.module:
            raise ValueError("AppConfig.name e AppConfig.module são obrigatórios.")
        self.views_module = self.views_module or f"{self.module}.views"
        self.urls_module = self.urls_module or f"{self.module}.urls"
        self.api_module = self.api_module or f"{self.module}.api"
        if not self.reloadable_modules:
            # Views are safe to refresh because Router.refresh_module swaps the
            # callable reference. API/routes stay persistent by default to avoid
            # duplicate decorator registration and state loss.
            self.reloadable_modules = (self.views_module,)
        if not self.static_dirs:
            self.static_dirs = (f"{self.module.replace('.', '/')}/static",)
        if not self.template_dirs:
            self.template_dirs = (f"{self.module.replace('.', '/')}/templates",)

    @classmethod
    def from_legacy(cls, module: str) -> "AppConfig":
        if not isinstance(module, str) or not module.strip():
            raise ValueError("app_module deve ser uma string não vazia.")
        normalized = module.strip()
        return cls(name=normalized.rsplit(".", 1)[-1], module=normalized)

    @property
    def import_modules(self) -> tuple[str, ...]:
        values = [self.module, self.views_module, self.urls_module, self.api_module]
        values.extend(self.hidden_imports)
        return tuple(dict.fromkeys(value for value in values if value))

    def build_metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "module": self.module,
            "modules": list(self.import_modules),
            "static_dirs": list(self.static_dirs),
            "template_dirs": list(self.template_dirs),
            "resources": list(self.resources),
            "hidden_imports": list(self.hidden_imports),
            "reloadable_modules": list(self.reloadable_modules),
            "persistent_modules": list(self.persistent_modules),
        }


class AppRegistry:
    def __init__(self) -> None:
        self._apps: dict[str, AppConfig] = {}

    @staticmethod
    def normalize(value: str | AppConfig | type[AppConfig]) -> AppConfig:
        if isinstance(value, str):
            return AppConfig.from_legacy(value)
        if isinstance(value, type) and issubclass(value, AppConfig):
            value = value()
        if not isinstance(value, AppConfig):
            raise TypeError("register_app aceita str, AppConfig ou classe AppConfig.")
        return value

    def register(self, value: str | AppConfig | type[AppConfig]) -> AppConfig:
        config = self.normalize(value)
        previous = self._apps.get(config.name)
        if previous and previous.module != config.module:
            raise ValueError(
                f"App name duplicado {config.name!r}: {previous.module!r} e {config.module!r}."
            )
        self._apps[config.name] = config
        return config

    def __iter__(self):
        return iter(self._apps.values())

    def __len__(self) -> int:
        return len(self._apps)

    def metadata(self) -> list[dict[str, object]]:
        return [config.build_metadata() for config in self._apps.values()]
