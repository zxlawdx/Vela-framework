# SPDX-License-Identifier: MPL-2.0
"""Ports mínimos do core; adapters padrão continuam Bottle/Waitress e pywebview."""

from __future__ import annotations

from typing import Protocol


class HttpServer(Protocol):
    port: int

    def start(self) -> int: ...
    def stop(self) -> None: ...
    def wait_until_ready(self, timeout: float = 10.0): ...


class WindowBackend(Protocol):
    def run(self) -> None: ...
