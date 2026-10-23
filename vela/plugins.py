# SPDX-License-Identifier: MPL-2.0
"""Plugins explicitamente ativados pela aplicação/build."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Callable

from vela.exceptions import PluginError
from vela.log.logger import VelaLogger


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    name: str
    priority: int = 100
    enabled: bool = True


class PluginManager:
    def __init__(self):
        self._hooks: list[tuple[PluginMetadata, Callable[[Any], object]]] = []
        self.logger = VelaLogger("plugins")

    def register(
        self,
        callback,
        *,
        name: str | None = None,
        priority: int = 100,
        enabled=True,
    ):
        if not callable(callback):
            raise TypeError("Hook deve ser chamável.")
        metadata = PluginMetadata(
            name or getattr(callback, "__name__", "plugin"), priority, enabled
        )
        if not any(existing is callback for _, existing in self._hooks):
            self._hooks.append((metadata, callback))
        return callback

    def apply(
        self,
        plan,
        *,
        include_entry_points: bool = True,
        continue_on_error: bool = False,
    ):
        hooks = sorted(self._hooks, key=lambda item: item[0].priority)
        for metadata, hook in hooks:
            if metadata.enabled:
                self._run(metadata.name, "build", hook, plan, continue_on_error)
        if include_entry_points:
            points = sorted(
                entry_points(group="vela.build_hooks"), key=lambda point: point.name
            )
            for point in points:
                try:
                    hook = point.load()
                except Exception as exc:
                    if continue_on_error:
                        self.logger.exception(
                            f"Plugin {point.name!r} falhou ao carregar: {exc}"
                        )
                        continue
                    raise PluginError(
                        f"Plugin {point.name!r} falhou ao carregar."
                    ) from exc
                self._run(point.name, "build", hook, plan, continue_on_error)
        return plan

    def _run(self, name, hook_name, callback, plan, continue_on_error):
        try:
            callback(plan)
        except Exception as exc:
            self.logger.exception(
                f"Plugin {name!r}, hook {hook_name!r}, falhou: {exc}"
            )
            if not continue_on_error:
                raise PluginError(
                    f"Plugin {name!r} falhou no hook {hook_name!r}."
                ) from exc


_build_hooks = []


def register_build_hook(callback):
    if not callable(callback):
        raise TypeError("Hook deve ser chamável.")
    if callback not in _build_hooks:
        _build_hooks.append(callback)
    return callback


def apply_build_hooks(plan):
    manager = PluginManager()
    for hook in _build_hooks:
        manager.register(hook)
    return manager.apply(plan)
